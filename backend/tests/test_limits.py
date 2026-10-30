import time

from conftest import case_id, client, hdr

from app import cache
from app.bench import generate
from app.db import SessionLocal
from app.models import Candidate, Case, Document, Entity, Fact, Page
from app.services import graph, resolve


def snapshot(db):
    ents = {e.id: (e.case_id, e.key) for e in db.query(Entity)}
    return {(ents[c.entity_a], ents[c.entity_b], c.score) for c in db.query(Candidate)}


def exhaustive_pairs(db):
    """The old behaviour: score every pair of people from different cases."""
    from itertools import combinations
    ents = db.query(Entity).all()
    vehicles = {}
    from collections import defaultdict
    v = defaultdict(lambda: defaultdict(list))
    for f in db.query(Fact).filter_by(type="vehicle"):
        v[f.case_id][f.normalised].append(f.id)
    out = set()
    for a, b in combinations(sorted(ents, key=lambda e: e.id), 2):
        if a.case_id != b.case_id:
            r = resolve.score_pair(a, b, v)
            if r and r[0] >= resolve.SHOW_MIN:
                out.add(((a.case_id, a.key), (b.case_id, b.key), r[0]))
    return out


# ---------- graph: server-side scope, limit, cache ----------
# ---------- graph: server-side scope, limit, cache ----------
def test_graph_linked_only_focus_and_limit_are_scoped_and_reported():
    full = client.get("/api/v1/relationships", headers=hdr("admin")).json()
    linked = client.get("/api/v1/relationships?linked_only=true", headers=hdr("admin")).json()
    assert 0 < linked["scope"]["shown_nodes"] < full["scope"]["shown_nodes"] and linked["scope"]["total_nodes"] == full["scope"]["total_nodes"]
    assert all(any(e["source"] == n["id"] or e["target"] == n["id"] for e in linked["edges"]) for n in linked["nodes"])
    focus = client.get("/api/v1/relationships", params={"focus": f"case:{case_id('EXC/NRP/114/2025')}", "depth": 1}, headers=hdr("admin")).json()
    assert 1 < focus["scope"]["shown_nodes"] < full["scope"]["shown_nodes"] and focus["scope"]["focus"]
    small = client.get("/api/v1/relationships?limit=20", headers=hdr("admin")).json()
    assert small["scope"]["shown_nodes"] <= 20 and small["scope"]["truncated"] is True
    assert {e["source"] for e in small["edges"]} <= {n["id"] for n in small["nodes"]}  # no edge points at a missing node
    assert all(set(c["node_ids"]) <= {n["id"] for n in small["nodes"]} for c in small["clusters"])
    # scoping happens before reduction: a district user can never see another district through focus or limits
    v = client.get("/api/v1/relationships", params={"focus": f"case:{case_id('Cr.45/2025-TNL')}"}, headers=hdr("inv_vizag")).json()
    assert not any(n["label"].startswith("Cr.") for n in v["nodes"])


def test_graph_cache_is_invalidated_by_changes_and_never_serves_across_districts():
    cache.bump()
    a = client.get("/api/v1/relationships", headers=hdr("inv_vizag")).json()
    b = client.get("/api/v1/relationships", headers=hdr("inv_vizag")).json()
    assert a == b
    cand = next(c for c in client.get("/api/v1/candidates", headers=hdr("inv_vizag")).json() if c["status"] == "unreviewed")
    assert client.post(f"/api/v1/candidates/{cand['id']}/review", headers=hdr("inv_vizag"), json={"decision": "confirm", "reason": "cache test"}).status_code == 200
    after = client.get("/api/v1/relationships", headers=hdr("inv_vizag")).json()
    assert any(e["id"] == f"cand:{cand['id']}" and e["status"] == "confirmed" for e in after["edges"])   # fresh, not stale
    g = client.get("/api/v1/relationships", headers=hdr("inv_guntur")).json()
    assert not any(n["label"].startswith(("EXC", "SEB")) for n in g["nodes"] if n["kind"] == "case")


def test_removed_person_fact_deletes_entity_and_its_unreviewed_links():
    with SessionLocal() as db:
        f = db.query(Fact).filter(Fact.type == "person", Fact.original == "Ramesh Babu Naidu").first()
        cid = f.case_id
        ent_before = db.query(Entity).filter_by(case_id=cid).count()
        for x in db.query(Fact).filter_by(case_id=cid, type="person", original="Ramesh Babu Naidu").all():
            db.delete(x)
        db.commit()
        resolve.refresh(db, {cid})
        assert db.query(Entity).filter_by(case_id=cid).count() == ent_before - 1
        ids = {e.id for e in db.query(Entity)}
        assert all(c.entity_a in ids and c.entity_b in ids for c in db.query(Candidate))  # no dangling links


