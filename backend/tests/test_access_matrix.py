"""Every endpoint x every role. Expected statuses are the security contract of the application."""
import pytest
from conftest import case_id, client, hdr

from app.db import SessionLocal
from app.models import Document, Fact

ROLES = ["anon", "inv_vizag", "sup_vizag", "analyst_vizag", "inv_guntur", "admin"]
OK, UNAUTH, FORBID, HIDDEN = 200, 401, 403, 404


def ctx():
    cid = case_id("EXC/NRP/041/2025")
    with SessionLocal() as db:
        doc = db.query(Document).filter_by(case_id=cid, doc_type="fir").one().id
        fact = db.query(Fact).filter_by(case_id=cid, type="quantity").first().id
    return {"cid": cid, "doc": doc, "fact": fact}


def call(role, method, path, body=None):
    h = {} if role == "anon" else hdr(role)
    return client.request(method, "/api/v1" + path.format(**ctx()), headers=h, json=body)


# (method, path, body, {role: status})  -- roles not listed follow the "default" key
READ_SCOPED = {"anon": UNAUTH, "inv_vizag": OK, "sup_vizag": OK, "analyst_vizag": OK, "inv_guntur": HIDDEN, "admin": OK}
ANY_LOGGED_IN = {"anon": UNAUTH, "inv_vizag": OK, "sup_vizag": OK, "analyst_vizag": OK, "inv_guntur": OK, "admin": OK}
EDITOR_SCOPED = {"anon": UNAUTH, "analyst_vizag": FORBID, "inv_guntur": HIDDEN}   # others succeed (checked as non-error)
SUPERVISOR_ONLY = {"anon": UNAUTH, "inv_vizag": FORBID, "analyst_vizag": FORBID, "inv_guntur": FORBID, "sup_vizag": OK, "admin": OK}

READS = [
    ("GET", "/cases", None, ANY_LOGGED_IN), ("GET", "/cases/overview", None, ANY_LOGGED_IN),
    ("GET", "/cases/{cid}", None, READ_SCOPED), ("GET", "/cases/{cid}/meta", None, READ_SCOPED),
    ("GET", "/cases/{cid}/network", None, READ_SCOPED), ("GET", "/cases/{cid}/brief", None, READ_SCOPED),
    ("GET", "/cases/{cid}/timeline", None, READ_SCOPED), ("GET", "/cases/{cid}/facts", None, READ_SCOPED),
    ("GET", "/cases/{cid}/legal", None, READ_SCOPED), ("GET", "/cases/{cid}/drafts", None, READ_SCOPED),
    ("GET", "/cases/{cid}/corrections", None, READ_SCOPED), ("GET", "/documents/{doc}", None, READ_SCOPED),
    ("GET", "/search?q=Naidu", None, ANY_LOGGED_IN), ("GET", "/search/suggest?q=nai", None, ANY_LOGGED_IN),
    ("GET", "/candidates", None, ANY_LOGGED_IN), ("GET", "/relationships", None, ANY_LOGGED_IN),
    ("GET", "/dashboard", None, ANY_LOGGED_IN), ("GET", "/reviews", None, ANY_LOGGED_IN),
    ("GET", "/analytics/hotspots", None, ANY_LOGGED_IN), ("GET", "/legal/catalogue", None, ANY_LOGGED_IN),
    ("GET", "/drafts", None, ANY_LOGGED_IN), ("GET", "/audit", None, SUPERVISOR_ONLY), ("GET", "/governance", None, SUPERVISOR_ONLY),
    ("POST", "/copilot/query", {"question": "vehicle AP 31 TX 4521"}, ANY_LOGGED_IN),
]


@pytest.mark.parametrize("method,path,body,expect", READS, ids=[f"{m} {p}" for m, p, _, _ in READS])
def test_read_endpoints_by_role(method, path, body, expect):
    for role, status in expect.items():
        assert call(role, method, path, body).status_code == status, f"{role} {method} {path}"


WRITES = [
    ("POST", "/cases/{cid}/legal/suggest", None), ("POST", "/cases/{cid}/drafts", {"doc_type": "case_diary"}),
    ("POST", "/cases/{cid}/facts", {"document_id": 0, "page": 1, "type": "person", "value": "x", "span": "x"}),
    ("PATCH", "/facts/{fact}", {"value": "130 bottles", "reason": "check"}),
    ("POST", "/facts/{fact}/remove", {"reason": ""}),
    ("POST", "/documents/{doc}/retry", None), ("POST", "/documents/{doc}/mark-reviewed", {"note": ""}),
    ("POST", "/cases", {"case_no": "X/1/2026", "district": "Visakhapatnam", "station": "S", "registered_on": "2026-01-01"}),
]


