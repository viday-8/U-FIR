"""Rule-based extractor: open-source, offline, deterministic. Every span is a verbatim match.
Covers the common Excise record formats; free-form prose and Telugu need the optional LLM extractor."""
import re

TOKEN = r"(?:[A-Z]\.|[A-Z][A-Za-z]+)"  # a dot only after a single-letter initial
NAME = rf"{TOKEN}(?:[ \t]{TOKEN}){{0,3}}"  # same line only
STOP = {"NDPL", "ID", "FIR", "AP", "TS", "PS", "AI", "NOTE", "EXCISE", "PROHIBITION", "ACT", "STATION", "DEPARTMENT", "NDPS", "IML", "SEB"}
LEAD_WORDS = {"accused", "witness", "present", "named", "one", "also", "driver", "owner"}

PERSON_REL = re.compile(rf"({NAME})(?:,?\s+(?:alias|@)\s+({NAME}))?,?\s+(S/o|W/o|D/o)\s+({NAME})")
PERSON_ROLE = re.compile(rf"\b(?:Accused|Present(?: at [a-z ]+)?:|Also named:|one|named)\s+({NAME})")
WITNESSES = re.compile(rf"Witnesses?:\s*({NAME}(?:\s+and\s+{NAME})*)")
VEHICLE = re.compile(r"\b(?:AP|TS|KA|TN|OD|MH)\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{4}\b")
DATE = re.compile(r"\b\d{2}[-./]\d{2}[-./]\d{4}\b")
QUANTITY = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s+(?:quarter bottles|bottles|litres|liters|ltrs|drums|kgs|kg|packets|tetra packs|cartons|cases|bags|cans)\b", re.I)
ITEM = re.compile(r"\b(?:non-duty paid liquor|NDPL|ID liquor|illicit distilled liquor|Karnataka-made liquor|Indian Made Liquor|IML|jaggery wash|black jaggery|dry ganja|ganja|arrack|toddy|spirit)\b", re.I)
SECTION = re.compile(r"(?:(?:AP|A\.P\.)\s+(?:Excise|Prohibition)\s+Act\s+)?(?:U/s|u/s|Sec(?:tion)?\.?)\s*\d+[A-Z]?(?:\([a-zA-Z0-9]+\))*(?:\s+(?:of|r/w)\s+(?:the\s+)?(?:AP\s+|A\.P\.\s+)?[A-Z][A-Za-z.&]*(?:\s[A-Z][A-Za-z.&]*)*?\s+Act)?")
PLACE = re.compile(rf"\b(?:near|at|in|of|R/o|from)\s+({NAME})")
AGE = re.compile(r"(?:aged\s+(?:about\s+)?|Age:\s*)(\d{1,2})")
RESIDENT = re.compile(rf"(?:,?\s*(?:aged\s+(?:about\s+)?|Age:\s*)\d{{1,2}}(?:\s*(?:yrs|years))?)?,?\s*(?:resident of|R/o|of)\s+({NAME})")


def _fact(type_, value, span, **attrs):
    return {"type": type_, "value": value, "span": span, "attributes": {k: v for k, v in attrs.items() if v}}


def extract_rules(text: str) -> list[dict]:
    facts, seen_person = [], set()

    def add_person(name, span, **attrs):
        words = name.split()
        while len(words) > 1 and words[0].lower() in LEAD_WORDS:  # "Accused Ramesh" -> "Ramesh"
            words.pop(0)
        name = " ".join(words)
        key = name.lower()
        if name.upper() in STOP or key in seen_person:
            return
        seen_person.add(key)
        facts.append(_fact("person", name, span, **attrs))

    for m in PERSON_REL.finditer(text):
        tail = text[m.end(): m.end() + 90]
        age = AGE.search(tail)
        resident = RESIDENT.match(tail)
        add_person(m.group(1), m.group(0), alias=m.group(2), relation=m.group(3), father_or_spouse=m.group(4),
                   age=age.group(1) if age else None, resident=resident.group(1) if resident and resident.group(1).upper() not in STOP else None)
    for m in PERSON_ROLE.finditer(text):
        add_person(m.group(1), m.group(0))
    for m in WITNESSES.finditer(text):
        for name in re.split(r"\s+and\s+", m.group(1)):
            add_person(name, m.group(0), role="witness")

    for m in VEHICLE.finditer(text):
        facts.append(_fact("vehicle", m.group(0), m.group(0)))
    for m in DATE.finditer(text):
        facts.append(_fact("date", m.group(0), m.group(0)))
    for m in QUANTITY.finditer(text):
        facts.append(_fact("quantity", m.group(0), m.group(0)))
    for m in ITEM.finditer(text):
        facts.append(_fact("item", m.group(0), m.group(0)))
    for m in SECTION.finditer(text):
        facts.append(_fact("legal_section", m.group(0), m.group(0)))
    seen_place = set()
    for m in PLACE.finditer(text):
        v = m.group(1)
        if any(w.upper() in STOP for w in v.split()) or v.lower() in seen_place or v.lower() in seen_person:
            continue
        seen_place.add(v.lower())
        facts.append(_fact("place", v, m.group(0)))
    return facts
