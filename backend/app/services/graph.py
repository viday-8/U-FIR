"""Candidate/relationship views. Everything is built from scoped cases only: a link to a case the
user cannot see is not returned, not counted and not hinted at."""
from collections import defaultdict

from sqlalchemy.orm import Session

from ..access import scoped_cases
from ..models import Candidate, Case, Document, Entity, Fact, User
from . import resolve
from .brief import DOC_LABEL


def _evidence(db: Session, ids: list[int], docs: dict[int, Document]) -> list[dict]:
    out = []
    for f in db.query(Fact).filter(Fact.id.in_(ids)) if ids else []:
        d = docs.get(f.document_id)
        out.append({"fact_id": f.id, "case_id": f.case_id, "document_id": f.document_id, "page": f.page,
                    "doc_type": DOC_LABEL.get(d.doc_type, d.doc_type) if d else "Document",
                    "type": f.type, "original": f.original, "span": f.span})
    return out


def visible_candidates(db: Session, user: User, status: str | None = None) -> list[dict]:
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    ents = {e.id: e for e in db.query(Entity) if e.case_id in cases}
    docs = {d.id: d for d in db.query(Document).filter(Document.case_id.in_(list(cases) or [0]))}
    out = []
    for c in db.query(Candidate).order_by(Candidate.score.desc()):
        a, b = ents.get(c.entity_a), ents.get(c.entity_b)
        if not a or not b or (status and c.status != status):
            continue  # both sides must be in the user's scope
        side = lambda e: {"entity_id": e.id, "name": e.label, "case_id": e.case_id,
                          "case_no": cases[e.case_id].case_no, "attributes": e.attributes or {}}
        out.append({"id": c.id, "status": c.status, "score": c.score, "strength": resolve.strength(c.score),
                    "a": side(a), "b": side(b), "signals": c.signals, "missing": c.missing,
                    "evidence": _evidence(db, [i for i in c.evidence if db.get(Fact, i).case_id in cases], docs),
                    "decided_by": c.decided_by, "reason": c.reason})
    return out


def build_graph(db: Session, user: User) -> dict:
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    nodes, edges = {}, []
    for c in cases.values():
        nodes[f"case:{c.id}"] = {"id": f"case:{c.id}", "kind": "case", "label": c.case_no}
    for e in db.query(Entity):
        if e.case_id in cases:
            nodes[f"person:{e.id}"] = {"id": f"person:{e.id}", "kind": "person", "label": e.label}
            edges.append({"id": f"in:{e.id}", "source": f"person:{e.id}", "target": f"case:{e.case_id}",
                          "type": "named in", "status": "direct", "evidence": e.fact_ids,
                          "explanation": "Name appears in this case's records."})
    veh = defaultdict(set)
    vfacts = defaultdict(list)
    for f in db.query(Fact).filter_by(type="vehicle"):
        if f.case_id in cases:
            veh[f.normalised].add(f.case_id)
            vfacts[(f.normalised, f.case_id)].append(f.id)
    for key, case_ids in veh.items():
        label = db.query(Fact).filter_by(type="vehicle", normalised=key).first().original
        nodes[f"vehicle:{key}"] = {"id": f"vehicle:{key}", "kind": "vehicle", "label": label}
        for cid in case_ids:
            edges.append({"id": f"veh:{key}:{cid}", "source": f"vehicle:{key}", "target": f"case:{cid}",
                          "type": "recorded in", "status": "direct", "evidence": vfacts[(key, cid)],
                          "explanation": "Vehicle number appears in this case's records."})
    for c in visible_candidates(db, user):
        if c["status"] == "rejected":
            continue
        label = {"confirmed": "same person (confirmed)"}.get(c["status"], f"{c['strength']} match (unreviewed)")
        edges.append({"id": f"cand:{c['id']}", "candidate_id": c["id"], "source": f"person:{c['a']['entity_id']}",
                      "target": f"person:{c['b']['entity_id']}", "type": label,
                      "status": "confirmed" if c["status"] == "confirmed" else "candidate",
                      "evidence": [e["fact_id"] for e in c["evidence"]],
                      "explanation": "; ".join(s["text"] for s in c["signals"])})
    return {"nodes": list(nodes.values()), "edges": edges,
            "notice": "Links show what records have in common. They are not findings of guilt or involvement."}
