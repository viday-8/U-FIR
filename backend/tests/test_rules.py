from conftest import doc_text

from app.seed_data import CASES
from app.services.rules import extract_rules


def vals(facts, t):
    return [f["value"] for f in facts if f["type"] == t]


def test_every_seed_document_span_is_verbatim_and_never_crosses_lines():
    for *_, docs in CASES:
        for _, text in docs:
            for f in extract_rules(text):
                assert f["span"] in text and f["value"] in text
                if f["type"] in ("person", "place"):
                    assert "\n" not in f["value"]


def test_fir_relation_vehicle_quantity_place():
    facts = extract_rules(doc_text("EXC/NRP/041/2025", "fir"))
    p = next(f for f in facts if f["type"] == "person")
    assert p["value"] == "Ramesh Babu Naidu"
    assert p["attributes"] == {"relation": "S/o", "father_or_spouse": "Appala Naidu", "age": "34", "resident": "Gavarapalem"}
    assert vals(facts, "vehicle") == ["AP 31 TX 4521"] and "120 bottles" in vals(facts, "quantity")
    assert "Anakapalle" in vals(facts, "place") and "NDPL" not in vals(facts, "place")
    assert "AP Excise Act Sec 34(a)" in vals(facts, "legal_section")


def test_alias_and_other_date_and_section_styles():
    f = extract_rules(doc_text("EXC/NRP/087/2026", "fir"))
    assert next(x for x in f if x["type"] == "person")["attributes"]["alias"] == "Ramesh"
    assert "09.06.2026" in vals(f, "date") and "Karnataka-made liquor" in vals(f, "item")
    ndps = extract_rules(doc_text("SEB/ANK/019/2026", "fir"))
    assert "Sec 20(b)(ii)(B) of NDPS Act" in vals(ndps, "legal_section")
    assert {"Satyam Rao", "Ravi Teja"} <= set(vals(ndps, "person")) and "AP 37 TA 9021" in vals(ndps, "vehicle")
    assert "Sec 7A of AP Prohibition Act" in vals(extract_rules(doc_text("Cr.71/2026-PGR", "fir")), "legal_section")
    assert "02/08/2025" in vals(extract_rules(doc_text("EXC/NRP/114/2025", "fir")), "date")


def test_witnesses_present_and_no_act_or_station_places():
    wit = extract_rules(doc_text("EXC/NRP/041/2025", "seizure"))
    assert {"K. Srinu", "P. Lakshmi"} <= set(vals(wit, "person"))
    assert "Satyam Rao" in vals(extract_rules(doc_text("EXC/NRP/114/2025", "fir")), "person")
    for case_no, *_ in CASES:
        for p in vals(extract_rules(doc_text(case_no, "fir")), "place"):
            assert not any(w in p for w in ("Act", "Station", "Excise"))


def test_injection_text_is_just_data_and_empty_text_gives_nothing():
    inj = extract_rules(doc_text("Cr.62/2025-MGR", "diary"))
    assert all(f["type"] in {"person", "date", "place", "legal_section", "vehicle", "quantity", "item"} for f in inj)
    assert extract_rules("No details recorded.") == []
