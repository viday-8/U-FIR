from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import current_user, get_case_or_404, require_role, scoped_cases
from .db import Base, engine, get_db
from datetime import datetime, timezone

from .models import Audit, Candidate, Case, Document, Draft, DraftVersion, Entity, Fact, FactCorrection, LegalSuggestion, Page, User
from .services import brief as brief_svc
from pathlib import Path

from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .services import drafts as drafts_svc
from .services import analytics, evaluate
from .services import copilot as copilot_svc
from .services import graph, ingest, legal, search
from . import audit, config
from .security import hash_password, make_token, verify_password

app = FastAPI(title="u-FIR Nexus API (DEMO / SYNTHETIC DATA)")
Base.metadata.create_all(engine)


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"  # case data must not be cached by browsers or proxies
    return resp


_failures: dict[str, list[float]] = {}
MAX_FAILS, WINDOW = 5, 60.0


class Login(BaseModel):
    username: str
    password: str


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "mode": "demo-synthetic"}


@app.post("/api/v1/auth/login")
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    import time
    key = f"{request.client.host if request.client else '?'}:{body.username.lower()}"
    now = time.time()
    recent = [t for t in _failures.get(key, []) if now - t < WINDOW]
    if len(recent) >= MAX_FAILS:
        raise HTTPException(429, "Too many failed attempts. Wait a minute and try again.")
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        _failures[key] = [*recent, now]
        raise HTTPException(401, "Invalid credentials")
    _failures.pop(key, None)
    return {"token": make_token(user.username), "role": user.role, "district": user.district}


def case_out(c: Case):
    return {"id": c.id, "case_no": c.case_no, "district": c.district, "station": c.station,
            "status": c.status, "registered_on": c.registered_on, "documents": len(c.documents)}


