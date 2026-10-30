from datetime import date, timedelta

from conftest import case_id, client, hdr

CASE = "EXC/NRP/041/2025"


def url(path):
    return f"/api/v1/cases/{case_id(CASE)}{path}"


# ---------- accused + deadline suggestion ----------
def test_accused_crud_roles_scope_and_validation():
    body = {"name": "Ramesh Babu Naidu", "father_or_spouse": "Appala Naidu", "age": "34", "status": "arrested", "arrested_on": "2025-03-14"}
    assert client.post(url("/accused"), json=body).status_code == 401
    assert client.post(url("/accused"), headers=hdr("analyst_vizag"), json=body).status_code == 403
    assert client.post(url("/accused"), headers=hdr("inv_guntur"), json=body).status_code == 404
    assert client.post(url("/accused"), headers=hdr("inv_vizag"), json=body | {"arrested_on": "14-03-2025"}).status_code == 422
    assert client.post(url("/accused"), headers=hdr("inv_vizag"), json=body | {"status": "guilty"}).status_code == 422   # no verdict-like status
    assert client.post(url("/accused"), headers=hdr("inv_vizag"), json=body | {"name": " "}).status_code == 422
    a = client.post(url("/accused"), headers=hdr("inv_vizag"), json=body)
    assert a.status_code == 201
    aid = a.json()["id"]
    assert client.get(url("/accused"), headers=hdr("analyst_vizag")).json()[0]["name"] == "Ramesh Babu Naidu"   # read-only roles can view
    assert client.get(url("/accused"), headers=hdr("inv_guntur")).status_code == 404
    assert client.patch(f"/api/v1/accused/{aid}", headers=hdr("inv_guntur"), json={"status": "bailed"}).status_code == 404
    r = client.patch(f"/api/v1/accused/{aid}", headers=hdr("sup_vizag"), json={"status": "remanded", "remand_till": "2025-03-28"})
    assert r.json()["status"] == "remanded" and r.json()["remand_till"] == "2025-03-28"


def test_chargesheet_deadline_is_arrest_date_plus_chosen_days_and_needs_arrest_date():
    aid = client.post(url("/accused"), headers=hdr("inv_vizag"), json={"name": "Satyam Rao", "status": "named"}).json()["id"]
    d = f"/api/v1/accused/{aid}/chargesheet-deadline"
    assert client.post(d, headers=hdr("inv_vizag"), json={"days": 60}).status_code == 422             # no arrest date yet
    client.patch(f"/api/v1/accused/{aid}", headers=hdr("inv_vizag"), json={"status": "arrested", "arrested_on": "2025-08-02"})
    assert client.post(d, headers=hdr("inv_vizag"), json={"days": 45}).status_code == 422              # only 60 or 90
    m = client.post(d, headers=hdr("inv_vizag"), json={"days": 90})
    assert m.status_code == 201 and m.json()["due_on"] == "2025-10-31" and "confirm with the prosecutor" in m.json()["title"]
    assert client.post(d, headers=hdr("analyst_vizag"), json={"days": 60}).status_code == 403


# ---------- seizure register ----------
def test_register_prefills_from_records_once_and_tracks_samples():
    r = client.post(url("/property/from-records"), headers=hdr("inv_vizag"))
    assert r.status_code == 201
    added = r.json()
    kinds = {p["kind"] for p in added}
    assert "vehicle" in kinds and "liquor" in kinds and any(p["description"] == "AP 31 TX 4521" for p in added)
    assert any(p["quantity"] for p in added if p["kind"] == "liquor")
    again = client.post(url("/property/from-records"), headers=hdr("inv_vizag")).json()
    assert again == []                                                                       # never duplicates
    pid = next(p["id"] for p in added if p["kind"] == "liquor")
    assert client.patch(f"/api/v1/property/{pid}", headers=hdr("inv_vizag"), json={"status": "sample_sent", "sample_sent_on": "2025-03-16"}).json()["status"] == "sample_sent"
    assert client.patch(f"/api/v1/property/{pid}", headers=hdr("inv_vizag"), json={"status": "stolen"}).status_code == 422
    assert client.patch(f"/api/v1/property/{pid}", headers=hdr("inv_guntur"), json={"status": "released"}).status_code == 404
    assert client.post(url("/property"), headers=hdr("analyst_vizag"), json={"kind": "liquor", "description": "x"}).status_code == 403
    assert client.get(url("/property"), headers=hdr("inv_guntur")).status_code == 404


