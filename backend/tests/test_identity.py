from conftest import client, hdr

from app.db import SessionLocal
from app.services import resolve


def cands(user):
    return client.get("/api/v1/candidates", headers=hdr(user)).json()


def find(user, name_a, name_b, case_a=None, case_b=None):
    for c in cands(user):
        names = {c["a"]["name"], c["b"]["name"]}
        cases = {c["a"]["case_no"], c["b"]["case_no"]}
        if names == {name_a, name_b} or (name_a == name_b and names == {name_a}):
            if (not case_a or case_a in cases) and (not case_b or case_b in cases):
                return c
    return None


def test_repeat_offender_is_likely_candidate_with_evidence_and_not_confirmed():
    c = find("inv_vizag", "Ramesh Babu Naidu", "Rameshbabu Naidu")
    assert c["status"] == "unreviewed" and c["strength"] == "likely"
    assert {"name", "father", "vehicle"} <= {s["kind"] for s in c["signals"] if s["supports"]}
    assert c["evidence"] and all(e["span"] for e in c["evidence"])


def test_spelling_and_alias_variants_are_found_in_each_district():
    assert find("inv_chittoor", "Munaswamy", "Muniswamy")["strength"] == "likely"
    assert find("inv_guntur", "Gangadhara Rao", "Gangadhar Rao")["strength"] == "likely"
    assert find("inv_vizag", "Satyam Rao", "Satyam Rao")  # same father and village in two Vizag cases


def test_cross_district_candidate_hidden_from_district_user_but_visible_to_admin():
    assert not any("Cr.45/2025-TNL" in (c["a"]["case_no"], c["b"]["case_no"]) for c in cands("inv_vizag"))
    assert find("admin", "Ramesh Babu Naidu", "Ramesh Babu Naiduu")


def test_lookalikes_with_different_family_are_not_linked():
    assert find("admin", "Ramesh Babu Naidu", "Ramesh Naidu") is None     # S/o Venkata Rao, aged 52
    assert find("admin", "Lakshmi Devi", "Lakshmi Devi") is None           # W/o Raju vs W/o Srinu
    assert find("admin", "Satyam Rao", "Satyam") is None


def test_review_requires_reason_role_and_scope_and_is_audited():
    cand = find("inv_vizag", "Ramesh Babu Naidu", "Rameshbabu Naidu")
    url = f"/api/v1/candidates/{cand['id']}/review"
    assert client.post(url, headers=hdr("analyst_vizag"), json={"decision": "confirm", "reason": "x"}).status_code == 403
    assert client.post(url, headers=hdr("inv_vizag"), json={"decision": "confirm", "reason": ""}).status_code == 422
    cross = find("admin", "Ramesh Babu Naidu", "Ramesh Babu Naiduu")
    assert client.post(f"/api/v1/candidates/{cross['id']}/review", headers=hdr("inv_vizag"),
                       json={"decision": "confirm", "reason": "x"}).status_code == 404
    assert client.post(url, headers=hdr("inv_vizag"), json={"decision": "confirm", "reason": "Same father, vehicle"}).status_code == 200
    assert find("inv_vizag", "Ramesh Babu Naidu", "Rameshbabu Naidu")["status"] == "confirmed"
    assert any(r["action"] == "review_identity_match" and r["outcome"] == "unreviewed->confirmed"
               for r in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())


def test_decision_survives_recomputation():
    with SessionLocal() as db:
        resolve.refresh(db)
    assert find("inv_vizag", "Ramesh Babu Naidu", "Rameshbabu Naidu")["status"] == "confirmed"


def test_graph_edges_have_evidence_and_respect_scope():
    g = client.get("/api/v1/relationships", headers=hdr("inv_vizag")).json()
    assert all(e["evidence"] for e in g["edges"])
    cases = {n["label"] for n in g["nodes"] if n["kind"] == "case"}
    assert len(cases) == 5 and not any(c.startswith("Cr.") for c in cases)
    assert any(e["status"] == "confirmed" for e in g["edges"]) and any(e["status"] == "direct" for e in g["edges"])
    assert "not findings of guilt" in g["notice"]