@app.get("/api/v1/cases")
def list_cases(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [case_out(c) for c in db.scalars(scoped_cases(user))]


@app.get("/api/v1/cases/{case_id}")
def get_case(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return case_out(get_case_or_404(db, user, case_id))


@app.get("/api/v1/audit")
def get_audit(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "admin", "supervisor")
    rows = db.scalars(select(Audit).order_by(Audit.id.desc()).limit(200))
    return [{"at": r.at, "actor": r.actor, "action": r.action, "resource": r.resource,
             "model": r.model, "outcome": r.outcome} for r in rows]


@app.post("/api/v1/ingest", status_code=202)
async def ingest_file(background: BackgroundTasks, case_id: int = Form(...), doc_type: str = Form("fir"),
                      file: UploadFile = File(...), user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    require_role(user, "investigator", "supervisor", "admin")
    get_case_or_404(db, user, case_id)
    doc = ingest.save_document(db, case_id, doc_type, file.filename or "", await file.read())
    if doc.status == "received":
        background.add_task(ingest.process_document, doc.id)
    return {"document_id": doc.id, "status": doc.status}


@app.get("/api/v1/ingest/{doc_id}")
def ingest_status(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Not found")
    get_case_or_404(db, user, doc.case_id)
    return {"document_id": doc.id, "status": doc.status}


class DocReview(BaseModel):
    note: str


def _doc_for_action(db: Session, user: User, doc_id: int) -> Document:
    require_role(user, "investigator", "supervisor", "admin")
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Not found")
    get_case_or_404(db, user, doc.case_id)
    return doc


@app.post("/api/v1/documents/{doc_id}/mark-reviewed")
def mark_document_reviewed(doc_id: int, body: DocReview, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _doc_for_action(db, user, doc_id)
    if doc.status not in ("needs_review", "failed"):
        raise HTTPException(409, "Only documents that need review can be marked reviewed")
    if not body.note.strip():
        raise HTTPException(422, "Say what you checked (a note is required)")
    old = doc.status
    doc.status, doc.reviewed_by, doc.review_note = "reviewed", user.username, body.note.strip()
    db.commit()
    audit.log(db, user.username, "review_document", f"document:{doc.id}", outcome=f"{old}->reviewed")
    return {"document_id": doc.id, "status": doc.status}


@app.post("/api/v1/documents/{doc_id}/retry")
def retry_document(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _doc_for_action(db, user, doc_id)
    if doc.status not in ("needs_review", "failed", "received"):
        raise HTTPException(409, "Only documents that failed or need review can be reprocessed")
    doc.reviewed_by = doc.review_note = None
    db.commit()
    ingest.process_document(doc.id)  # same pipeline as the first run; failures are logged, never raised
    db.refresh(doc)
    audit.log(db, user.username, "retry_document", f"document:{doc.id}", outcome=doc.status)
    return {"document_id": doc.id, "status": doc.status}


@app.get("/api/v1/cases/{case_id}/facts")
def case_facts(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case_or_404(db, user, case_id)
    rows = db.scalars(select(Fact).where(Fact.case_id == case_id).order_by(Fact.id))
    return [{"id": f.id, "type": f.type, "original": f.original, "normalised": f.normalised,
             "document_id": f.document_id, "page": f.page, "span": f.span,
             "attributes": f.attributes, "model": f.model, "corrected": f.corrected} for f in rows]


@app.get("/api/v1/search")
def search_endpoint(q: str, doc_type: str | None = None, station: str | None = None,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    return search.search(db, user, q[:200], doc_type=doc_type, station=station)


@app.get("/api/v1/cases/{case_id}/brief")
def case_brief(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    case = get_case_or_404(db, user, case_id)
    result = brief_svc.build_brief(db, case)
    used = sorted({i for s in result["sections"] for st in s["statements"] for i in st["fact_ids"]})
    audit.log(db, user.username, "generate_brief", f"case:{case_id}", model="template-v1", evidence=used, outcome="shown")
    return result


@app.get("/api/v1/cases/{case_id}/timeline")
def case_timeline(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return brief_svc.build_timeline(db, get_case_or_404(db, user, case_id))


@app.get("/api/v1/documents/{doc_id}")
def get_document(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Not found")
    case = get_case_or_404(db, user, doc.case_id)
    facts = db.scalars(select(Fact).where(Fact.document_id == doc_id).order_by(Fact.id))
    return {"id": doc.id, "case_id": case.id, "case_no": case.case_no, "doc_type": doc.doc_type, "status": doc.status,
            "checksum": doc.checksum, "language": doc.language, "reviewed_by": doc.reviewed_by, "review_note": doc.review_note, "has_ocr": any(p.ocr for p in doc.pages),
            "pages": [{"number": p.number, "text": p.text, "ocr": p.ocr} for p in sorted(doc.pages, key=lambda p: p.number)],
            "facts": [{"id": f.id, "type": f.type, "original": f.original, "page": f.page, "span": f.span} for f in facts]}


@app.get("/api/v1/candidates")
def list_candidates(status: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return graph.visible_candidates(db, user, status)


@app.get("/api/v1/relationships")
def relationships(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return graph.build_graph(db, user)


class Decision(BaseModel):
    decision: str  # confirm | reject | defer
    reason: str = ""


@app.post("/api/v1/candidates/{cand_id}/review")
def review_candidate(cand_id: int, body: Decision, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "investigator", "supervisor", "admin")
    status = {"confirm": "confirmed", "reject": "rejected", "defer": "deferred"}.get(body.decision)
    if not status:
        raise HTTPException(422, "decision must be confirm, reject or defer")
    if status != "deferred" and not body.reason.strip():
        raise HTTPException(422, "A reason is required")
    visible = {c["id"] for c in graph.visible_candidates(db, user)}  # both cases must be in scope
    cand = db.get(Candidate, cand_id) if cand_id in visible else None
    if not cand:
        raise HTTPException(404, "Not found")
    old = cand.status
    cand.status, cand.decided_by, cand.reason, cand.decided_at = status, user.username, body.reason.strip() or None, datetime.now(timezone.utc)
    db.commit()
    audit.log(db, user.username, "review_identity_match", f"candidate:{cand_id}", evidence=cand.evidence, outcome=f"{old}->{status}")
    return {"id": cand.id, "status": cand.status}


@app.get("/api/v1/legal/catalogue")
def legal_catalogue(user: User = Depends(current_user)):
    return legal.catalogue()


@app.get("/api/v1/cases/{case_id}/legal")
def case_legal(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case_or_404(db, user, case_id)
    rows = db.query(LegalSuggestion).filter_by(case_id=case_id).order_by(LegalSuggestion.id).all()
    return {"notice": legal.CATALOGUE["notice"], "suggestions": [legal.out(r) for r in rows]}


@app.post("/api/v1/cases/{case_id}/legal/suggest")
def case_legal_suggest(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "investigator", "supervisor", "admin")
    rows = legal.suggest(db, get_case_or_404(db, user, case_id))
    audit.log(db, user.username, "legal_suggestions", f"case:{case_id}", model="catalogue-rules-v1",
              evidence=[r.ref_id for r in rows], outcome=f"{len(rows)} suggestion(s)")
    return {"notice": legal.CATALOGUE["notice"], "suggestions": [legal.out(r) for r in rows]}


class LegalDecision(BaseModel):
    decision: str  # accept | reject
    reason: str = ""


@app.post("/api/v1/legal/{sid}/review")
def review_legal(sid: int, body: LegalDecision, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "investigator", "supervisor", "admin")
    status = {"accept": "accepted", "reject": "rejected"}.get(body.decision)
    if not status:
        raise HTTPException(422, "decision must be accept or reject")
    if not body.reason.strip():
        raise HTTPException(422, "A reason is required")
    row = db.get(LegalSuggestion, sid)
    if not row:
        raise HTTPException(404, "Not found")
    get_case_or_404(db, user, row.case_id)
    old, row.status = row.status, status
    row.decided_by, row.reason, row.decided_at = user.username, body.reason.strip(), datetime.now(timezone.utc)
    db.commit()
    audit.log(db, user.username, "review_legal_suggestion", f"legal:{sid}", evidence=row.fact_ids, outcome=f"{old}->{status}")
    return legal.out(row)


# ---------------- Document Studio ----------------
EDITORS = ("investigator", "supervisor", "admin")


def draft_out(d: Draft, db: Session, full: bool = True):
    out = {"id": d.id, "case_id": d.case_id, "doc_type": d.doc_type, "title": drafts_svc.TYPES[d.doc_type], "status": d.status,
           "version": d.version, "author": d.author, "reviewer": d.reviewer, "updated_at": d.updated_at}
    if full:
        out |= {"sections": d.sections, "comments": d.comments, "unfilled": drafts_svc.unfilled(d.sections),
                "versions": [{"version": v.version, "author": v.author, "note": v.note, "at": v.at}
                             for v in db.query(DraftVersion).filter_by(draft_id=d.id).order_by(DraftVersion.id)],
                "banner": "APPROVED" if d.status == "approved" else "DRAFT - AI-assisted. Not an approved record."}
    return out


def get_draft_or_404(db: Session, user: User, draft_id: int) -> Draft:
    d = db.get(Draft, draft_id)
    if not d:
        raise HTTPException(404, "Not found")
    get_case_or_404(db, user, d.case_id)
    return d


class NewDraft(BaseModel):
    doc_type: str


@app.post("/api/v1/cases/{case_id}/drafts", status_code=201)
def create_draft(case_id: int, body: NewDraft, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, *EDITORS)
    if body.doc_type not in drafts_svc.TYPES:
        raise HTTPException(422, "doc_type must be case_diary or chargesheet")
    case = get_case_or_404(db, user, case_id)
    d = Draft(case_id=case.id, doc_type=body.doc_type, sections=drafts_svc.generate(db, case, body.doc_type), author=user.username)
    db.add(d)
    db.commit()
    drafts_svc.snapshot(db, d, user.username, "Generated from case facts")
    used = sorted({i for s in d.sections for i in s["fact_ids"]})
    audit.log(db, user.username, "generate_draft", f"draft:{d.id}", model="template-v1", evidence=used, outcome="draft")
    return draft_out(d, db)


@app.get("/api/v1/cases/{case_id}/drafts")
def list_drafts(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case_or_404(db, user, case_id)
    return [draft_out(d, db, full=False) for d in db.query(Draft).filter_by(case_id=case_id).order_by(Draft.id.desc())]


@app.get("/api/v1/drafts")
def all_drafts(status: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ids = {c.id: c for c in db.scalars(scoped_cases(user))}
    q = db.query(Draft).filter(Draft.case_id.in_(list(ids) or [0])).order_by(Draft.updated_at.desc())
    return [draft_out(d, db, full=False) | {"case_no": ids[d.case_id].case_no} for d in q if not status or d.status == status]


@app.get("/api/v1/drafts/{draft_id}")
def get_draft(draft_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return draft_out(get_draft_or_404(db, user, draft_id), db)


class SectionEdit(BaseModel):
    key: str
    text: str


class DraftEdit(BaseModel):
    sections: list[SectionEdit]


@app.put("/api/v1/drafts/{draft_id}")
def edit_draft(draft_id: int, body: DraftEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, *EDITORS)
    d = get_draft_or_404(db, user, draft_id)
    if d.status not in ("draft", "returned"):
        raise HTTPException(409, f"A draft that is {d.status} cannot be edited")
    edits = {e.key: e.text for e in body.sections}
    new = []
    for s in d.sections:
        if s["key"] in edits and edits[s["key"]] != s["text"]:
            s = {**s, "text": edits[s["key"]], "source": "officer"}  # edited text is officer-entered
        new.append(s)
    d.sections, d.version, d.status = new, d.version + 1, "draft"
    db.commit()
    drafts_svc.snapshot(db, d, user.username, "Edited by " + user.username)
    audit.log(db, user.username, "edit_draft", f"draft:{d.id}", outcome=f"v{d.version}")
    return draft_out(d, db)


@app.post("/api/v1/drafts/{draft_id}/submit")
def submit_draft(draft_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, *EDITORS)
    d = get_draft_or_404(db, user, draft_id)
    if d.status not in ("draft", "returned"):
        raise HTTPException(409, f"A draft that is {d.status} cannot be submitted")
    missing = drafts_svc.unfilled(d.sections)
    if missing:
        raise HTTPException(422, "Complete required sections first: " + ", ".join(missing))
    d.status = "in_review"
    db.commit()
    audit.log(db, user.username, "request_draft_review", f"draft:{d.id}", outcome="in_review")
    return draft_out(d, db)


class DraftDecision(BaseModel):
    decision: str  # approve | return
    comment: str = ""


@app.post("/api/v1/drafts/{draft_id}/review")
def review_draft(draft_id: int, body: DraftDecision, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = get_draft_or_404(db, user, draft_id)
    if user.role not in ("supervisor", "admin") or d.author == user.username:
        audit.log(db, user.username, "draft_review_denied", f"draft:{d.id}", outcome="blocked")
        raise HTTPException(403, "Only a supervisor other than the author can review this draft")
    if body.decision not in ("approve", "return"):
        raise HTTPException(422, "decision must be approve or return")
    if body.decision == "return" and not body.comment.strip():
        raise HTTPException(422, "A comment is required when returning a draft")
    if d.status != "in_review":
        raise HTTPException(409, "Only drafts that are in review can be decided")
    d.status = "approved" if body.decision == "approve" else "returned"
    d.reviewer = user.username
    d.comments = [*d.comments, {"by": user.username, "decision": body.decision, "text": body.comment.strip(),
                                "at": datetime.now(timezone.utc).isoformat()}]
    db.commit()
    drafts_svc.snapshot(db, d, user.username, f"{d.status} by {user.username}")
    audit.log(db, user.username, "review_draft", f"draft:{d.id}", outcome=d.status)
    return draft_out(d, db)


@app.get("/api/v1/drafts/{draft_id}/export", response_class=PlainTextResponse)
def export_draft(draft_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = get_draft_or_404(db, user, draft_id)
    audit.log(db, user.username, "export_draft", f"draft:{d.id}", outcome=d.status)
    return drafts_svc.export_text(d, db.get(Case, d.case_id))


@app.get("/api/v1/dashboard")
def dashboard(district: str | None = None, station: str | None = None, from_month: str | None = None, to_month: str | None = None,
              user: User = Depends(current_user), db: Session = Depends(get_db)):
    in_scope = {c.id: c for c in db.scalars(scoped_cases(user))}  # access scope first; filters only narrow it further
    cases = {i: c for i, c in in_scope.items()
             if (not district or c.district == district) and (not station or c.station == station)
             and (not from_month or c.registered_on[:7] >= from_month) and (not to_month or c.registered_on[:7] <= to_month)}
    ids = list(cases) or [0]
    docs = db.query(Document).filter(Document.case_id.in_(ids)).all()
    stages: dict[str, int] = {}
    for d in docs:
        stages[d.status] = stages.get(d.status, 0) + 1
    cands = [c for c in graph.visible_candidates(db, user) if c["a"]["case_id"] in cases or c["b"]["case_id"] in cases]
    legal_pending = db.query(LegalSuggestion).filter(LegalSuggestion.case_id.in_(ids), LegalSuggestion.status == "suggested").count()
    drafts = db.query(Draft).filter(Draft.case_id.in_(ids)).all()
    by_station: dict[str, int] = {}
    by_month: dict[str, int] = {}
    for c in cases.values():
        by_station[c.station] = by_station.get(c.station, 0) + 1
        by_month[c.registered_on[:7]] = by_month.get(c.registered_on[:7], 0) + 1
    attention = []
    for d in docs:
        if d.status in ("needs_review", "failed"):
            attention.append({"kind": "document", "label": f"{d.doc_type.upper()} in {cases[d.case_id].case_no} is {d.status.replace('_', ' ')}", "case_id": d.case_id})
    for c in cands:
        if c["status"] == "unreviewed":
            attention.append({"kind": "identity", "label": f"Possible match: {c['a']['name']} / {c['b']['name']} ({c['strength']}, {c['score']})", "candidate_id": c["id"]})
    for d in drafts:
        if d.status == "in_review":
            attention.append({"kind": "draft", "label": f"{drafts_svc.TYPES[d.doc_type]} for {cases[d.case_id].case_no} awaits review", "draft_id": d.id, "case_id": d.case_id})
    recent = []
    if user.role in ("admin", "supervisor"):
        recent = [{"at": r.at, "actor": r.actor, "action": r.action, "resource": r.resource, "outcome": r.outcome}
                  for r in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(8))]
    return {"user": {"username": user.username, "role": user.role, "district": user.district},
            "filters": {"district": district, "station": station, "from_month": from_month, "to_month": to_month},
            "options": {"districts": sorted({c.district for c in in_scope.values()}), "stations": sorted({c.station for c in in_scope.values()}),
                        "months": sorted({c.registered_on[:7] for c in in_scope.values()})},
            "counts": {"cases": len(cases), "documents": len(docs), "facts": db.query(Fact).filter(Fact.case_id.in_(ids)).count(),
                       "identity_to_review": sum(1 for c in cands if c["status"] == "unreviewed"),
                       "legal_to_review": legal_pending, "drafts_in_review": sum(1 for d in drafts if d.status == "in_review")},
            "pipeline": stages, "cases_by_station": by_station, "cases_by_month": dict(sorted(by_month.items())),
            "attention": attention[:12], "recent_activity": recent, "data_notice": "Synthetic demo data."}


class CopilotQ(BaseModel):
    question: str
    case_id: int | None = None


@app.post("/api/v1/copilot/query")
def copilot_query(body: CopilotQ, user: User = Depends(current_user), db: Session = Depends(get_db)):
    question = body.question.strip()[:500]
    if not question:
        raise HTTPException(422, "Ask a question")
    if body.case_id is not None:
        get_case_or_404(db, user, body.case_id)  # permission re-checked on every request, including follow-ups
    result = copilot_svc.ask(db, user, question, body.case_id)
    audit.log(db, user.username, "copilot_query", f"case:{body.case_id}" if body.case_id else "scope:all",
              model="llm:" + config.LLM_MODEL if result["mode"] == "llm" else "retrieval-v1",
              evidence=[c["document_id"] for c in result["citations"]], outcome="answered" if result["found"] else "not_found")
    return result


@app.get("/api/v1/analytics/hotspots")
def hotspots(kind: str = "location", user: User = Depends(current_user), db: Session = Depends(get_db)):
    if kind not in ("location", "residence"):
        raise HTTPException(422, "kind must be location or residence")
    return analytics.hotspots(db, user, kind)


@app.get("/api/v1/reviews")
def reviews(type: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = analytics.review_queue(db, user)
    return [i for i in items if not type or i["type"] == type]


def data_quality(db: Session) -> dict:
    types: dict[str, int] = {}
    for f in db.query(Fact):
        types[f.type] = types.get(f.type, 0) + 1
    docs = db.query(Document).all()
    langs: dict[str, int] = {}
    for d in docs:
        langs[d.language] = langs.get(d.language, 0) + 1
    return {"documents": len(docs), "needs_review": sum(d.status == "needs_review" for d in docs), "failed": sum(d.status == "failed" for d in docs),
            "ocr_documents": sum(any(p.ocr for p in d.pages) for d in docs), "languages": langs, "facts_by_type": types,
            "facts_corrected_by_officers": db.query(Fact).filter(Fact.corrected.is_(True)).count(),
            "correction_events": db.query(FactCorrection).count()}


@app.get("/api/v1/governance")
def governance(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "supervisor", "admin")
    docs: dict[str, int] = {}
    for d in db.query(Document):
        docs[d.status] = docs.get(d.status, 0) + 1
    out = {
        "mode": "demo-synthetic",
        "system": {"extractor": config.MODEL_LABEL, "llm_provider": config.LLM_PROVIDER, "llm_model": config.LLM_MODEL,
                   "copilot_llm": config.COPILOT_LLM, "database": config.DATABASE_URL.split(":")[0],
                   "legal_catalogue": {"version": legal.CATALOGUE["catalogue_version"], "verified": legal.CATALOGUE["verified"]}},
        "risk": {"configured": False, "status": "Not configured / not evaluated",
                 "reason": "The challenge brief does not define what 'risk' means, the prediction horizon, the labels or the accuracy metric. "
                           "No risk score is produced, and no accuracy figure is claimed, until the organisers define these in writing."},
        "evaluation": evaluate.evaluate(),
        "data_quality": data_quality(db),
        "users": None,
    }
    if user.role == "admin":
        out["users"] = [{"username": u.username, "role": u.role, "district": u.district or "All districts", "active": u.active} for u in db.query(User).order_by(User.id)]
    return out


# ---------------- Fact correction (EXT-06) ----------------
FACT_TYPES = ("person", "alias", "place", "vehicle", "item", "quantity", "date", "legal_section")


class FactEdit(BaseModel):
    value: str
    reason: str


class FactReason(BaseModel):
    reason: str


class FactNew(BaseModel):
    document_id: int
    page: int
    type: str
    value: str
    span: str
    attributes: dict[str, str] = {}


def _need_reason(reason: str):
    if not reason.strip():
        raise HTTPException(422, "A reason is required")


def _fact_for_edit(db: Session, user: User, fact_id: int) -> Fact:
    require_role(user, "investigator", "supervisor", "admin")
    f = db.get(Fact, fact_id)
    if not f:
        raise HTTPException(404, "Not found")
    get_case_or_404(db, user, f.case_id)
    return f


@app.patch("/api/v1/facts/{fact_id}")
def edit_fact(fact_id: int, body: FactEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .services import normalise, resolve
    f = _fact_for_edit(db, user, fact_id)
    _need_reason(body.reason)
    value = body.value.strip()
    if not value or len(value) > 300:
        raise HTTPException(422, "Value must be 1-300 characters")
    db.add(FactCorrection(fact_id=f.id, case_id=f.case_id, action="edit", old_value=f.original, new_value=value,
                          fact_type=f.type, by=user.username, reason=body.reason.strip()))
    f.original, f.normalised, f.corrected = value, normalise.norm_value(f.type, value), True
    db.commit()
    resolve.refresh(db)
    audit.log(db, user.username, "correct_fact", f"fact:{f.id}", evidence=[f.id], outcome="edited")
    return {"id": f.id, "original": f.original, "corrected": True}


@app.post("/api/v1/facts/{fact_id}/remove")
def remove_fact(fact_id: int, body: FactReason, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .services import resolve
    f = _fact_for_edit(db, user, fact_id)
    _need_reason(body.reason)
    db.add(FactCorrection(fact_id=f.id, case_id=f.case_id, action="remove", old_value=f.original, new_value=None,
                          fact_type=f.type, by=user.username, reason=body.reason.strip()))
    case_id, fid = f.case_id, f.id
    db.delete(f)
    db.commit()
    resolve.refresh(db)
    audit.log(db, user.username, "correct_fact", f"fact:{fid}", outcome="removed")
    return {"removed": fid, "case_id": case_id}


@app.post("/api/v1/cases/{case_id}/facts", status_code=201)
def add_fact(case_id: int, body: FactNew, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .services import normalise, resolve
    require_role(user, "investigator", "supervisor", "admin")
    get_case_or_404(db, user, case_id)
    if body.type not in FACT_TYPES:
        raise HTTPException(422, "Unknown fact type")
    page = db.query(Page).filter_by(document_id=body.document_id, number=body.page).first()
    doc = db.get(Document, body.document_id)
    if not page or not doc or doc.case_id != case_id:
        raise HTTPException(404, "Not found")
    if body.span not in page.text or body.value not in body.span:
        raise HTTPException(422, "The quoted text must appear exactly on that page, and contain the value")
    f = Fact(case_id=case_id, document_id=doc.id, page=page.number, type=body.type, original=body.value.strip(),
             normalised=normalise.norm_value(body.type, body.value), span=body.span, attributes=body.attributes or None,
             model="officer", corrected=True)
    db.add(f)
    db.flush()
    db.add(FactCorrection(fact_id=f.id, case_id=case_id, action="add", old_value=None, new_value=f.original,
                          fact_type=f.type, by=user.username, reason="Added by officer from the source text"))
    db.commit()
    resolve.refresh(db)
    audit.log(db, user.username, "correct_fact", f"fact:{f.id}", evidence=[f.id], outcome="added")
    return {"id": f.id}


@app.get("/api/v1/cases/{case_id}/corrections")
def case_corrections(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case_or_404(db, user, case_id)
    return [{"fact_id": c.fact_id, "action": c.action, "type": c.fact_type, "old": c.old_value, "new": c.new_value,
             "by": c.by, "reason": c.reason, "at": c.at} for c in db.query(FactCorrection).filter_by(case_id=case_id).order_by(FactCorrection.id.desc())]


# ---------------- Administration ----------------
class NewUser(BaseModel):
    username: str
    password: str
    role: str
    district: str | None = None


@app.post("/api/v1/admin/users", status_code=201)
def create_user(body: NewUser, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "admin")
    if body.role not in ("investigator", "supervisor", "analyst", "admin"):
        raise HTTPException(422, "Unknown role")
    if len(body.password) < 8 or not body.username.strip().isidentifier():
        raise HTTPException(422, "Username must be letters/digits/underscore and password at least 8 characters")
    if body.role != "admin" and not body.district:
        raise HTTPException(422, "A district is required for this role")
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "Username already exists")
    db.add(User(username=body.username, password_hash=hash_password(body.password), role=body.role,
                district=None if body.role == "admin" else body.district))
    db.commit()
    audit.log(db, user.username, "create_user", f"user:{body.username}", outcome=body.role)
    return {"username": body.username}


class Active(BaseModel):
    active: bool


@app.post("/api/v1/admin/users/{username}/active")
def set_user_active(username: str, body: Active, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "admin")
    target = db.scalar(select(User).where(User.username == username))
    if not target:
        raise HTTPException(404, "Not found")
    if target.username == user.username:
        raise HTTPException(409, "You cannot deactivate your own account")
    target.active = body.active
    db.commit()
    audit.log(db, user.username, "set_user_active", f"user:{username}", outcome=str(body.active))
    return {"username": username, "active": target.active}


# Serve the built UI (frontend/dist) from the same origin when it exists, so one command runs the whole demo.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="ui")
