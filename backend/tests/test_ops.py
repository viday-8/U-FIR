from conftest import client, hdr


def test_hotspots_are_scoped_and_explain_their_limits():
    v = client.get("/api/v1/analytics/hotspots", headers=hdr("inv_vizag")).json()
    names = {p["name"] for p in v["places"]}
    assert "Anakapalle" in names and "Tenali" not in names and "Kuppam" not in names
    assert all(c.startswith(("EXC", "SEB")) for p in v["places"] for c in p["case_nos"])
    assert v["coverage"]["cases_total"] == 5 and "not verified offence coordinates" in v["method"] and "Not a prediction" in v["caveat"]
    assert sum(s["cases"] for s in v["stations"]) == 5
    admin = client.get("/api/v1/analytics/hotspots", headers=hdr("admin")).json()
    assert {"Tenali", "Kuppam"} <= {p["name"] for p in admin["places"]}
    res = client.get("/api/v1/analytics/hotspots?kind=residence", headers=hdr("inv_vizag")).json()
    assert "Gavarapalem" in {p["name"] for p in res["places"]}
    assert client.get("/api/v1/analytics/hotspots?kind=bogus", headers=hdr("inv_vizag")).status_code == 422


def test_review_queue_is_unified_scoped_and_has_reasons():
    q = client.get("/api/v1/reviews", headers=hdr("inv_vizag")).json()
    assert {i["type"] for i in q} >= {"identity"} and all(i["reason"] and i["href"] for i in q)
    assert not any("Cr." in i["label"] + i["reason"] for i in q)
    only = client.get("/api/v1/reviews?type=identity", headers=hdr("inv_vizag")).json()
    assert only and all(i["type"] == "identity" for i in only)
    assert len(client.get("/api/v1/reviews", headers=hdr("admin")).json()) >= len(q)


def test_governance_shows_unconfigured_risk_and_measured_evaluation():
    assert client.get("/api/v1/governance", headers=hdr("inv_vizag")).status_code == 403
    g = client.get("/api/v1/governance", headers=hdr("sup_vizag")).json()
    assert g["risk"]["configured"] is False and "does not define" in g["risk"]["reason"]
    ev = g["evaluation"]
    assert ev["documents"] == 6 and ev["gold_facts"] > 30 and ev["missed"] and ev["limits"]
    assert 0 < ev["overall"]["recall"] < 1  # honest: not a perfect score
    assert g["users"] is None
    assert len(client.get("/api/v1/governance", headers=hdr("admin")).json()["users"]) == 7
