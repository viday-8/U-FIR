"""Case diary / chargesheet drafts assembled from extracted facts and accepted legal suggestions.
Each section lists the facts it used; sections the system cannot fill stay as visible placeholders
that block submission. Officer edits are marked as officer-entered."""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Case, Draft, DraftVersion, Fact, LegalSuggestion
from . import legal
from .brief import DOC_LABEL, build_brief

PLACEHOLDER = "[Officer to enter"
TYPES = {"case_diary": "Case Diary", "chargesheet": "Chargesheet"}


def _sec(key, title, text, fact_ids=(), required=False, source="system"):
    return {"key": key, "title": title, "text": text, "fact_ids": sorted(set(fact_ids)), "required": required, "source": source}


def _person_line(f: Fact) -> str:
    a = f.attributes or {}
    bits = [f"{a['relation']} {a['father_or_spouse']}" if a.get("father_or_spouse") else None,
            f"aged {a['age']}" if a.get("age") else None, f"R/o {a['resident']}" if a.get("resident") else None,
            f"alias {a['alias']}" if a.get("alias") else None]
    return f"{f.original}" + (f", {', '.join(b for b in bits if b)}" if any(bits) else "")


def _people(facts):
    groups = defaultdict(list)
    for f in facts:
        if f.type == "person":
            groups[f.normalised].append(f)
    out = []
    for g in groups.values():
        best = max(g, key=lambda f: len(f.attributes or {}))
        out.append((best, g, (best.attributes or {}).get("role") == "witness"))
    return out


def _unique(facts, type_):
    seen, out = set(), []
    for f in facts:
        if f.type == type_ and f.normalised not in seen:
            seen.add(f.normalised)
            out.append(f)
    return out


def generate(db: Session, case: Case, doc_type: str) -> list[dict]:
    facts = db.query(Fact).filter_by(case_id=case.id).order_by(Fact.id).all()
    people = _people(facts)
    accused = [(b, g) for b, g, w in people if not w]
    witnesses = [(b, g) for b, g, w in people if w]
    accepted = [s for s in db.query(LegalSuggestion).filter_by(case_id=case.id, status="accepted")]
    cited = _unique(facts, "legal_section")
    brief = build_brief(db, case)

    particulars = _sec("particulars", "Case particulars",
                       f"Case No.: {case.case_no}\nStation: {case.station}, {case.district}\nRegistered on: {case.registered_on}")
    if accepted:
        law_text = "\n".join(f"{legal.ENTRIES[s.ref_id]['act']}, Section {legal.ENTRIES[s.ref_id]['section']} (accepted by {s.decided_by})" for s in accepted)
        law = _sec("law", "Provisions of law", law_text, [i for s in accepted for i in s.fact_ids], required=True)
    else:
        note = f" Sections written in the records: {', '.join(f.original for f in cited)}." if cited else ""
        law = _sec("law", "Provisions of law", f"{PLACEHOLDER}: no legal provision has been accepted in the Legal panel yet.]{note}",
                   [f.id for f in cited], required=True)
    items = _unique(facts, "item") + _unique(facts, "quantity") + _unique(facts, "vehicle")
    property_ = _sec("property", "Property seized / recorded",
                     "\n".join(f"{f.type.capitalize()}: {f.original}" for f in items) or f"{PLACEHOLDER}: no property recorded in the documents.]",
                     [f.id for f in items], required=not items)
    docs = ", ".join(f"{DOC_LABEL.get(d.doc_type, d.doc_type)}" for d in case.documents)
    gaps = brief["missing"] + [c["text"] for c in brief["conflicts"]]
    gaps_sec = _sec("gaps", "Gaps and conflicts in the records (remove once resolved)",
                    "\n".join(f"- {g}" for g in gaps) or "None detected in the extracted records.")

    if doc_type == "case_diary":
        dates = _unique(facts, "date")
        places = _unique(facts, "place")
        return [
            particulars,
            _sec("occurrence", "Dates and places recorded",
                 f"Dates: {', '.join(f.original for f in dates) or 'not recorded'}\nPlaces: {', '.join(f.original for f in places) or 'not recorded'}",
                 [f.id for f in dates + places]),
            _sec("persons", "Persons named", "\n".join(f"- {_person_line(b)}" + (" (witness)" if (b.attributes or {}).get("role") == "witness" else "")
                                                       for b, _, _ in people) or "No persons recorded.", [f.id for _, g, _ in people for f in g]),
            property_, law,
            _sec("steps", "Steps taken today", f"{PLACEHOLDER}: steps taken, statements recorded, places visited, next steps.]", required=True, source="officer"),
            gaps_sec,
        ]
    return [
        particulars,
        _sec("accused", "Persons named (officer to confirm who is charged)",
             "Persons named in the records. The officer must decide who is charged; this list does not designate anyone as accused.\n"
             + ("\n".join(f"{i}. {_person_line(b)}" for i, (b, _) in enumerate(accused, 1)) or f"{PLACEHOLDER}: no persons recorded.]"),
             [f.id for _, g in accused for f in g], required=not accused),
        _sec("facts", "Brief facts", f"{PLACEHOLDER}: brief facts of the case in the officer's words. Recorded items and quantities are listed under Property.]",
             required=True, source="officer"),
        _sec("witnesses", "Witnesses", "\n".join(f"{i}. {_person_line(b)}" for i, (b, _) in enumerate(witnesses, 1)) or "No witnesses recorded in the documents.",
             [f.id for _, g in witnesses for f in g]),
        property_, law,
        _sec("documents", "Documents relied on", docs or f"{PLACEHOLDER}: list of documents.]", required=not docs),
        gaps_sec,
    ]


def unfilled(sections: list[dict]) -> list[str]:
    return [s["title"] for s in sections if s["required"] and PLACEHOLDER in s["text"]]


def snapshot(db: Session, d: Draft, author: str, note: str) -> None:
    db.add(DraftVersion(draft_id=d.id, version=d.version, sections=d.sections, author=author, note=note))
    d.updated_at = datetime.now(timezone.utc)
    db.commit()


def export_text(d: Draft, case: Case) -> str:
    banner = (f"APPROVED by {d.reviewer}" if d.status == "approved"
              else "DRAFT - AI-assisted, NOT an approved record. Do not file or rely on this document.")
    body = "\n\n".join(f"## {s['title']}\n{s['text']}" for s in d.sections)
    return f"{banner}\n\n# {TYPES[d.doc_type]} - {case.case_no}\nVersion {d.version} - status: {d.status}\n\n{body}\n"