# ---------- scale: indexed matching equals exhaustive matching, and does far less work ----------
# ---------- scale: indexed matching equals exhaustive matching, and does far less work ----------
def test_indexed_matching_finds_exactly_what_exhaustive_matching_finds_with_far_fewer_comparisons():
    with SessionLocal() as db:
        db.query(Candidate).delete()
        generate(db, 220, seed=7, start=1000)
        resolve.refresh(db)
        indexed = {s for s in snapshot(db) if s[0][1] and s[0][0] and True}
        expected = exhaustive_pairs(db)
        assert indexed == expected and len(expected) > 5          # same links, nothing lost
        ents = resolve.refresh_entities(db)
        scored = sum(1 for _ in resolve.candidate_pairs(ents, None))
        total = len(ents) * (len(ents) - 1) // 2
        assert scored < 0.25 * total                               # a large share of pairs is never compared


def test_incremental_refresh_equals_full_refresh():
    with SessionLocal() as db:
        generate(db, 29, seed=11, start=5000)
        resolve.refresh(db)                                   # the archive as it was
        generate(db, 1, seed=12, start=5029)                  # one new case arrives
        new_case = db.query(Case).order_by(Case.id.desc()).first()
        resolve.refresh(db, {new_case.id})                    # only that case is rescored
        incremental = snapshot(db)
        resolve.refresh(db)                                   # reference: rescore everything
        assert incremental == snapshot(db)


def test_graph_with_hundreds_of_cases_stays_fast_and_bounded():
    with SessionLocal() as db:
        generate(db, 250, seed=3, start=9000)
        resolve.refresh(db)
    cache.bump()
    t = time.perf_counter()
    r = client.get("/api/v1/relationships?linked_only=true&limit=300", headers=hdr("admin"))
    cold = time.perf_counter() - t
    g = r.json()
    assert r.status_code == 200 and g["scope"]["shown_nodes"] <= 300 and cold < 8
    t = time.perf_counter()
    client.get("/api/v1/relationships?linked_only=true&limit=300", headers=hdr("admin"))
    assert time.perf_counter() - t < cold  # cached answer is quicker than building it



# ---------- offence tags: evidence and officer override ----------
def meta(user, case_no):
    return client.get(f"/api/v1/cases/{case_id(case_no)}/meta", headers=hdr(user)).json()


def test_tags_carry_the_evidence_that_produced_them():
    m = meta("inv_vizag", "EXC/BHM/203/2025")
    d = next(x for x in m["offence_detail"] if x["tag"] == "Sale / decoy operation")
    assert d["source"] == "auto" and any("decoy" in r for r in d["reasons"])
    wash = meta("inv_vizag", "EXC/NRP/114/2025")
    assert any("jaggery wash" in r for x in wash["offence_detail"] if x["tag"] == "ID liquor manufacture" for r in x["reasons"])
    assert m["offence_source"] == "auto"


def test_tag_vocabulary_uses_word_boundaries_and_local_terms():
    from app.services.profile import tag_details
    tags = lambda items, text, sec="": [d["tag"] for d in tag_details(set(items), sec, text)]
    assert "ID liquor manufacture" in tags({"id liquor"}, "A navasagaram unit was found")
    assert "Sale / decoy operation" in tags({"ndpl"}, "stock kept for a belt shop")
    assert "ID liquor manufacture" not in tags({"ndpl"}, "the child was stillborn")   # 'still' only as a whole word
    assert "Liquor transport" not in tags(set(), "the vehicle was intercepted")        # no liquor involved
    assert "Ganja / NDPS" in tags(set(), "ganjai packets", "")


def test_officer_can_correct_tags_with_reason_and_it_is_audited_and_filterable():
    cn = "EXC/BHM/203/2025"
    url = f"/api/v1/cases/{case_id(cn)}/tags"
    body = {"offence": ["Illicit liquor possession"], "reason": "Stock was only possessed; no sale proven"}
    assert client.put(url, headers=hdr("analyst_vizag"), json=body).status_code == 403
    assert client.put(url, headers=hdr("inv_guntur"), json=body).status_code == 404
    assert client.put(url, headers=hdr("inv_vizag"), json=body | {"reason": " "}).status_code == 422
    assert client.put(url, headers=hdr("inv_vizag"), json=body | {"offence": ["Made up"]}).status_code == 422
    assert client.put(url, headers=hdr("inv_vizag"), json=body | {"offence": ["Arrack", "Ganja / NDPS", "Liquor transport", "Illicit liquor possession"]}).status_code == 422
    r = client.put(url, headers=hdr("inv_vizag"), json=body)
    assert r.status_code == 200 and r.json()["offence"] == ["Illicit liquor possession"] and r.json()["offence_source"] == "officer"
    assert "no sale proven" in r.json()["offence_detail"][0]["reasons"][0] and "inv_vizag" in r.json()["offence_detail"][0]["reasons"][0]
    ov = client.get("/api/v1/cases/overview", params={"offence": "Illicit liquor possession"}, headers=hdr("inv_vizag")).json()
    assert cn in {i["case_no"] for i in ov["items"]}                                    # the correction drives the filter
    assert cn not in {i["case_no"] for i in client.get("/api/v1/cases/overview", params={"offence": "Sale / decoy operation"}, headers=hdr("inv_vizag")).json()["items"]}
    assert any(a["action"] == "set_case_tags" for a in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())
    back = client.delete(url, headers=hdr("inv_vizag")).json()
    assert back["offence_source"] == "auto" and "Sale / decoy operation" in back["offence"]
