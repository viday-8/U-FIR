from conftest import case_id, client, hdr


def overview(user, **params):
    r = client.get("/api/v1/cases/overview", params=params, headers=hdr(user))
    assert r.status_code == 200, r.text
    return r.json()


def by_no(res):
    return {i["case_no"]: i for i in res["items"]}


def test_overview_has_rich_metadata_derived_from_facts():
    items = by_no(overview("inv_vizag"))
    m = items["EXC/NRP/041/2025"]["meta"]
    assert m["offence"] == ["Liquor transport"] and m["vehicles"] == ["AP 31 TX 4521"] and "NDPL" in " ".join(m["items"]).upper()
    assert m["accused"][0]["name"] == "Ramesh Babu Naidu" and m["accused"][0]["age"] == "34" and m["witnesses"]
    assert m["documents"] == {"diary": 1, "fir": 1, "seizure": 1} and m["date_first"] == "2025-03-14"
    assert "Ganja / NDPS" in items["SEB/ANK/019/2026"]["meta"]["offence"]
    assert "Sale / decoy operation" in items["EXC/BHM/203/2025"]["meta"]["offence"]
    assert "ID liquor manufacture" in by_no(overview("inv_guntur"))["Cr.88/2025-NRT"]["meta"]["offence"]
    assert by_no(overview("inv_chittoor"))["Cr.71/2026-PGR"]["meta"]["offence"][0] == "Arrack"


def test_keyword_query_matches_names_vehicles_places_sections_with_reasons():
    r = overview("inv_vizag", q="AP 31 TX 4521")
    assert {i["case_no"] for i in r["items"]} == {"EXC/NRP/041/2025", "EXC/NRP/114/2025"}
    assert any("Vehicle" in m for i in r["items"] for m in i["matched"])
    assert {i["case_no"] for i in overview("inv_vizag", q="Rameshbabu")["items"]} >= {"EXC/NRP/041/2025", "EXC/NRP/114/2025"}  # spelling variant
    assert {i["case_no"] for i in overview("inv_vizag", q="ganja NDPS")["items"]} == {"SEB/ANK/019/2026"}
    assert overview("inv_vizag", q="Kuppam")["items"] == []  # other district: no result, no hint
    assert overview("inv_vizag", q="Ramesh zzzzunknown")["items"] == []  # every word must match


def test_filters_and_facets_stay_inside_scope():
    r = overview("inv_vizag", offence="Liquor transport")
    assert {"EXC/NRP/041/2025", "EXC/NRP/087/2026"} <= {i["case_no"] for i in r["items"]} and "SEB/ANK/019/2026" not in {i["case_no"] for i in r["items"]}
    assert set(r["facets"]["district"]) == {"Visakhapatnam"} and sum(r["facets"]["station"].values()) == 5
    assert overview("inv_vizag", station="SEB Station, Anakapalle")["total"] == 1
    assert overview("inv_vizag", from_date="2026-01-01")["total"] == 2
    assert overview("inv_vizag", district="Guntur")["total"] == 0
    assert overview("admin")["total"] == 12 and set(overview("admin")["facets"]["district"]) == {"Visakhapatnam", "Guntur", "Chittoor"}


def test_search_returns_case_hits_text_hits_and_respects_filters():
    r = client.get("/api/v1/search", params={"q": "Naidu"}, headers=hdr("inv_vizag")).json()
    assert r["case_hits"] and all(c["case_no"].startswith(("EXC", "SEB")) for c in r["case_hits"])
    assert r["case_hits"][0]["matched"] and "offence" in r["case_hits"][0]
    f = client.get("/api/v1/search", params={"q": "Narsipatnam", "offence": "Ganja / NDPS"}, headers=hdr("inv_vizag")).json()
    assert {t["case_no"] for t in f["text_hits"]} <= {"SEB/ANK/019/2026"}
    assert client.get("/api/v1/search", params={"q": "Kuppam"}, headers=hdr("inv_vizag")).json()["case_hits"] == []


def test_suggestions_are_scoped_typed_and_tolerate_spelling():
    s = client.get("/api/v1/search/suggest", params={"q": "ram"}, headers=hdr("inv_vizag")).json()
    assert any(x["text"].startswith("Ramesh") for x in s) and {x["kind"] for x in s} <= {"Person named", "Witness", "Case number", "Place", "Item", "Vehicle", "Section", "Offence type", "Quantity"}
    assert not any("Munaswamy" in x["text"] for x in client.get("/api/v1/search/suggest", params={"q": "muna"}, headers=hdr("inv_vizag")).json())
    assert any("Munaswamy" in x["text"] for x in client.get("/api/v1/search/suggest", params={"q": "muna"}, headers=hdr("inv_chittoor")).json())
    assert any("Muniswamy" in x["text"] for x in client.get("/api/v1/search/suggest", params={"q": "munasw"}, headers=hdr("inv_chittoor")).json())
    assert client.get("/api/v1/search/suggest", params={"q": "r"}, headers=hdr("inv_vizag")).json() == []


def test_case_meta_and_network_are_scoped():
    cid = case_id("EXC/NRP/114/2025")
    net = client.get(f"/api/v1/cases/{cid}/network", headers=hdr("inv_vizag")).json()
    assert net["summary"]["related_cases"] >= 1 and any(p["links"] for p in net["people"])
    assert any(s["vehicle"] == "AP 31 TX 4521" for s in net["shared_vehicles"])
    assert all(r["case_no"].startswith(("EXC", "SEB")) for r in net["related_cases"])
    assert client.get(f"/api/v1/cases/{cid}/network", headers=hdr("inv_guntur")).status_code == 404
    assert client.get(f"/api/v1/cases/{cid}/meta", headers=hdr("inv_guntur")).status_code == 404
    gnt = case_id("Cr.45/2025-TNL")
    admin_net = client.get(f"/api/v1/cases/{gnt}/network", headers=hdr("admin")).json()
    assert any(r["case_no"].startswith("EXC/NRP") for r in admin_net["related_cases"])  # admin sees cross-district link
    assert client.get(f"/api/v1/cases/{gnt}/network", headers=hdr("inv_guntur")).json()["related_cases"] == []  # district user does not


def test_graph_has_clusters_stats_and_node_details():
    g = client.get("/api/v1/relationships", headers=hdr("inv_vizag")).json()
    assert g["stats"]["clusters"] >= 1 and g["stats"]["cases"] == 5
    cl = next(c for c in g["clusters"] if "Ramesh Babu Naidu" in c["names"])
    assert len(cl["case_ids"]) >= 2 and "AP 31 TX 4521" in cl["shared_vehicles"] and cl["status"] == "needs_review" and cl["min_score"] >= 50
    person = next(n for n in g["nodes"] if n["kind"] == "person" and n["label"] == "Ramesh Babu Naidu")
    assert person["father_or_spouse"] == "Appala Naidu" and person["cluster_id"] and person["degree"] >= 2
    case = next(n for n in g["nodes"] if n["kind"] == "case" and n["label"] == "EXC/NRP/041/2025")
    assert case["offence"] == ["Liquor transport"] and case["station"]
    assert not any(c["names"] == ["Lakshmi Devi"] for c in g["clusters"])  # lookalikes never clustered
    adm = client.get("/api/v1/relationships", headers=hdr("admin")).json()
    assert any("Ramesh Babu Naiduu" in c["names"] for c in adm["clusters"]) and not any("Ramesh Babu Naiduu" in c["names"] for c in g["clusters"])
