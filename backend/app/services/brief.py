"""Case Brief and timeline, assembled only from extracted facts. Every statement carries fact ids.
Wording says "recorded"/"named": the brief never states an allegation as an established finding."""
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Case, Document, Fact, Page

DOC_LABEL = {"fir": "FIR", "diary": "Case Diary", "seizure": "Seizure Panchanama", "progress": "Progress Report", "remand": "Remand Report"}


def _parse(d: str) -> str | None:
    try:
        return datetime.strptime(d.replace(".", "-").replace("/", "-"), "%d-%m-%Y").date().isoformat()
    except ValueError:
        return None


def _stmt(text, facts):
    return {"text": text, "fact_ids": [f.id for f in facts]}


def _person_text(f: Fact) -> str:
    a = f.attributes or {}
    bits = []
    if a.get("father_or_spouse"):
        bits.append(f"{a.get('relation', 'relative')} {a['father_or_spouse']}")
    if a.get("age"):
        bits.append(f"age {a['age']}")
    if a.get("resident"):
        bits.append(f"resident of {a['resident']}")
    return f.original + (f" ({', '.join(bits)})" if bits else "")


def _line_around(text: str, needle: str) -> str:
    i = text.find(needle)
    if i < 0:
        return needle
    start = text.rfind("\n", 0, i) + 1
    end = text.find("\n", i)
    line = text[start: end if end != -1 else len(text)].strip()
    if len(line) <= 150:
        return line
    j = line.find(needle)
    return ("…" if j > 60 else "") + line[max(0, j - 60): j + 90].strip() + "…"


def build_timeline(db: Session, case: Case) -> list[dict]:
    docs = {d.id: d for d in case.documents}
    pages = {(p.document_id, p.number): p.text for d in docs.values() for p in d.pages}
    events, seen = [], set()
    for f in db.query(Fact).filter_by(case_id=case.id, type="date").order_by(Fact.id):
        iso = _parse(f.original)
        if (f.document_id, iso or f.original) in seen:
            continue  # the same date repeated in one document is one event
        seen.add((f.document_id, iso or f.original))
        label = DOC_LABEL.get(docs[f.document_id].doc_type, docs[f.document_id].doc_type)
        events.append({"date": iso, "date_text": f.original, "uncertain": iso is None, "document_id": f.document_id,
                       "doc_type": label, "page": f.page, "fact_id": f.id,
                       "context": _line_around(pages.get((f.document_id, f.page), ""), f.original)})
    return sorted(events, key=lambda e: (e["date"] is None, e["date"] or "", e["fact_id"]))


def build_brief(db: Session, case: Case) -> dict:
    facts = db.query(Fact).filter_by(case_id=case.id).order_by(Fact.id).all()
    by_type = defaultdict(list)
    for f in facts:
        by_type[f.type].append(f)
    sections, missing, conflicts = [], [], []

    # people: group repeated mentions of the same normalised name, prefer the richest mention
    people = defaultdict(list)
    for f in by_type["person"]:
        people[f.normalised].append(f)
    if people:
        stmts = []
        for group in people.values():
            best = max(group, key=lambda f: len(f.attributes or {}))
            role = (best.attributes or {}).get("role")
            verb = "is recorded as a witness" if role == "witness" else "is named in the records"
            stmts.append(_stmt(f"{_person_text(best)} {verb}.", group))
            for key, label in (("age", "age"), ("father_or_spouse", "father/spouse name"), ("resident", "residence")):
                vals = {(f.attributes or {}).get(key) for f in group} - {None}
                if len(vals) > 1:
                    conflicts.append(_stmt(f"Records give different {label} for {best.original}: {', '.join(sorted(vals))}.",
                                           [f for f in group if (f.attributes or {}).get(key)]))
        sections.append({"title": "People named", "statements": stmts})
    else:
        missing.append("No person is named in the extracted records.")

    def listing(title, items, label):
        if not items:
            return False
        groups = defaultdict(list)
        for f in items:
            groups[f.normalised].append(f)
        sections.append({"title": title, "statements": [
            _stmt(f"{label}: {g[0].original}.", g) for g in groups.values()]})
        return True

    listing("Items recorded", by_type["item"], "Item mentioned")
    listing("Quantities recorded", by_type["quantity"], "Quantity mentioned")
    if not listing("Vehicles recorded", by_type["vehicle"], "Vehicle"):
        missing.append("No vehicle number recorded.")
    if not listing("Legal references recorded", by_type["legal_section"], "Referred"):
        missing.append("No legal section recorded in the documents.")
    listing("Places mentioned", by_type["place"], "Place")

    docs = {d.id: d for d in case.documents}
    for pid, group in people.items():
        if all("age" not in (f.attributes or {}) for f in group) and \
                any((f.attributes or {}).get("relation") for f in group):
            missing.append(f"Age not recorded for {group[0].original}.")

    # the registration date on the case should appear among the dates written in the FIR
    fir_dates = [f for f in by_type["date"] if docs[f.document_id].doc_type == "fir"]
    if fir_dates and case.registered_on not in {_parse(f.original) for f in fir_dates}:
        given = ", ".join(sorted({f.original for f in fir_dates}))
        conflicts.append(_stmt(f"Case registered on {case.registered_on}, but the dates written in the FIR are: {given}.", fir_dates))

    seen_types = {d.doc_type for d in case.documents}
    for needed in ("seizure", "diary"):
        if needed not in seen_types:
            missing.append(f"No {DOC_LABEL[needed]} among the documents reviewed.")

    return {"case_id": case.id, "case_no": case.case_no, "station": case.station, "district": case.district,
            "registered_on": case.registered_on, "generated_by": "template-v1",
            "records_reviewed": {"documents": len(case.documents),
                                 "list": [{"id": d.id, "type": DOC_LABEL.get(d.doc_type, d.doc_type), "status": d.status, "language": d.language,
                                      "ocr": any(p.ocr for p in d.pages)} for d in case.documents]},
            "sections": sections, "conflicts": conflicts, "missing": missing,
            "notice": "Summary of what the records state. Not a finding of fact or guilt."}
