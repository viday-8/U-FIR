from conftest import case_id, client, hdr

from app.db import SessionLocal
from app.models import Case, Document, Fact


def first_case(u, case_no):
    return {"id": case_id(case_no)}


def test_every_statement_is_cited_and_cites_real_facts():
    case = first_case("inv_vizag", "EXC/NRP/041/2025")
    brief = client.get(f"/api/v1/cases/{case['id']}/brief", headers=hdr("inv_vizag")).json()
    with SessionLocal() as db:
        real = {f.id for f in db.query(Fact).filter_by(case_id=case["id"])}
    stmts = [s for sec in brief["sections"] for s in sec["statements"]] + brief["conflicts"]
    assert stmts and all(s["fact_ids"] and set(s["fact_ids"]) <= real for s in stmts)
    text = " ".join(s["text"] for s in stmts).lower()
    assert "guilty" not in text and "convicted" not in text
    assert brief["records_reviewed"]["documents"] == 3 and "Not a finding" in brief["notice"]


def test_missing_info_and_no_invention():
    case = first_case("inv_vizag", "EXC/BHM/203/2025")  # decoy case: no seizure panchanama, no vehicle
    brief = client.get(f"/api/v1/cases/{case['id']}/brief", headers=hdr("inv_vizag")).json()
    assert "No vehicle number recorded." in brief["missing"]
    assert any("Seizure Panchanama" in m for m in brief["missing"])
    assert any("Case Diary" in m for m in brief["missing"])


def test_different_ages_across_documents_surface_as_conflict():
    brief = client.get(f"/api/v1/cases/{case_id('SEB/ANK/019/2026')}/brief", headers=hdr("inv_vizag")).json()
    assert any("different age" in c["text"] and "36" in c["text"] and "38" in c["text"] for c in brief["conflicts"])


def test_registration_date_not_in_fir_is_flagged():
    with SessionLocal() as db:
        db.query(Case).filter_by(case_no="Cr.12/2026-KPM").one().registered_on = "2026-02-09"
        db.commit()
    brief = client.get(f"/api/v1/cases/{case_id('Cr.12/2026-KPM')}/brief", headers=hdr("inv_chittoor")).json()
    assert any("registered on 2026-02-09" in c["text"] for c in brief["conflicts"])


def test_conflicting_attribute_is_surfaced_not_resolved():
    case = first_case("inv_vizag", "EXC/NRP/041/2025")
    with SessionLocal() as db:
        f = db.query(Fact).filter_by(case_id=case["id"], type="person", original="Ramesh Babu Naidu").first()
        db.add(Fact(case_id=f.case_id, document_id=f.document_id, page=1, type="person", original="Ramesh Babu Naidu",
                    normalised=f.normalised, span="Ramesh Babu Naidu", attributes={"age": "41"}, model="test"))
        db.commit()
    brief = client.get(f"/api/v1/cases/{case['id']}/brief", headers=hdr("inv_vizag")).json()
    assert any("different age" in c["text"] and "34" in c["text"] and "41" in c["text"] for c in brief["conflicts"])


def test_timeline_sorted_with_sources():
    case = first_case("inv_vizag", "EXC/NRP/041/2025")
    tl = client.get(f"/api/v1/cases/{case['id']}/timeline", headers=hdr("inv_vizag")).json()
    dates = [e["date"] for e in tl]
    assert dates == sorted(dates) and all(e["document_id"] and e["context"] for e in tl)


def test_brief_timeline_document_are_scoped():
    g = first_case("inv_guntur", "Cr.45/2025-TNL")
    v = hdr("inv_vizag")
    for path in (f"/api/v1/cases/{g['id']}/brief", f"/api/v1/cases/{g['id']}/timeline"):
        assert client.get(path, headers=v).status_code == 404
    with SessionLocal() as db:
        gdoc = db.query(Document).filter_by(case_id=g["id"]).first().id
    assert client.get(f"/api/v1/documents/{gdoc}", headers=v).status_code == 404
    assert client.get(f"/api/v1/documents/{gdoc}", headers=hdr("inv_guntur")).status_code == 200


def test_brief_is_audited():
    case = first_case("inv_vizag", "EXC/NRP/041/2025")
    client.get(f"/api/v1/cases/{case['id']}/brief", headers=hdr("inv_vizag"))
    rows = client.get("/api/v1/audit", headers=hdr("sup_vizag")).json()
    assert any(r["action"] == "generate_brief" for r in rows)
