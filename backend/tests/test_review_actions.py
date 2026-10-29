from conftest import case_id, client, hdr

from app.db import SessionLocal
from app.models import Document

CASE = "EXC/NRP/041/2025"


def make_flagged():
    with SessionLocal() as db:
        d = db.query(Document).filter_by(case_id=case_id(CASE), doc_type="diary").one()
        d.status = "needs_review"
        db.commit()
        return d.id


def test_mark_reviewed_needs_note_role_scope_and_is_audited():
    doc = make_flagged()
    url = f"/api/v1/documents/{doc}/mark-reviewed"
    assert client.post(url, headers=hdr("inv_vizag"), json={"note": "  "}).status_code == 422
    assert client.post(url, headers=hdr("analyst_vizag"), json={"note": "x"}).status_code == 403
    assert client.post(url, headers=hdr("inv_guntur"), json={"note": "x"}).status_code == 404
    r = client.post(url, headers=hdr("inv_vizag"), json={"note": "Compared with the original page; names match"})
    assert r.json()["status"] == "reviewed"
    d = client.get(f"/api/v1/documents/{doc}", headers=hdr("inv_vizag")).json()
    assert d["status"] == "reviewed" and d["reviewed_by"] == "inv_vizag" and "match" in d["review_note"]
    assert client.post(url, headers=hdr("inv_vizag"), json={"note": "again"}).status_code == 409  # only flagged documents
    assert any(a["action"] == "review_document" for a in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())
    queue = client.get("/api/v1/reviews?type=extraction", headers=hdr("inv_vizag")).json()
    assert not any(i.get("document_id") == doc for i in queue)  # leaves the queue once reviewed


def test_retry_reprocesses_a_failed_document_and_is_scoped():
    with SessionLocal() as db:
        d = db.query(Document).filter_by(case_id=case_id(CASE), doc_type="seizure").one()
        d.status, doc = "failed", d.id
        db.commit()
    queue = client.get("/api/v1/reviews?type=extraction", headers=hdr("inv_vizag")).json()
    assert any(i["document_id"] == doc and i["status"] == "failed" for i in queue)
    assert client.post(f"/api/v1/documents/{doc}/retry", headers=hdr("inv_guntur")).status_code == 404
    assert client.post(f"/api/v1/documents/{doc}/retry", headers=hdr("analyst_vizag")).status_code == 403
    r = client.post(f"/api/v1/documents/{doc}/retry", headers=hdr("inv_vizag"))
    assert r.status_code == 200 and r.json()["status"] == "indexed"
    assert client.post(f"/api/v1/documents/{doc}/retry", headers=hdr("inv_vizag")).status_code == 409  # healthy now


def test_dashboard_filters_narrow_but_never_widen_scope():
    base = client.get("/api/v1/dashboard", headers=hdr("inv_vizag")).json()
    assert base["counts"]["cases"] == 5 and base["options"]["districts"] == ["Visakhapatnam"]
    st = client.get("/api/v1/dashboard", params={"station": "SEB Station, Anakapalle"}, headers=hdr("inv_vizag")).json()
    assert st["counts"]["cases"] == 1 and set(st["cases_by_station"]) == {"SEB Station, Anakapalle"}
    per = client.get("/api/v1/dashboard", params={"from_month": "2026-01", "to_month": "2026-12"}, headers=hdr("inv_vizag")).json()
    assert per["counts"]["cases"] == 2 and all(m >= "2026-01" for m in per["cases_by_month"])
    other = client.get("/api/v1/dashboard", params={"district": "Guntur"}, headers=hdr("inv_vizag")).json()
    assert other["counts"]["cases"] == 0  # a district filter cannot reveal another district
    assert "Cr." not in " ".join(a["label"] for a in other["attention"])
    admin = client.get("/api/v1/dashboard", params={"district": "Chittoor"}, headers=hdr("admin")).json()
    assert admin["counts"]["cases"] == 3 and len(admin["options"]["districts"]) == 3
