"""Case management: accused/custody, seizure register, deadlines, compliance checklist, CSV export.
Deliberately plain CRUD. Every route is scoped to cases the caller may access; writes need an editor role and are audited."""
import csv
import io
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from . import audit
from .access import current_user, get_case_or_404, require_role, scoped_cases
from .db import get_db
from .models import Accused, CaseCheck, Draft, Fact, Milestone, Property, User
from .services import profile

router = APIRouter(prefix="/api/v1")
EDITORS = ("investigator", "supervisor", "admin")
ACCUSED_STATUS = Literal["named", "arrested", "remanded", "bailed", "absconding"]
PROPERTY_STATUS = Literal["seized", "sample_sent", "lab_report_received", "produced_in_court", "released", "destroyed"]
PROPERTY_KIND = Literal["liquor", "ganja", "vehicle", "other"]
MILESTONE_KIND = Literal["chargesheet_due", "remand_expiry", "court_hearing", "lab_report_due", "other"]


def _date(v):
    if v in (None, ""):
        return None
    try:
        date.fromisoformat(v)
    except ValueError:
        raise ValueError("Dates must be YYYY-MM-DD")
    return v


class _Dates(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _check(cls, v, info):
        return _date(v) if info.field_name.endswith(("_on", "_till")) else v


class AccusedIn(_Dates):
    name: str
    father_or_spouse: str | None = None
    age: str | None = None
    status: ACCUSED_STATUS = "named"
    arrested_on: str | None = None
    remand_till: str | None = None
    bail_on: str | None = None


class AccusedPatch(_Dates):
    status: ACCUSED_STATUS | None = None
    arrested_on: str | None = None
    remand_till: str | None = None
    bail_on: str | None = None


class PropertyIn(_Dates):
    kind: PROPERTY_KIND
    description: str
    quantity: str | None = None
    custody: str = "Station malkhana"
    status: PROPERTY_STATUS = "seized"
    sample_sent_on: str | None = None
    lab_report_on: str | None = None


class PropertyPatch(_Dates):
    status: PROPERTY_STATUS | None = None
    custody: str | None = None
    sample_sent_on: str | None = None
    lab_report_on: str | None = None


class MilestoneIn(_Dates):
    kind: MILESTONE_KIND
    title: str
    due_on: str


def _row(o, fields):
    return {f: getattr(o, f) for f in fields} | {"id": o.id}


A_FIELDS = ("case_id", "name", "father_or_spouse", "age", "status", "arrested_on", "remand_till", "bail_on")
P_FIELDS = ("case_id", "kind", "description", "quantity", "custody", "status", "sample_sent_on", "lab_report_on")
M_FIELDS = ("case_id", "kind", "title", "due_on", "done")


def _editor(user: User):
    require_role(user, *EDITORS)


def _owned(db: Session, user: User, model, obj_id: int):
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(404, "Not found")
    get_case_or_404(db, user, obj.case_id)  # same 404 for a missing row and a row in another district
    return obj


# ---------------- accused ----------------
@router.get("/cases/{case_id}/accused")
def list_accused(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case_or_404(db, user, case_id)
    return [_row(a, A_FIELDS) for a in db.query(Accused).filter_by(case_id=case_id).order_by(Accused.id)]


@router.post("/cases/{case_id}/accused", status_code=201)
def add_accused(case_id: int, body: AccusedIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    get_case_or_404(db, user, case_id)
    if not body.name.strip():
        raise HTTPException(422, "Name is required")
    a = Accused(case_id=case_id, **body.model_dump() | {"name": body.name.strip()})
    db.add(a)
    db.commit()
    audit.log(db, user.username, "add_accused", f"case:{case_id}", outcome=a.status)
    return _row(a, A_FIELDS)


@router.patch("/accused/{aid}")
def update_accused(aid: int, body: AccusedPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    a = _owned(db, user, Accused, aid)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    audit.log(db, user.username, "update_accused", f"accused:{aid}", outcome=a.status)
    return _row(a, A_FIELDS)


class DeadlineSuggest(BaseModel):
    days: Literal[60, 90]


@router.post("/accused/{aid}/chargesheet-deadline", status_code=201)
def suggest_deadline(aid: int, body: DeadlineSuggest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Adds a chargesheet milestone = first custody date + 60 or 90 days. The officer chooses which; the app does not decide the legal limit."""
    _editor(user)
    a = _owned(db, user, Accused, aid)
    if not a.arrested_on:
        raise HTTPException(422, "Set the arrest date first")
    due = (date.fromisoformat(a.arrested_on) + timedelta(days=body.days)).isoformat()
    m = Milestone(case_id=a.case_id, kind="chargesheet_due", title=f"Chargesheet due for {a.name} ({body.days}-day limit; confirm with the prosecutor)", due_on=due)
    db.add(m)
    db.commit()
    audit.log(db, user.username, "add_milestone", f"case:{a.case_id}", outcome=f"chargesheet_due {due}")
    return _row(m, M_FIELDS)


# ---------------- seizure register ----------------
@router.get("/cases/{case_id}/property")
def list_property(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case_or_404(db, user, case_id)
    return [_row(p, P_FIELDS) for p in db.query(Property).filter_by(case_id=case_id).order_by(Property.id)]


@router.post("/cases/{case_id}/property", status_code=201)
def add_property(case_id: int, body: PropertyIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    get_case_or_404(db, user, case_id)
    if not body.description.strip():
        raise HTTPException(422, "Description is required")
    p = Property(case_id=case_id, **body.model_dump() | {"description": body.description.strip()})
    db.add(p)
    db.commit()
    audit.log(db, user.username, "add_property", f"case:{case_id}", outcome=p.kind)
    return _row(p, P_FIELDS)


@router.post("/cases/{case_id}/property/from-records", status_code=201)
def property_from_records(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Pre-fills the register from vehicles and items found in the documents. Existing entries are never duplicated or changed."""
    _editor(user)
    get_case_or_404(db, user, case_id)
    have = {(p.kind, p.description.lower()) for p in db.query(Property).filter_by(case_id=case_id)}
    facts = db.query(Fact).filter_by(case_id=case_id).order_by(Fact.id).all()
    qty = {}
    for f in facts:
        if f.type == "quantity":
            qty.setdefault((f.document_id, f.page), f.original)
    added = []
    for f in facts:
        if f.type not in ("item", "vehicle"):
            continue
        kind = "vehicle" if f.type == "vehicle" else "ganja" if "ganja" in f.normalised else "liquor"
        key = (kind, f.original.lower())
        if key in have:
            continue
        have.add(key)
        p = Property(case_id=case_id, kind=kind, description=f.original, quantity=None if kind == "vehicle" else qty.get((f.document_id, f.page)))
        db.add(p)
        added.append(p)
    db.commit()
    audit.log(db, user.username, "add_property", f"case:{case_id}", outcome=f"{len(added)} from records")
    return [_row(p, P_FIELDS) for p in added]


@router.patch("/property/{pid}")
def update_property(pid: int, body: PropertyPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    p = _owned(db, user, Property, pid)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    audit.log(db, user.username, "update_property", f"property:{pid}", outcome=p.status)
    return _row(p, P_FIELDS)


# ---------------- deadlines ----------------
def _milestone_out(m: Milestone, case_no: str, today: date) -> dict:
    d = date.fromisoformat(m.due_on)
    state = "done" if m.done else "overdue" if d < today else "soon" if d <= today + timedelta(days=14) else "later"
    return _row(m, M_FIELDS) | {"case_no": case_no, "state": state, "days": (d - today).days}


@router.get("/cases/{case_id}/milestones")
def list_milestones(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    case = get_case_or_404(db, user, case_id)
    today = date.today()
    return [_milestone_out(m, case.case_no, today) for m in db.query(Milestone).filter_by(case_id=case_id).order_by(Milestone.due_on)]


@router.post("/cases/{case_id}/milestones", status_code=201)
def add_milestone(case_id: int, body: MilestoneIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    case = get_case_or_404(db, user, case_id)
    if not body.title.strip():
        raise HTTPException(422, "Title is required")
    m = Milestone(case_id=case_id, kind=body.kind, title=body.title.strip(), due_on=body.due_on)
    db.add(m)
    db.commit()
    audit.log(db, user.username, "add_milestone", f"case:{case_id}", outcome=f"{m.kind} {m.due_on}")
    return _milestone_out(m, case.case_no, date.today())


class Done(BaseModel):
    done: bool


@router.patch("/milestones/{mid}")
def set_milestone_done(mid: int, body: Done, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    m = _owned(db, user, Milestone, mid)
    m.done = body.done
    db.commit()
    audit.log(db, user.username, "update_milestone", f"milestone:{mid}", outcome="done" if m.done else "reopened")
    return _milestone_out(m, get_case_or_404(db, user, m.case_id).case_no, date.today())


@router.get("/deadlines")
def all_deadlines(include_done: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    today = date.today()
    q = db.query(Milestone).filter(Milestone.case_id.in_(list(cases) or [0])).order_by(Milestone.due_on)
    rows = [_milestone_out(m, cases[m.case_id].case_no, today) for m in q if include_done or not m.done]
    return {"today": today.isoformat(), "items": rows,
            "counts": {"overdue": sum(r["state"] == "overdue" for r in rows), "soon": sum(r["state"] == "soon" for r in rows)}}


# ---------------- compliance checklist ----------------
CHECK_LABELS = {
    "fir": "FIR is on record",
    "panchanama": "Seizure panchanama is on record",
    "witnesses": "Two or more witnesses are named in the records",
    "avrec": "Search and seizure was audio-video recorded (BNSS s.105; confirm the requirement with legal)",
    "samples": "Samples have been sent to the lab (where applicable)",
    "deadline": "A chargesheet deadline has been set",
}


@router.get("/cases/{case_id}/checklist")
def checklist(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    case = get_case_or_404(db, user, case_id)
    types = {d.doc_type for d in case.documents}
    witnesses = {f.normalised for f in db.query(Fact).filter_by(case_id=case_id, type="person") if (f.attributes or {}).get("role") == "witness"}
    manual = {c.key: c for c in db.query(CaseCheck).filter_by(case_id=case_id)}
    done = {
        "fir": "fir" in types, "panchanama": "seizure" in types, "witnesses": len(witnesses) >= 2,
        "avrec": bool(manual.get("avrec") and manual["avrec"].done),
        "samples": db.query(Property).filter(Property.case_id == case_id, Property.sample_sent_on.isnot(None)).count() > 0,
        "deadline": db.query(Milestone).filter_by(case_id=case_id, kind="chargesheet_due").count() > 0,
    }
    return {"items": [{"key": k, "label": CHECK_LABELS[k], "done": done[k], "manual": k == "avrec",
                       "by": manual[k].by if k in manual else None} for k in CHECK_LABELS],
            "notice": "A reminder list derived from the records. It is not a legal opinion; confirm requirements with the prosecutor or legal cell."}


class Tick(BaseModel):
    done: bool


@router.post("/cases/{case_id}/checklist/avrec")
def tick_avrec(case_id: int, body: Tick, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _editor(user)
    get_case_or_404(db, user, case_id)
    row = db.get(CaseCheck, (case_id, "avrec"))
    if row:
        row.done, row.by = body.done, user.username
    else:
        db.add(CaseCheck(case_id=case_id, key="avrec", done=body.done, by=user.username))
    db.commit()
    audit.log(db, user.username, "update_checklist", f"case:{case_id}", outcome=f"avrec={body.done}")
    return {"ok": True}


# ---------------- CSV export ----------------
def _safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # stop spreadsheet formula injection


@router.get("/cases/export.csv", response_class=PlainTextResponse)
def export_cases(q: str = "", offence: str = "", station: str = "", status: str = "", district: str = "", from_date: str = "",
                 to_date: str = "", flag: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows, _ = profile.filtered(db, user, q[:200], offence, station, status, district, from_date, to_date, flag)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["case_no", "district", "station", "registered_on", "status", "offence_types", "persons_named", "vehicles", "items", "places", "sections"])
    for r in rows:
        m = r["meta"]
        w.writerow([_safe(x) for x in (r["case_no"], r["district"], r["station"], r["registered_on"], r["status"], "; ".join(m["offence"]),
                                       "; ".join(a["name"] for a in m["accused"]), "; ".join(m["vehicles"]), "; ".join(m["items"]),
                                       "; ".join(m["places"]), "; ".join(m["sections"]))])
    return out.getvalue()


# ---------------- case lifecycle stage ----------------
@router.get("/cases/{case_id}/stage")
def case_stage(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Where the case file stands, derived from what is on record. The first step not yet done is the current one."""
    case = get_case_or_404(db, user, case_id)
    types = {d.doc_type for d in case.documents}
    props = db.query(Property).filter_by(case_id=case_id).all()
    accused = db.query(Accused).filter_by(case_id=case_id).all()
    drafts = db.query(Draft).filter_by(case_id=case_id, doc_type="chargesheet").all()
    hearings = db.query(Milestone).filter_by(case_id=case_id, kind="court_hearing").all()
    steps = [
        ("Registered", True, f"FIR registered {case.registered_on}"),
        ("Seizure recorded", "seizure" in types, "Seizure panchanama on record" if "seizure" in types else "No seizure panchanama yet"),
        ("Samples and lab", any(p.sample_sent_on or p.lab_report_on for p in props), "Sample sent or lab report logged" if any(p.sample_sent_on or p.lab_report_on for p in props) else "No sample or lab date logged"),
        ("Custody", any(a.status in ("arrested", "remanded", "bailed") for a in accused), f"{sum(1 for a in accused if a.status != 'named')} accused with custody status" if accused else "No accused recorded"),
        ("Chargesheet", any(d.status == "approved" for d in drafts), "Chargesheet draft approved" if any(d.status == "approved" for d in drafts) else "In review" if any(d.status == "in_review" for d in drafts) else "Draft started" if drafts else "No chargesheet draft"),
        ("Court", bool(hearings) and all(h.done for h in hearings), f"{sum(1 for h in hearings if not h.done)} hearing(s) pending" if hearings else "No hearing date tracked"),
    ]
    out, current_set = [], False
    for name, done, hint in steps:
        state = "done" if done else ("todo" if current_set else "current")
        current_set = current_set or not done
        out.append({"name": name, "state": state, "hint": hint})
    return {"steps": out, "note": "Derived from the records and the officer's entries; it does not replace the court or department record."}
