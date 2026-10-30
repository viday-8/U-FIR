"""Case metadata and keyword search. Everything is derived from extracted facts and document text, so it stays
traceable to the source. All functions work only on cases the caller passes in (already access-scoped)."""
import re
from collections import defaultdict
from datetime import date

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ..access import scoped_cases
from ..models import Case, CaseTag, Document, Fact, User
from .brief import _parse
from .normalise import norm_name, phonetic

LIQUOR = {"ndpl", "non-duty paid liquor", "id liquor", "illicit distilled liquor", "karnataka-made liquor", "indian made liquor", "iml", "spirit"}
OFFENCES = ["Ganja / NDPS", "Arrack", "ID liquor manufacture", "Sale / decoy operation", "Liquor transport", "Illicit liquor possession"]
# Words that point to a tag. Regex word boundaries keep short local terms ("sara", "still") from matching inside other words.
WORDS = {
    "Ganja / NDPS": r"\b(ganja|ganjai|cannabis|narcotic)\b",
    "Arrack": r"\b(arrack|naatu sara|country liquor)\b",
    "ID liquor manufacture": r"\b(manufactur\w*|distill\w*|brew\w*|navasagaram|fermenting|still)\b",
    "Sale / decoy operation": r"\b(decoy|belt shop|selling|sold|sale of)\b",
    "Liquor transport": r"\b(intercept\w*|transport\w*|carrying|carried|brought|stopped|checkpost|border)\b",
}


def tag_details(items: set[str], sections: str, text: str) -> list[dict]:
    """Automatic offence tags, each with the evidence that produced it. A browsing label, not a legal classification."""
    t, s = text.lower(), sections.lower()
    found = {}

    def add(tag, reason):
        found.setdefault(tag, [])
        if reason not in found[tag]:
            found[tag].append(reason)

    for i in sorted(items & {"ganja", "dry ganja"}):
        add("Ganja / NDPS", f"item: {i}")
    if "ndps" in s:
        add("Ganja / NDPS", "section: NDPS Act")
    if "arrack" in items:
        add("Arrack", "item: arrack")
    if "prohibition act" in s:
        add("Arrack", "section: AP Prohibition Act")
    for i in sorted(items & {"jaggery wash", "black jaggery"}):
        add("ID liquor manufacture", f"item: {i}")
    for tag, pattern in WORDS.items():
        for m in sorted({m.group(0) for m in re.finditer(pattern, t)})[:3]:
            if tag == "Liquor transport" and not items & LIQUOR:
                continue  # transport words only count when liquor is involved
            add(tag, f"word: “{m}”")
    if not found and items & LIQUOR:
        add("Illicit liquor possession", "liquor item recorded, no other activity found")
    order = {o: n for n, o in enumerate(OFFENCES)}
    return [{"tag": k, "reasons": v[:4], "source": "auto"} for k, v in sorted(found.items(), key=lambda kv: order[kv[0]])][:3]


def offence_tags(items: set[str], sections: str, text: str) -> list[str]:
    return [d["tag"] for d in tag_details(items, sections, text)]


def skeleton(s: str) -> str:
    """Consonant skeleton of the phonetic key: 'munasw' and 'Muniswamy' both start with 'mnsv'."""
    return re.sub(r"[aeiou]", "", phonetic(s))


def _uniq(values):
    seen, out = set(), []
    for v in values:
        if v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def profiles(db: Session, cases: dict[int, Case]) -> dict[int, dict]:
    """One profile per case, built with bulk queries."""
    ids = list(cases) or [0]
    facts = defaultdict(list)
    for f in db.query(Fact).filter(Fact.case_id.in_(ids)).order_by(Fact.id):
        facts[f.case_id].append(f)
    docs = defaultdict(list)
    for d in db.query(Document).filter(Document.case_id.in_(ids)):
        docs[d.case_id].append(d)
    overrides = {t.case_id: t for t in db.query(CaseTag).filter(CaseTag.case_id.in_(ids))}
    out = {}
    for cid, case in cases.items():
        fs, ds = facts[cid], docs[cid]
        by = defaultdict(list)
        for f in fs:
            by[f.type].append(f)
        text = " ".join(p.text for d in ds for p in d.pages)
        items = {f.normalised for f in by["item"]}
        sections = " ".join(f.original for f in by["legal_section"])
        people = {}
        for f in by["person"]:
            a = f.attributes or {}
            cur = people.setdefault(f.normalised, {"name": f.original, "witness": a.get("role") == "witness"})
            for k in ("alias", "age", "resident", "father_or_spouse"):
                if a.get(k) and k not in cur:
                    cur[k] = a[k]
            if a.get("role") != "witness":
                cur["witness"] = False
        accused = [p for p in people.values() if not p["witness"]]
        witnesses = [p["name"] for p in people.values() if p["witness"]]
        dates = sorted(d for d in (_parse(f.original) for f in by["date"]) if d)
        details = tag_details(items, sections, text)
        ov = overrides.get(cid)
        if ov:  # an officer's decision always wins over the automatic tags
            details = [{"tag": t, "reasons": [f"set by {ov.by}: {ov.reason}"], "source": "officer"} for t in ov.tags]
        prof = {
            "offence": [d["tag"] for d in details],
            "offence_detail": details,
            "offence_source": "officer" if ov else "auto",
            "accused": accused,
            "witnesses": witnesses,
            "vehicles": _uniq(f.original for f in by["vehicle"]),
            "items": _uniq(f.original for f in by["item"]),
            "quantities": _uniq(f.original for f in by["quantity"]),
            "places": _uniq(f.original for f in by["place"]),
            "sections": _uniq(f.original for f in by["legal_section"]),
            "documents": dict(sorted({d.doc_type: sum(1 for x in ds if x.doc_type == d.doc_type) for d in ds}.items())),
            "date_first": dates[0] if dates else None,
            "date_last": dates[-1] if dates else None,
            "flags": {"needs_review": any(d.status in ("needs_review", "failed") for d in ds),
                      "ocr": any(p.ocr for d in ds for p in d.pages), "telugu": any(d.language != "en" for d in ds)},
        }
        prof["keywords"] = _uniq([*prof["offence"], *prof["items"], *prof["vehicles"], *prof["places"][:4], *prof["sections"]])[:14]
        out[cid] = prof
    return out


