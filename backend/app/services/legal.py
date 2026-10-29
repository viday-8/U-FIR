"""Legal suggestions from an approved catalogue only. Never invents a provision: output is limited to
catalogue ids, each with the case facts and verbatim passages that triggered it. Abstains when facts are thin."""
import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Case, Document, Fact, LegalSuggestion

CATALOGUE = json.loads((Path(__file__).parent.parent / "data" / "legal_catalogue.json").read_text())
ENTRIES = {e["id"]: e for e in CATALOGUE["entries"]}


def catalogue() -> dict:
    return {k: CATALOGUE[k] for k in ("catalogue_version", "verified", "notice")} | {"entries": [
        {k: e[k] for k in ("id", "act", "section", "title", "summary")} for e in CATALOGUE["entries"]]}


def _sentence(text: str, i: int) -> str:
    start = max(text.rfind(".", 0, i), text.rfind("\n", 0, i)) + 1
    ends = [x for x in (text.find(".", i), text.find("\n", i)) if x != -1]
    end = (min(ends) + 1) if ends else len(text)
    return text[start:end].strip()[:300]


def _passage(pages, words):
    """First sentence containing any activity word, as a verbatim quote."""
    for doc, page in pages:
        for w in words:
            m = re.search(re.escape(w), page.text, re.I)
            if m:
                return {"document_id": doc.id, "page": page.number, "span": _sentence(page.text, m.start())}
    return None


def _entry_result(entry, facts, pages, docs):
    if entry.get("needs_vehicle_seized"):
        vehicles = [f for f in facts if f.type == "vehicle"]
        p = _passage(pages, ["seized", "seizure"])
        seized = [f for f in vehicles if any(f.original in pg.text and re.search("seiz", pg.text, re.I) for _, pg in pages)]
        if seized and p:
            return "suggested", f"A vehicle ({seized[0].original}) is recorded as seized in the records.", [f.id for f in seized], [p]
        return None
    items = [f for f in facts if f.type == "item" and f.normalised in entry["items"]]
    if not items:
        return None
    names = sorted({f.original for f in items})
    related = [f.id for f in facts if f.type in ("quantity", "vehicle")]
    ids = [f.id for f in items] + related
    p = _passage(pages, entry["activities"])
    if p:
        return "suggested", f"Records mention {', '.join(names)} together with a transport, possession, sale or manufacture activity.", ids, [p]
    return "insufficient", f"{', '.join(names)} recorded, but no transport, possession, sale or manufacture activity was found in the text. Officer to confirm the facts.", ids, []


def suggest(db: Session, case: Case) -> list[LegalSuggestion]:
    facts = db.query(Fact).filter_by(case_id=case.id).order_by(Fact.id).all()
    docs = {d.id: d for d in case.documents}
    pages = [(docs[d.id], p) for d in case.documents for p in sorted(d.pages, key=lambda p: p.number)]
    cited = " ".join(f.original for f in facts if f.type == "legal_section")
    existing = {s.ref_id: s for s in db.query(LegalSuggestion).filter_by(case_id=case.id)}
    for entry in CATALOGUE["entries"]:
        r = _entry_result(entry, facts, pages, docs)
        if r is None:
            continue
        status, rationale, ids, passages = r
        row = existing.get(entry["id"]) or LegalSuggestion(case_id=case.id, ref_id=entry["id"], status=status)
        if row.status in ("suggested", "insufficient"):  # never overwrite a human decision
            row.status = status
        sec = entry["section"]
        row.already_cited = bool(re.search(rf"\b{re.escape(sec)}", cited))
        row.rationale, row.fact_ids, row.passages, row.catalogue_version = rationale, ids, passages, CATALOGUE["catalogue_version"]
        db.add(row)
    db.commit()
    return db.query(LegalSuggestion).filter_by(case_id=case.id).order_by(LegalSuggestion.id).all()


def out(s: LegalSuggestion) -> dict:
    e = ENTRIES[s.ref_id]
    return {"id": s.id, "ref_id": s.ref_id, "act": e["act"], "section": e["section"], "title": e["title"],
            "summary": e["summary"], "status": s.status, "rationale": s.rationale, "fact_ids": s.fact_ids,
            "passages": s.passages, "already_cited": s.already_cited, "catalogue_version": s.catalogue_version,
            "verified": CATALOGUE["verified"], "decided_by": s.decided_by, "reason": s.reason,
            "label": "AI-assisted suggestion. Not a legal determination."}
