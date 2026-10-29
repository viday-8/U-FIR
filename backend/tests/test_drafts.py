from conftest import case_id, client, hdr

CASE = "EXC/NRP/041/2025"


def make(user, doc_type="case_diary", case_no=CASE):
    r = client.post(f"/api/v1/cases/{case_id(case_no)}/drafts", headers=hdr(user), json={"doc_type": doc_type})
    assert r.status_code == 201, r.text
    return r.json()


def fill(draft, user):
    secs = [{"key": s["key"], "text": "Officer text." if "[Officer to enter" in s["text"] else s["text"]} for s in draft["sections"]]
    return client.put(f"/api/v1/drafts/{draft['id']}", headers=hdr(user), json={"sections": secs})


def test_draft_is_marked_draft_sourced_and_cites_facts():
    d = make("inv_vizag", "chargesheet")
    assert d["status"] == "draft" and "Not an approved record" in d["banner"]
    by = {s["key"]: s for s in d["sections"]}
    assert "Ramesh Babu Naidu, S/o Appala Naidu, aged 34" in by["accused"]["text"] and by["accused"]["fact_ids"]
    assert "K. Srinu" in by["witnesses"]["text"] and "AP 31 TX 4521" in by["property"]["text"]
    assert by["facts"]["source"] == "officer" and "[Officer to enter" in by["facts"]["text"]
    assert d["unfilled"]  # facts, law: cannot submit yet


def test_cannot_submit_with_unfilled_required_sections():
    d = make("inv_vizag")
    r = client.post(f"/api/v1/drafts/{d['id']}/submit", headers=hdr("inv_vizag"))
    assert r.status_code == 422 and "Steps taken today" in r.json()["detail"]


def test_accepted_legal_suggestion_flows_into_the_draft():
    client.post(f"/api/v1/cases/{case_id(CASE)}/legal/suggest", headers=hdr("inv_vizag"))
    sug = client.get(f"/api/v1/cases/{case_id(CASE)}/legal", headers=hdr("inv_vizag")).json()["suggestions"]
    sid = next(s["id"] for s in sug if s["ref_id"] == "APEXC-34A")
    client.post(f"/api/v1/legal/{sid}/review", headers=hdr("inv_vizag"), json={"decision": "accept", "reason": "ok"})
    law = next(s for s in make("inv_vizag", "chargesheet")["sections"] if s["key"] == "law")
    assert "Section 34(a)" in law["text"] and "[Officer" not in law["text"]


def test_full_workflow_with_versions_review_and_export():
    d = make("inv_vizag")
    d2 = fill(d, "inv_vizag").json()
    assert d2["version"] == 2 and not d2["unfilled"] and any(s["source"] == "officer" for s in d2["sections"])
    assert len(d2["versions"]) == 2
    assert client.post(f"/api/v1/drafts/{d['id']}/submit", headers=hdr("inv_vizag")).json()["status"] == "in_review"
    assert client.put(f"/api/v1/drafts/{d['id']}", headers=hdr("inv_vizag"), json={"sections": []}).status_code == 409
    exp = client.get(f"/api/v1/drafts/{d['id']}/export", headers=hdr("inv_vizag")).text
    assert exp.startswith("DRAFT - AI-assisted, NOT an approved record")
    assert client.post(f"/api/v1/drafts/{d['id']}/review", headers=hdr("sup_vizag"), json={"decision": "return", "comment": ""}).status_code == 422
    assert client.post(f"/api/v1/drafts/{d['id']}/review", headers=hdr("sup_vizag"), json={"decision": "return", "comment": "Add statements"}).json()["status"] == "returned"
    fill(client.get(f"/api/v1/drafts/{d['id']}", headers=hdr("inv_vizag")).json(), "inv_vizag")
    client.post(f"/api/v1/drafts/{d['id']}/submit", headers=hdr("inv_vizag"))
    ok = client.post(f"/api/v1/drafts/{d['id']}/review", headers=hdr("sup_vizag"), json={"decision": "approve"}).json()
    assert ok["status"] == "approved" and ok["reviewer"] == "sup_vizag" and ok["banner"] == "APPROVED"
    assert client.get(f"/api/v1/drafts/{d['id']}/export", headers=hdr("inv_vizag")).text.startswith("APPROVED by sup_vizag")


def test_unauthorised_or_self_approval_is_blocked_and_audited():
    d = make("sup_vizag")
    fill(d, "sup_vizag"); client.post(f"/api/v1/drafts/{d['id']}/submit", headers=hdr("sup_vizag"))
    url = f"/api/v1/drafts/{d['id']}/review"
    assert client.post(url, headers=hdr("inv_vizag"), json={"decision": "approve"}).status_code == 403   # wrong role
    assert client.post(url, headers=hdr("sup_vizag"), json={"decision": "approve"}).status_code == 403   # own draft
    assert client.get(f"/api/v1/drafts/{d['id']}", headers=hdr("sup_vizag")).json()["status"] == "in_review"
    assert any(a["action"] == "draft_review_denied" for a in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())


def test_drafts_are_scoped_to_the_cases_users_can_access():
    d = make("inv_vizag")
    assert client.get(f"/api/v1/drafts/{d['id']}", headers=hdr("inv_guntur")).status_code == 404
    assert client.post(f"/api/v1/cases/{case_id(CASE)}/drafts", headers=hdr("inv_guntur"), json={"doc_type": "case_diary"}).status_code == 404
    assert client.post(f"/api/v1/cases/{case_id(CASE)}/drafts", headers=hdr("analyst_vizag"), json={"doc_type": "case_diary"}).status_code == 403
    assert all(x["case_no"].startswith(("EXC", "SEB")) for x in client.get("/api/v1/drafts", headers=hdr("inv_vizag")).json())


def test_dashboard_is_scoped_and_lists_work():
    v = client.get("/api/v1/dashboard", headers=hdr("inv_vizag")).json()
    g = client.get("/api/v1/dashboard", headers=hdr("inv_guntur")).json()
    a = client.get("/api/v1/dashboard", headers=hdr("admin")).json()
    assert v["counts"]["cases"] == 5 and g["counts"]["cases"] == 4 and a["counts"]["cases"] == 12
    assert v["counts"]["identity_to_review"] >= 1 and v["recent_activity"] == []
    assert not any("Cr." in x["label"] for x in v["attention"])
    assert a["recent_activity"] and sum(a["pipeline"].values()) == a["counts"]["documents"]
