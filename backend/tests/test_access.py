from conftest import case_id, client, hdr

from app import seed
from app.db import SessionLocal
from app.models import Case, Document, Fact
from app.seed_data import CASES
from app.services import extract, llm


def test_requires_auth():
    assert client.get("/api/v1/cases").status_code == 401


def test_bad_login():
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "x"}).status_code == 401


def test_list_is_district_scoped():
    cases = client.get("/api/v1/cases", headers=hdr("inv_vizag")).json()
    assert len(cases) == 5 and all(c["district"] == "Visakhapatnam" for c in cases)
    assert len(client.get("/api/v1/cases", headers=hdr("admin")).json()) == len(CASES)


def test_restricted_case_looks_like_missing():
    restricted = client.get(f"/api/v1/cases/{case_id('Cr.45/2025-TNL')}", headers=hdr("inv_vizag"))
    missing = client.get("/api/v1/cases/99999", headers=hdr("inv_vizag"))
    assert restricted.status_code == missing.status_code == 404 and restricted.json() == missing.json()


def test_audit_role_gate():
    assert client.get("/api/v1/audit", headers=hdr("inv_vizag")).status_code == 403
    assert client.get("/api/v1/audit", headers=hdr("sup_vizag")).status_code == 200


def search(user, q):
    return client.get("/api/v1/search", params={"q": q}, headers=hdr(user)).json()


def test_text_search_respects_scope():
    assert search("inv_guntur", "Rentachintala")["text_hits"]
    assert search("inv_vizag", "Rentachintala")["text_hits"] == []   # other district
    assert search("inv_vizag", "Kuppam")["text_hits"] == []
    assert search("admin", "Kuppam")["text_hits"]
    assert all(h["case_no"].startswith(("EXC", "SEB")) for h in search("inv_vizag", "Narsipatnam")["text_hits"])


def test_fuzzy_name_search_keeps_original_spelling_and_scope():
    names = {m["name"] for m in search("inv_vizag", "Ramesh Babu Naidu")["name_matches"]}
    assert {"Ramesh Babu Naidu", "Rameshbabu Naidu"} <= names and "Ramesh Babu Naiduu" not in names
    assert "Ramesh Babu Naiduu" in {m["name"] for m in search("admin", "Ramesh Babu Naidu")["name_matches"]}
    assert "Muniswamy" in {m["name"] for m in search("inv_chittoor", "Munaswamy")["name_matches"]}


def test_upload_scope_and_validation():
    vizag = hdr("inv_vizag")
    f = {"file": ("a.txt", b"hello", "text/plain")}
    assert client.post("/api/v1/ingest", headers=vizag, data={"case_id": case_id("Cr.45/2025-TNL")}, files=f).status_code == 404
    vid = case_id("EXC/NRP/041/2025")
    bad = {"file": ("a.exe", b"x", "application/octet-stream")}
    assert client.post("/api/v1/ingest", headers=vizag, data={"case_id": vid}, files=bad).status_code == 415
    assert client.post("/api/v1/ingest", headers=hdr("analyst_vizag"), data={"case_id": vid}, files=f).status_code == 403


def test_llm_extraction_drops_unsupported_facts_and_flags_review(monkeypatch):
    def fake(system, user):
        return {"facts": [
            {"type": "person", "value": "Ramesh Babu Naidu", "span": "Ramesh Babu Naidu, S/o Appala Naidu", "attributes": {"father": "Appala Naidu"}},
            {"type": "person", "value": "Invented Person", "span": "Invented Person"},
            {"type": "vehicle", "value": "AP 31 TX 4521", "span": "auto-rickshaw AP 31 TX 4521"},
        ]}
    monkeypatch.setattr(llm, "chat_json", fake)
    monkeypatch.setattr("app.config.EXTRACTOR", "llm")
    with SessionLocal() as db:
        case = db.query(Case).filter_by(case_no="EXC/NRP/041/2025").one()
        doc = db.query(Document).filter_by(case_id=case.id, doc_type="fir").one()
        extract.extract_document(db, doc)
        facts = db.query(Fact).filter_by(document_id=doc.id).all()
        assert {f.original for f in facts} == {"Ramesh Babu Naidu", "AP 31 TX 4521"}
        assert doc.status == "needs_review"


def test_partial_name_queries_return_name_matches_too():
    for q in ("Rameshbabu", "Ramesh Naidu", "Babu"):
        names = {m["name"] for m in search("inv_vizag", q)["name_matches"]}
        assert "Ramesh Babu Naidu" in names or "Rameshbabu Naidu" in names, q
    assert not any(m["name"] == "Munaswamy" for m in search("inv_vizag", "Muna")["name_matches"])  # other district stays hidden