FIELD_LABEL = {"case_no": "Case number", "station": "Station", "accused": "Person named", "vehicle": "Vehicle", "item": "Item",
               "place": "Place", "section": "Section", "offence": "Offence type", "witness": "Witness", "quantity": "Quantity"}


def _fields(case: Case, p: dict) -> list[tuple[str, str]]:
    f = [("case_no", case.case_no), ("station", case.station), ("station", case.district)]
    f += [("accused", a["name"]) for a in p["accused"]] + [("accused", a["alias"]) for a in p["accused"] if a.get("alias")]
    f += [("witness", w) for w in p["witnesses"]]
    f += [("vehicle", v) for v in p["vehicles"]] + [("item", i) for i in p["items"]] + [("place", x) for x in p["places"]]
    f += [("section", s) for s in p["sections"]] + [("offence", o) for o in p["offence"]] + [("quantity", q) for q in p["quantities"]]
    return f


def _token_hits(token: str, fields: list[tuple[str, str]]) -> list[tuple[str, str]]:
    t = token.lower()
    tflat = re.sub(r"[^a-z0-9]", "", t)
    hits = []
    for kind, value in fields:
        v = value.lower()
        vflat = re.sub(r"[^a-z0-9]", "", v)
        if t in v or (tflat and tflat in vflat):
            hits.append((kind, value))
        elif kind in ("accused", "witness") and len(t) >= 4:
            words = norm_name(value).split()
            if any(fuzz.ratio(t, w) >= 85 or phonetic(t) == phonetic(w) for w in words):
                hits.append((kind, value))
    return hits


def match(case: Case, p: dict, q: str) -> list[str] | None:
    """None when any word of the query matches nothing in the case; otherwise the fields that matched."""
    tokens = re.findall(r"[A-Za-z0-9/.\-]+", q)
    if not tokens:
        return []
    fields, matched = _fields(case, p), []
    for tok in tokens:
        hits = _token_hits(tok, fields)
        if not hits:
            return None  # every word must match something in this case
        matched += [f"{FIELD_LABEL[k]}: {v}" for k, v in hits[:2]]
    return _uniq(matched)[:6]


def filtered(db: Session, user: User, q: str = "", offence: str = "", station: str = "", status: str = "", district: str = "",
             from_date: str = "", to_date: str = "", flag: str = "") -> tuple[list[dict], dict]:
    """Returns (rows, facets). Facets count the whole accessible set so filters never reveal anything outside scope."""
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    profs = profiles(db, cases)
    facets = {"offence": defaultdict(int), "station": defaultdict(int), "district": defaultdict(int), "status": defaultdict(int)}
    for cid, c in cases.items():
        for o in profs[cid]["offence"]:
            facets["offence"][o] += 1
        facets["station"][c.station] += 1
        facets["district"][c.district] += 1
        facets["status"][c.status] += 1
    rows = []
    for cid, c in cases.items():
        p = profs[cid]
        if offence and offence not in p["offence"] or station and c.station != station or status and c.status != status:
            continue
        if district and c.district != district or from_date and c.registered_on < from_date or to_date and c.registered_on > to_date:
            continue
        if flag == "needs_review" and not p["flags"]["needs_review"] or flag == "ocr" and not p["flags"]["ocr"]:
            continue
        matched = match(c, p, q) if q.strip() else []
        if matched is None:
            continue
        rows.append({"id": c.id, "case_no": c.case_no, "district": c.district, "station": c.station, "status": c.status,
                     "registered_on": c.registered_on, "documents": len(c.documents), "meta": p, "matched": matched})
    rows.sort(key=lambda r: (-len(r["matched"]), r["registered_on"]), reverse=False)
    rows.sort(key=lambda r: r["registered_on"], reverse=True)
    if q.strip():
        rows.sort(key=lambda r: -len(r["matched"]))
    return rows, {k: dict(sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))) for k, v in facets.items()}


def suggest(db: Session, user: User, q: str, limit: int = 8) -> list[dict]:
    q = q.strip().lower()
    if len(q) < 2:
        return []
    cases = {c.id: c for c in db.scalars(scoped_cases(user))}
    profs = profiles(db, cases)
    best: dict[tuple[str, str], int] = {}
    qf, qp = re.sub(r"[^a-z0-9]", "", q), phonetic(q)
    for cid, c in cases.items():
        for kind, value in _fields(c, profs[cid]):
            if kind in ("station",):
                continue
            v = value.lower()
            vflat = re.sub(r"[^a-z0-9]", "", v)
            score = 100 if v.startswith(q) else 90 if qf and qf in vflat else 0
            if not score and kind in ("accused", "witness") and len(q) >= 3:
                words = norm_name(value).split()
                sk = skeleton(q)
                if any(fuzz.ratio(q, w) >= 85 or phonetic(w) == qp or (len(sk) >= 3 and skeleton(w).startswith(sk)) for w in words):
                    score = 80
            if score:
                key = (kind, value)
                best[key] = max(best.get(key, 0), score)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1], kv[0][1]))[:limit]
    return [{"kind": FIELD_LABEL[k], "text": v} for (k, v), _ in ranked]