# ---------- deadlines ----------
def test_milestones_states_dashboard_and_scope():
    today = date.today()
    cid = case_id(CASE)
    def add(title, delta, kind="court_hearing"):
        return client.post(url("/milestones"), headers=hdr("inv_vizag"), json={"kind": kind, "title": title, "due_on": (today + timedelta(days=delta)).isoformat()}).json()
    late, soon, later = add("Past hearing", -3), add("Hearing next week", 5), add("Far hearing", 60)
    assert (late["state"], soon["state"], later["state"]) == ("overdue", "soon", "later")
    assert client.post(url("/milestones"), headers=hdr("inv_vizag"), json={"kind": "court_hearing", "title": "x", "due_on": "tomorrow"}).status_code == 422
    assert client.post(url("/milestones"), headers=hdr("analyst_vizag"), json={"kind": "other", "title": "x", "due_on": "2030-01-01"}).status_code == 403
    dash = client.get("/api/v1/dashboard", headers=hdr("inv_vizag")).json()
    assert dash["deadlines"]["overdue"] >= 1 and dash["deadlines"]["soon"] >= 1
    assert any(a["kind"] == "deadline" and "OVERDUE" in a["label"] for a in dash["attention"])
    g = client.get("/api/v1/dashboard", headers=hdr("inv_guntur")).json()
    assert g["deadlines"]["overdue"] == 0 and not any("EXC/NRP" in a["label"] for a in g["attention"])   # other district sees nothing
    lst = client.get("/api/v1/deadlines", headers=hdr("inv_vizag")).json()
    assert {i["title"] for i in lst["items"]} >= {"Past hearing", "Hearing next week"} and lst["counts"]["overdue"] >= 1
    assert client.get("/api/v1/deadlines", headers=hdr("inv_guntur")).json()["items"] == []
    done = client.patch(f"/api/v1/milestones/{late['id']}", headers=hdr("inv_vizag"), json={"done": True}).json()
    assert done["state"] == "done"
    assert "Past hearing" not in {i["title"] for i in client.get("/api/v1/deadlines", headers=hdr("inv_vizag")).json()["items"]}
    assert client.patch(f"/api/v1/milestones/{later['id']}", headers=hdr("inv_guntur"), json={"done": True}).status_code == 404
    assert any(a["action"] == "add_milestone" for a in client.get("/api/v1/audit", headers=hdr("sup_vizag")).json())
    assert cid


# ---------- checklist ----------
def test_checklist_is_derived_from_records_with_one_manual_tick():
    items = {i["key"]: i for i in client.get(url("/checklist"), headers=hdr("inv_vizag")).json()["items"]}
    assert items["fir"]["done"] and items["panchanama"]["done"] and items["witnesses"]["done"]       # K. Srinu + P. Lakshmi
    assert items["deadline"]["done"] and items["samples"]["done"]                                      # created by the tests above
    assert not items["avrec"]["done"] and items["avrec"]["manual"]
    assert client.post(url("/checklist/avrec"), headers=hdr("analyst_vizag"), json={"done": True}).status_code == 403
    assert client.post(url("/checklist/avrec"), headers=hdr("inv_guntur"), json={"done": True}).status_code == 404
    assert client.post(url("/checklist/avrec"), headers=hdr("inv_vizag"), json={"done": True}).status_code == 200
    after = {i["key"]: i for i in client.get(url("/checklist"), headers=hdr("sup_vizag")).json()["items"]}
    assert after["avrec"]["done"] and after["avrec"]["by"] == "inv_vizag"
    bare = {i["key"]: i for i in client.get(f"/api/v1/cases/{case_id('EXC/BHM/203/2025')}/checklist", headers=hdr("inv_vizag")).json()["items"]}
    assert bare["fir"]["done"] and not bare["panchanama"]["done"] and not bare["deadline"]["done"]   # honest gaps show as not done
    assert "not a legal opinion" in client.get(url("/checklist"), headers=hdr("inv_vizag")).json()["notice"]


# ---------- CSV export ----------
def test_csv_export_is_scoped_filtered_and_formula_safe():
    r = client.get("/api/v1/cases/export.csv", headers=hdr("inv_vizag"))
    assert r.status_code == 200 and r.text.splitlines()[0].startswith("case_no,district")
    assert len(r.text.strip().splitlines()) == 6 and "Kuppam" not in r.text and "Cr.45" not in r.text   # header + 5 own cases
    f = client.get("/api/v1/cases/export.csv", params={"offence": "Ganja / NDPS"}, headers=hdr("inv_vizag")).text
    assert "SEB/ANK/019/2026" in f and "EXC/NRP/041/2025" not in f
    assert len(client.get("/api/v1/cases/export.csv", headers=hdr("admin")).text.strip().splitlines()) == 13
    assert client.get("/api/v1/cases/export.csv").status_code == 401
    from app.management import _safe
    assert _safe("=HYPERLINK(1)") == "'=HYPERLINK(1)" and _safe("+1") == "'+1" and _safe("Ramesh") == "Ramesh"


# ---------- lifecycle stage + heatmap ----------
def test_case_stage_follows_the_records_and_is_scoped():
    def stage(case_no, user="inv_vizag"):
        r = client.get(f"/api/v1/cases/{case_id(case_no)}/stage", headers=hdr(user))
        assert r.status_code == 200
        return {s["name"]: s for s in r.json()["steps"]}
    s = stage("EXC/BHM/203/2025")                       # decoy case: FIR only, no seizure panchanama
    assert s["Registered"]["state"] == "done" and s["Seizure recorded"]["state"] == "current" and s["Court"]["state"] == "todo"
    full = stage(CASE)                                    # earlier tests added accused, samples and hearings to this case
    assert full["Seizure recorded"]["state"] == "done" and full["Samples and lab"]["state"] == "done" and full["Custody"]["state"] == "done"
    assert [x["state"] for x in full.values()].count("current") == 1 and full["Chargesheet"]["state"] == "current"
    assert client.get(f"/api/v1/cases/{case_id(CASE)}/stage", headers=hdr("inv_guntur")).status_code == 404
    assert client.get(f"/api/v1/cases/{case_id(CASE)}/stage").status_code == 401


def test_hotspot_heatmap_is_station_by_month_and_scoped():
    h = client.get("/api/v1/analytics/hotspots", headers=hdr("inv_vizag")).json()["heatmap"]
    assert h["months"] == sorted(h["months"]) and all(len(r["counts"]) == len(h["months"]) for r in h["rows"])
    assert sum(r["total"] for r in h["rows"]) == 5 and not any("Kuppam" in r["station"] for r in h["rows"])
    assert any("Kuppam" in r["station"] for r in client.get("/api/v1/analytics/hotspots", headers=hdr("admin")).json()["heatmap"]["rows"])
