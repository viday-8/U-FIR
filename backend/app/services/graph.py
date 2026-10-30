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


def _clusters(entities: dict[int, Entity], cands: list[dict], cases: dict, veh_by_case: dict) -> list[dict]:
    """Groups of person records that are linked by non-rejected candidate matches. A cluster is a *candidate*
    identity group for a reviewer; it is only labelled confirmed when every link in it has been confirmed."""
    parent = {i: i for i in entities}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    live = [c for c in cands if c["status"] != "rejected"]
    for c in live:
        parent[find(c["a"]["entity_id"])] = find(c["b"]["entity_id"])
    groups = defaultdict(list)
    for i in entities:
        groups[find(i)].append(i)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        links = [c for c in live if c["a"]["entity_id"] in members]
        case_ids = sorted({entities[i].case_id for i in members})
        vehicle_counts = defaultdict(set)
        for cid in case_ids:
            for v in veh_by_case.get(cid, {}):
                vehicle_counts[v].add(cid)
        names = sorted({entities[i].label for i in members})
        out.append({"id": f"cl:{min(members)}", "label": entities[min(members)].label, "names": names,
                    "node_ids": [f"person:{i}" for i in sorted(members)], "case_ids": case_ids,
                    "case_nos": [cases[c].case_no for c in case_ids],
                    "shared_vehicles": sorted({veh_by_case[next(iter(cs))][v] for v, cs in vehicle_counts.items() if len(cs) > 1}),
                    "min_score": min(c["score"] for c in links), "max_score": max(c["score"] for c in links),
                    "status": "confirmed" if all(c["status"] == "confirmed" for c in links) else "needs_review",
                    "candidate_ids": [c["id"] for c in links]})
    return sorted(out, key=lambda c: (-len(c["case_ids"]), -c["max_score"]))


def build_graph(db: Session, user: User, linked_only: bool = False, focus: str | None = None, depth: int = 2, limit: int = 400) -> dict:
    from . import profile
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    profs = profile.profiles(db, cases)
    cands = visible_candidates(db, user)
    nodes, edges = {}, []
    for c in cases.values():
        p = profs[c.id]
        nodes[f"case:{c.id}"] = {"id": f"case:{c.id}", "kind": "case", "label": c.case_no, "case_id": c.id, "station": c.station,
                                 "district": c.district, "registered_on": c.registered_on, "offence": p["offence"],
                                 "documents": len(c.documents)}
    entities = {e.id: e for e in db.query(Entity) if e.case_id in cases}
    for e in entities.values():
        a = e.attributes or {}
        nodes[f"person:{e.id}"] = {"id": f"person:{e.id}", "kind": "person", "label": e.label, "case_id": e.case_id,
                                   "case_no": cases[e.case_id].case_no, "age": a.get("age"), "father_or_spouse": a.get("father_or_spouse"),
                                   "relation": a.get("relation"), "resident": a.get("resident"), "alias": a.get("alias")}
        edges.append({"id": f"in:{e.id}", "source": f"person:{e.id}", "target": f"case:{e.case_id}",
                      "type": "named in", "status": "direct", "evidence": e.fact_ids,
                      "explanation": "Name appears in this case's records."})
    veh, vfacts, vlabel = defaultdict(set), defaultdict(list), {}
    for f in db.query(Fact).filter_by(type="vehicle"):
        if f.case_id in cases:
            veh[f.normalised].add(f.case_id)
            vfacts[(f.normalised, f.case_id)].append(f.id)
            vlabel.setdefault(f.normalised, f.original)
    veh_by_case = defaultdict(dict)
    for key, case_ids in veh.items():
        nodes[f"vehicle:{key}"] = {"id": f"vehicle:{key}", "kind": "vehicle", "label": vlabel[key], "cases": len(case_ids)}
        for cid in case_ids:
            veh_by_case[cid][key] = vlabel[key]
            edges.append({"id": f"veh:{key}:{cid}", "source": f"vehicle:{key}", "target": f"case:{cid}",
                          "type": "recorded in", "status": "direct", "evidence": vfacts[(key, cid)],
                          "explanation": "Vehicle number appears in this case's records."})
    for c in cands:
        if c["status"] == "rejected":
            continue
        label = {"confirmed": "same person (confirmed)"}.get(c["status"], f"{c['strength']} match (unreviewed)")
        edges.append({"id": f"cand:{c['id']}", "candidate_id": c["id"], "source": f"person:{c['a']['entity_id']}",
                      "target": f"person:{c['b']['entity_id']}", "type": label, "score": c["score"], "strength": c["strength"],
                      "status": "confirmed" if c["status"] == "confirmed" else "candidate",
                      "evidence": [e["fact_id"] for e in c["evidence"]],
                      "explanation": "; ".join(s["text"] for s in c["signals"])})
    clusters = _clusters(entities, cands, cases, veh_by_case)
    for cl in clusters:
        for nid in cl["node_ids"]:
            nodes[nid]["cluster_id"] = cl["id"]
    degree = defaultdict(int)
    for e in edges:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    for n in nodes.values():
        n["degree"] = degree[n["id"]]
    stats = {"cases": len(cases), "people": len(entities), "vehicles": len(veh), "links": sum(1 for e in edges if e["status"] != "direct"),
             "clusters": len(clusters)}
    total = len(nodes)
    nodes, edges, clusters, truncated = _scope(nodes, edges, clusters, linked_only, focus, depth, limit)
    return {"nodes": list(nodes.values()), "edges": edges, "clusters": clusters, "stats": stats,
            "scope": {"total_nodes": total, "shown_nodes": len(nodes), "linked_only": linked_only, "focus": focus, "truncated": truncated},
            "notice": "Links show what records have in common. They are not findings of guilt or involvement."}