@pytest.mark.parametrize("method,path,body", WRITES, ids=[f"{m} {p}" for m, p, _ in WRITES])
def test_write_endpoints_enforce_role_and_scope(method, path, body):
    assert call("anon", method, path, body).status_code == UNAUTH
    assert call("analyst_vizag", method, path, body).status_code == FORBID     # read-only role never writes
    if "{cid}" in path or "{doc}" in path or "{fact}" in path:
        assert call("inv_guntur", method, path, body).status_code in (HIDDEN, FORBID)  # other district: no access, no hint
    for role in ("inv_vizag", "sup_vizag"):
        assert call(role, method, path, body).status_code not in (UNAUTH, FORBID, 500), f"{role} {method} {path}"


def test_ingest_and_intake_roles():
    f = {"file": ("a.txt", b"hello world", "text/plain")}
    cid = case_id("EXC/NRP/041/2025")
    for role, status in {"anon": 401, "analyst_vizag": 403, "inv_guntur": 404}.items():
        h = {} if role == "anon" else hdr(role)
        assert client.post("/api/v1/ingest", headers=h, data={"case_id": cid}, files=f).status_code == status, role
    assert client.post("/api/v1/intake/analyze", headers={}, files=[("files", f["file"])]).status_code == 401
    assert client.post("/api/v1/intake/analyze", headers=hdr("analyst_vizag"), files=[("files", f["file"])]).status_code == 403
    assert client.post("/api/v1/intake/analyze", headers=hdr("inv_vizag"), files=[("files", f["file"])]).status_code == 200


def test_admin_endpoints_admin_only():
    body = {"username": "matrix_user", "password": "longenough1", "role": "analyst", "district": "Guntur"}
    for role in ("anon", "inv_vizag", "sup_vizag", "analyst_vizag", "inv_guntur"):
        h = {} if role == "anon" else hdr(role)
        assert client.post("/api/v1/admin/users", headers=h, json=body).status_code == (401 if role == "anon" else 403), role
        assert client.post("/api/v1/admin/users/inv_vizag/active", headers=h, json={"active": False}).status_code == (401 if role == "anon" else 403), role
    assert client.post("/api/v1/admin/users", headers=hdr("admin"), json=body).status_code == 201


def test_draft_endpoints_are_scoped():
    d = client.post(f"/api/v1/cases/{case_id('EXC/NRP/041/2025')}/drafts", headers=hdr("inv_vizag"), json={"doc_type": "case_diary"}).json()["id"]
    for path, method, body in [(f"/drafts/{d}", "GET", None), (f"/drafts/{d}/export", "GET", None), (f"/drafts/{d}", "PUT", {"sections": []}),
                               (f"/drafts/{d}/submit", "POST", None), (f"/drafts/{d}/review", "POST", {"decision": "approve"})]:
        assert client.request(method, "/api/v1" + path, headers=hdr("inv_guntur"), json=body).status_code in (404, 403), path
        assert client.request(method, "/api/v1" + path, json=body).status_code == 401, path


def test_candidate_and_legal_review_endpoints_are_scoped():
    c = next(x for x in client.get("/api/v1/candidates", headers=hdr("inv_vizag")).json())
    legal = client.post(f"/api/v1/cases/{case_id('EXC/NRP/041/2025')}/legal/suggest", headers=hdr("inv_vizag")).json()["suggestions"][0]["id"]
    for path, body in [(f"/candidates/{c['id']}/review", {"decision": "confirm", "reason": "x"}), (f"/legal/{legal}/review", {"decision": "accept", "reason": "x"})]:
        assert client.post("/api/v1" + path, json=body).status_code == 401
        assert client.post("/api/v1" + path, headers=hdr("analyst_vizag"), json=body).status_code == 403
        assert client.post("/api/v1" + path, headers=hdr("inv_guntur"), json=body).status_code == 404


def test_no_cross_district_data_in_any_list_endpoint_for_district_users():
    import json
    for path in ["/cases", "/cases/overview", "/search?q=Kuppam", "/search?q=Tenali", "/candidates", "/relationships", "/dashboard", "/reviews", "/analytics/hotspots", "/drafts"]:
        data = client.get("/api/v1" + path, headers=hdr("inv_vizag")).json()
        if isinstance(data, dict):
            data.pop("query", None)  # the user's own search text is echoed back; that is not data from the records
        blob = json.dumps(data)
        for secret in ("Cr.45/2025", "Cr.12/2026", "Cr.58/2026", "Munaswamy", "Gangadhar", "Kuppam", "Tenali", "Rentachintala"):
            assert secret not in blob, f"{secret} leaked through {path}"
    assert "Visakhapatnam" not in json.dumps(client.get("/api/v1/cases/overview", headers=hdr("inv_chittoor")).json())
