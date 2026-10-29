from conftest import case_id, client, hdr

from app.services import legal


def suggest(user, case_no):
    r = client.post(f"/api/v1/cases/{case_id(case_no)}/legal/suggest", headers=hdr(user))
    assert r.status_code == 200
    return {s["ref_id"]: s for s in r.json()["suggestions"]}


def test_suggestions_come_only_from_the_catalogue_and_are_labelled_advisory():
    s = suggest("inv_vizag", "EXC/NRP/041/2025")
    assert set(s) <= set(legal.ENTRIES) and {"APEXC-34A", "APEXC-46"} <= set(s)
    a = s["APEXC-34A"]
    assert a["status"] == "suggested" and a["fact_ids"] and a["passages"] and a["already_cited"]
    assert "Not a legal determination" in a["label"] and a["verified"] is False
    assert all(p["span"] for p in a["passages"])


def test_each_typology_maps_to_its_own_provision():
    assert "NDPS-20" in suggest("inv_vizag", "SEB/ANK/019/2026")
    assert "APPROH-7A" in suggest("inv_chittoor", "Cr.71/2026-PGR")
    assert "NDPS-20" not in suggest("inv_vizag", "EXC/NRP/041/2025")


def test_no_suggestion_when_no_relevant_facts():
    from app.db import SessionLocal
    from app.models import Fact
    with SessionLocal() as db:
        db.query(Fact).filter_by(case_id=case_id("Cr.17/2026-NRT"), type="item").delete()
        db.commit()
    assert "APEXC-34A" not in suggest("inv_guntur", "Cr.17/2026-NRT")


def test_abstains_when_item_found_without_activity():
    from app.db import SessionLocal
    from app.models import Page
    with SessionLocal() as db:
        for p in db.query(Page).all():
            if "Cr.No.: 62/2025" in p.text:
                p.text = "Cr.No.: 62/2025 Date of registration: 09.09.2025\nRamesh Naidu, S/o Venkata Rao, aged 52, R/o Mangalagiri. ID liquor recorded.\n"
        db.commit()
    s = suggest("inv_guntur", "Cr.62/2025-MGR")
    assert s["APEXC-34A"]["status"] == "insufficient" and not s["APEXC-34A"]["passages"]


def test_scope_roles_and_review_rules():
    assert client.post(f"/api/v1/cases/{case_id('Cr.45/2025-TNL')}/legal/suggest", headers=hdr("inv_vizag")).status_code == 404
    cid = case_id("EXC/NRP/041/2025")
    assert client.post(f"/api/v1/cases/{cid}/legal/suggest", headers=hdr("analyst_vizag")).status_code == 403
    sid = suggest("inv_vizag", "EXC/NRP/041/2025")["APEXC-34A"]["id"]
    url = f"/api/v1/legal/{sid}/review"
    assert client.post(url, headers=hdr("inv_vizag"), json={"decision": "accept", "reason": ""}).status_code == 422
    assert client.post(url, headers=hdr("inv_guntur"), json={"decision": "accept", "reason": "x"}).status_code == 404
    r = client.post(url, headers=hdr("inv_vizag"), json={"decision": "accept", "reason": "Facts match panchanama"})
    assert r.json()["status"] == "accepted"
    assert suggest("inv_vizag", "EXC/NRP/041/2025")["APEXC-34A"]["status"] == "accepted"  # re-run keeps the decision
    assert any(a["action"] == "review_legal_suggestion" for a in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())