def _components(nodes: dict, edges: list) -> list[set]:
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        parent[find(e["source"])] = find(e["target"])
    groups = defaultdict(set)
    for n in nodes:
        groups[find(n)].add(n)
    return list(groups.values())


def _scope(nodes: dict, edges: list, clusters: list, linked_only: bool, focus: str | None, depth: int, limit: int):
    """Server-side reduction so big archives stay fast and readable: a focused neighbourhood, or only the networks that
    link cases or people, capped at `limit` nodes (largest, most-linked networks first)."""
    keep = None
    if focus and focus in nodes:
        adj = defaultdict(set)
        for e in edges:
            adj[e["source"]].add(e["target"])
            adj[e["target"]].add(e["source"])
        keep, frontier = {focus}, {focus}
        for _ in range(max(1, min(depth, 4))):
            frontier = {m for n in frontier for m in adj[n]} - keep
            keep |= frontier
    elif linked_only or len(nodes) > limit:
        comps = _components(nodes, edges)
        linked_nodes = {e["source"] for e in edges if e["status"] != "direct"} | {e["target"] for e in edges if e["status"] != "direct"}

        def is_network(c):
            return sum(1 for n in c if nodes[n]["kind"] == "case") >= 2 or bool(c & linked_nodes)
        pool = [c for c in comps if is_network(c)] if linked_only else comps
        pool.sort(key=lambda c: (-bool(c & linked_nodes), -sum(1 for n in c if nodes[n]["kind"] == "case"), -len(c)))
        keep = set()
        for c in pool:
            if len(keep) + len(c) <= limit:
                keep |= c
            elif len(keep) < limit:  # a network larger than the room left: take its best-connected nodes
                keep |= set(sorted(c, key=lambda n: -nodes[n]["degree"])[: limit - len(keep)])
    truncated = False
    if keep is not None:
        if len(keep) > limit:
            keep = set(sorted(keep, key=lambda n: (n != focus, -nodes[n]["degree"]))[:limit])
        truncated = len(keep) < len(nodes) and (not linked_only or bool(focus is None and len(nodes) > limit))
        nodes = {k: v for k, v in nodes.items() if k in keep}
        edges = [e for e in edges if e["source"] in keep and e["target"] in keep]
        clusters = [c for c in clusters if all(n in keep for n in c["node_ids"])]
    return nodes, edges, clusters, truncated


def case_network(db: Session, user: User, case_id: int) -> dict:
    """What this case connects to, from the viewpoint of the user's access. Used after an upload to show its impact."""
    from . import profile
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    ents = {e.id: e for e in db.query(Entity).filter(Entity.case_id == case_id)}
    cands = [c for c in visible_candidates(db, user) if c["status"] != "rejected"
             and (c["a"]["entity_id"] in ents or c["b"]["entity_id"] in ents)]
    people = []
    for e in ents.values():
        links = []
        for c in cands:
            mine, other = (c["a"], c["b"]) if c["a"]["entity_id"] == e.id else (c["b"], c["a"]) if c["b"]["entity_id"] == e.id else (None, None)
            if mine:
                links.append({"candidate_id": c["id"], "status": c["status"], "score": c["score"], "strength": c["strength"],
                              "other": {"entity_id": other["entity_id"], "name": other["name"], "case_id": other["case_id"], "case_no": other["case_no"]},
                              "top_signals": [s["text"] for s in c["signals"] if s["supports"]][:3]})
        a = e.attributes or {}
        people.append({"entity_id": e.id, "name": e.label, "age": a.get("age"), "father_or_spouse": a.get("father_or_spouse"),
                       "resident": a.get("resident"), "links": links})
    mine_v = {f.normalised: f.original for f in db.query(Fact).filter_by(case_id=case_id, type="vehicle")}
    shared = []
    for key, label in mine_v.items():
        others = sorted({f.case_id for f in db.query(Fact).filter_by(type="vehicle", normalised=key) if f.case_id != case_id and f.case_id in cases})
        if others:
            shared.append({"vehicle": label, "cases": [{"id": i, "case_no": cases[i].case_no} for i in others]})
    related = defaultdict(list)
    for p in people:
        for l in p["links"]:
            related[l["other"]["case_id"]].append(f"{p['name']} ↔ {l['other']['name']} ({l['strength']} match)")
    for s in shared:
        for c in s["cases"]:
            related[c["id"]].append(f"Same vehicle {s['vehicle']}")
    return {"case_id": case_id, "people": people, "shared_vehicles": shared,
            "related_cases": [{"id": i, "case_no": cases[i].case_no, "why": w} for i, w in related.items()],
            "summary": {"people": len(people), "possible_matches": sum(len(p["links"]) for p in people),
                        "shared_vehicles": len(shared), "related_cases": len(related)}}
