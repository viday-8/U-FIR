"""Hotspots and the unified review queue, both built only from cases the user may access."""
from collections import defaultdict

from sqlalchemy.orm import Session

from ..access import scoped_cases
from ..models import Case, Document, Draft, Fact, LegalSuggestion, User
from . import graph

LOCATION_WORDS = ("near", "at", "in")


def hotspots(db: Session, user: User, kind: str = "location") -> dict:
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    firs = {d.id for d in db.query(Document).filter(Document.case_id.in_(list(cases) or [0]), Document.doc_type == "fir")}
    places = defaultdict(set)
    for f in db.query(Fact).filter(Fact.type == "place", Fact.document_id.in_(list(firs) or [0])):
        first = f.span.split()[0].lower() if f.span else ""
        is_location = first in LOCATION_WORDS
        if (kind == "location") == is_location:
            places[f.original].add(f.case_id)
    rows = sorted(({"name": n, "cases": len(ids), "case_ids": sorted(ids), "case_nos": sorted(cases[i].case_no for i in ids)}
                   for n, ids in places.items()), key=lambda r: (-r["cases"], r["name"]))
    by_station, by_month = defaultdict(list), defaultdict(int)
    for c in cases.values():
        by_station[c.station].append(c.id)
        by_month[c.registered_on[:7]] += 1
    covered = {i for r in rows for i in r["case_ids"]}
    months = sorted(by_month)
    heat = [{"station": st, "counts": [sum(1 for i in ids if cases[i].registered_on[:7] == m) for m in months], "total": len(ids)}
            for st, ids in sorted(by_station.items(), key=lambda kv: -len(kv[1]))]
    return {"kind": kind, "places": rows, "heatmap": {"months": months, "rows": heat},
            "stations": sorted(({"name": s, "cases": len(ids), "case_ids": ids} for s, ids in by_station.items()), key=lambda r: -r["cases"]),
            "months": dict(sorted(by_month.items())),
            "coverage": {"cases_with_place": len(covered), "cases_total": len(cases),
                         "note": "Cases whose FIR names no place of this kind are not counted in the place ranking."},
            "method": "Counts distinct cases whose FIR text mentions the place, using the extracted place facts. These are mentions in text, not verified offence coordinates, so there is no map.",
            "caveat": "Patterns in recorded data. Not a prediction of future offences and not evidence about any individual."}


def review_queue(db: Session, user: User) -> list[dict]:
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    ids = list(cases) or [0]
    items = []
    for d in db.query(Document).filter(Document.case_id.in_(ids), Document.status.in_(["needs_review", "failed"])):
        items.append({"type": "extraction", "status": d.status, "label": f"{d.doc_type.upper()} in {cases[d.case_id].case_no}",
                      "reason": "Some extracted facts could not be verified against the text, or nothing was extracted." if d.status == "needs_review" else "Processing failed; retry or check the file.",
                      "case_id": d.case_id, "document_id": d.id, "href": f"#/cases/{d.case_id}", "who": "investigator"})
    for c in graph.visible_candidates(db, user):
        if c["status"] in ("unreviewed", "deferred"):
            items.append({"type": "identity", "status": c["status"], "label": f"{c['a']['name']} / {c['b']['name']}",
                          "reason": f"{c['strength'].capitalize()} match (score {c['score']}) between {c['a']['case_no']} and {c['b']['case_no']}.",
                          "case_id": c["a"]["case_id"], "href": "#/relationships", "who": "investigator or supervisor"})
    for s in db.query(LegalSuggestion).filter(LegalSuggestion.case_id.in_(ids), LegalSuggestion.status.in_(["suggested", "insufficient"])):
        items.append({"type": "legal", "status": s.status, "label": f"{s.ref_id} for {cases[s.case_id].case_no}",
                      "reason": "Advisory suggestion awaiting an officer's decision." if s.status == "suggested" else "Item recorded but activity not found; officer to confirm the facts.",
                      "case_id": s.case_id, "href": f"#/cases/{s.case_id}", "who": "investigator or supervisor"})
    for d in db.query(Draft).filter(Draft.case_id.in_(ids), Draft.status.in_(["in_review", "returned"])):
        items.append({"type": "draft", "status": d.status, "label": f"{d.doc_type.replace('_', ' ').title()} for {cases[d.case_id].case_no}",
                      "reason": f"Submitted by {d.author}; needs a supervisor's decision." if d.status == "in_review" else "Returned to the author with comments.",
                      "case_id": d.case_id, "href": f"#/studio/{d.id}", "who": "supervisor" if d.status == "in_review" else d.author})
    return items
