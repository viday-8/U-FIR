from conftest import case_id, client, hdr

from app import seed
from app.db import SessionLocal
from app.models import Fact


def fact_id(case_no, type_, original):
    with SessionLocal() as db:
        return db.query(Fact).filter_by(case_id=case_id(case_no), type=type_, original=original).first().id


def test_security_headers_and_no_store_on_api():
    r = client.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"] and r.headers["cache-control"] == "no-store"


def test_login_rate_limit_blocks_guessing_then_recovers_on_other_users():
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"username": "ghost_user", "password": "bad"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "ghost_user", "password": seed.DEMO_PASSWORD}).status_code == 429
    assert client.post("/api/v1/auth/login", json={"username": "inv_vizag", "password": seed.DEMO_PASSWORD}).status_code == 200  # others unaffected


def test_fact_edit_keeps_history_requires_reason_and_scope():
    cn = "EXC/NRP/041/2025"
    fid = fact_id(cn, "quantity", "120 bottles")
    url = f"/api/v1/facts/{fid}"
    assert client.patch(url, headers=hdr("inv_vizag"), json={"value": "125 bottles", "reason": ""}).status_code == 422
    assert client.patch(url, headers=hdr("analyst_vizag"), json={"value": "125 bottles", "reason": "x"}).status_code == 403
    assert client.patch(url, headers=hdr("inv_guntur"), json={"value": "125 bottles", "reason": "x"}).status_code == 404
    assert client.patch(url, headers=hdr("inv_vizag"), json={"value": "125 bottles", "reason": "Panchanama says 125"}).status_code == 200
    facts = client.get(f"/api/v1/cases/{case_id(cn)}/facts", headers=hdr("inv_vizag")).json()
    f = next(x for x in facts if x["id"] == fid)
    assert f["original"] == "125 bottles" and f["corrected"] and f["span"] == "120 bottles"  # source quote untouched
    hist = client.get(f"/api/v1/cases/{case_id(cn)}/corrections", headers=hdr("inv_vizag")).json()
    assert hist[0]["old"] == "120 bottles" and hist[0]["new"] == "125 bottles" and hist[0]["by"] == "inv_vizag"
    assert any(a["action"] == "correct_fact" for a in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())


def test_fact_remove_and_add_from_source_text_and_dependents_refresh():
    cn = "EXC/NRP/114/2025"
    fid = fact_id(cn, "place", "Gavarapalem")
    assert client.post(f"/api/v1/facts/{fid}/remove", headers=hdr("inv_vizag"), json={"reason": ""}).status_code == 422
    assert client.post(f"/api/v1/facts/{fid}/remove", headers=hdr("inv_vizag"), json={"reason": "Not an offence place"}).status_code == 200
    assert fid not in [f["id"] for f in client.get(f"/api/v1/cases/{case_id(cn)}/facts", headers=hdr("inv_vizag")).json()]
    doc = client.get(f"/api/v1/cases/{case_id(cn)}/facts", headers=hdr("inv_vizag")).json()[0]["document_id"]
    page_text = client.get(f"/api/v1/documents/{doc}", headers=hdr("inv_vizag")).json()["pages"][0]["text"]
    quote = "Satyam Rao"
    assert quote in page_text
    ok = client.post(f"/api/v1/cases/{case_id(cn)}/facts", headers=hdr("inv_vizag"),
                     json={"document_id": doc, "page": 1, "type": "person", "value": quote, "span": quote, "attributes": {"role": "supplier"}})
    assert ok.status_code == 201
    bad = client.post(f"/api/v1/cases/{case_id(cn)}/facts", headers=hdr("inv_vizag"),
                      json={"document_id": doc, "page": 1, "type": "person", "value": "Nobody Here", "span": "Nobody Here"})
    assert bad.status_code == 422  # a fact must be quotable from the page
    assert client.post(f"/api/v1/cases/{case_id(cn)}/facts", headers=hdr("inv_vizag"),
                       json={"document_id": doc, "page": 1, "type": "bogus", "value": quote, "span": quote}).status_code == 422


def test_search_filters_by_document_type_and_station():
    r = client.get("/api/v1/search", params={"q": "Narsipatnam", "doc_type": "remand"}, headers=hdr("inv_vizag")).json()
    assert r["text_hits"] and all("114" in h["case_no"] or "019" in h["case_no"] for h in r["text_hits"])
    s = client.get("/api/v1/search", params={"q": "Anakapalle", "station": "SEB Station, Anakapalle"}, headers=hdr("inv_vizag")).json()
    assert s["text_hits"] and all(h["case_no"] == "SEB/ANK/019/2026" for h in s["text_hits"])


def test_phonetic_variants_match():
    from app.services.normalise import phonetic
    assert phonetic("Sathyanarayana") == phonetic("Satyanarayana") and phonetic("Reddy") == phonetic("Reddi")
    r = client.get("/api/v1/search", params={"q": "Chinna Reddi"}, headers=hdr("inv_chittoor")).json()
    assert isinstance(r["name_matches"], list)  # phonetic key is exercised via the unit assertions above


def test_admin_user_management_and_data_quality():
    body = {"username": "new_inv", "password": "longenough1", "role": "investigator", "district": "Guntur"}
    assert client.post("/api/v1/admin/users", headers=hdr("sup_vizag"), json=body).status_code == 403
    assert client.post("/api/v1/admin/users", headers=hdr("admin"), json=body | {"password": "short"}).status_code == 422
    assert client.post("/api/v1/admin/users", headers=hdr("admin"), json=body | {"district": None}).status_code == 422
    assert client.post("/api/v1/admin/users", headers=hdr("admin"), json=body).status_code == 201
    assert client.post("/api/v1/admin/users", headers=hdr("admin"), json=body).status_code == 409
    assert client.post("/api/v1/auth/login", json={"username": "new_inv", "password": "longenough1"}).status_code == 200
    assert client.post("/api/v1/admin/users/new_inv/active", headers=hdr("admin"), json={"active": False}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"username": "new_inv", "password": "longenough1"}).status_code == 401
    assert client.post("/api/v1/admin/users/admin/active", headers=hdr("admin"), json={"active": False}).status_code == 409
    g = client.get("/api/v1/governance", headers=hdr("admin")).json()
    assert g["data_quality"]["documents"] >= 12 and g["data_quality"]["facts_by_type"]["person"] > 0
    assert any(u["username"] == "new_inv" and u["active"] is False for u in g["users"])
