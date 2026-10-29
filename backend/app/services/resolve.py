"""Identity resolution. Conservative by design: a name match alone never reaches the threshold,
nothing is auto-confirmed, and every candidate lists signals for AND against."""
from collections import defaultdict
from itertools import combinations

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ..models import Candidate, Entity, Fact
from .normalise import phonetic

NAME_MIN = 80       # below this similarity the pair is not even considered
SHOW_MIN = 50       # below this score the pair is not surfaced
LIKELY = 75


def _flat(s: str) -> str:
    return s.replace(" ", "")


def _age(e) -> int | None:
    a = (e.attributes or {}).get("age")
    return int(a) if a and a.isdigit() else None


def refresh_entities(db: Session) -> list[Entity]:
    groups = defaultdict(list)
    for f in db.query(Fact).filter_by(type="person").order_by(Fact.id):
        if (f.attributes or {}).get("role") == "witness":
            continue  # witnesses are not matched, to keep false links down
        groups[(f.case_id, f.normalised)].append(f)
    existing = {(e.case_id, e.key): e for e in db.query(Entity)}
    for (case_id, key), facts in groups.items():
        best = max(facts, key=lambda f: len(f.attributes or {}))
        e = existing.get((case_id, key)) or Entity(case_id=case_id, key=key)
        e.label, e.attributes, e.fact_ids = best.original, best.attributes, [f.id for f in facts]
        db.add(e)
    db.flush()
    return db.query(Entity).all()


def score_pair(a: Entity, b: Entity, vehicles: dict[int, dict[str, list[int]]]):
    sim = max(fuzz.ratio(_flat(a.key), _flat(b.key)), fuzz.ratio(phonetic(a.key), phonetic(b.key)))
    if sim < NAME_MIN:
        return None
    score, signals, missing, evidence = 0.4 * sim, [], [], list(a.fact_ids) + list(b.fact_ids)
    signals.append({"kind": "name", "supports": True, "text": f"Names are similar ({round(sim)}%): “{a.label}” / “{b.label}”"})
    aa, ba = a.attributes or {}, b.attributes or {}

    fa, fb = aa.get("father_or_spouse"), ba.get("father_or_spouse")
    if fa and fb:
        fsim = fuzz.ratio(_flat(fa.lower()), _flat(fb.lower()))
        if fsim >= 85:
            score += 30
            signals.append({"kind": "father", "supports": True, "text": f"Father/spouse name matches: “{fa}” / “{fb}”"})
        elif fsim < 60:
            score -= 30
            signals.append({"kind": "father", "supports": False, "text": f"Father/spouse name differs: “{fa}” vs “{fb}”"})
    else:
        missing.append("Father/spouse name not recorded in both records")

    ra, rb = aa.get("resident"), ba.get("resident")
    if ra and rb:
        if ra.lower() == rb.lower():
            score += 10
            signals.append({"kind": "residence", "supports": True, "text": f"Same residence: {ra}"})
        else:
            signals.append({"kind": "residence", "supports": False, "text": f"Different residence: {ra} vs {rb}"})
            score -= 5
    else:
        missing.append("Residence not recorded in both records")

    ya, yb = _age(a), _age(b)
    if ya is not None and yb is not None:
        if abs(ya - yb) <= 2:
            score += 5
            signals.append({"kind": "age", "supports": True, "text": f"Ages are close ({ya} / {yb})"})
        elif abs(ya - yb) > 3:
            score -= 10
            signals.append({"kind": "age", "supports": False, "text": f"Ages differ ({ya} vs {yb})"})
    else:
        missing.append("Age not recorded in both records")

    shared = set(vehicles.get(a.case_id, {})) & set(vehicles.get(b.case_id, {}))
    for v in sorted(shared):
        score += 20
        evidence += vehicles[a.case_id][v] + vehicles[b.case_id][v]
        signals.append({"kind": "vehicle", "supports": True, "text": "Same vehicle recorded in both cases"})
    # A vehicle is case-level, so it cannot identify a person. Require a person-level match as well.
    if not any(s["supports"] and s["kind"] in ("father", "residence") for s in signals):
        return None
    return max(0, min(100, round(score))), signals, missing, sorted(set(evidence))


def refresh(db: Session) -> None:
    """Recompute entities and candidate pairs. Reviewed decisions are preserved."""
    entities = refresh_entities(db)
    vehicles = defaultdict(lambda: defaultdict(list))
    for f in db.query(Fact).filter_by(type="vehicle"):
        vehicles[f.case_id][f.normalised].append(f.id)
    old = {(c.entity_a, c.entity_b): c for c in db.query(Candidate)}
    for a, b in combinations(sorted(entities, key=lambda e: e.id), 2):
        if a.case_id == b.case_id:
            continue
        r = score_pair(a, b, vehicles)
        cand = old.get((a.id, b.id))
        if r is None or (r[0] < SHOW_MIN and not cand):
            continue
        score, signals, missing, evidence = r
        if cand is None:
            cand = Candidate(entity_a=a.id, entity_b=b.id)
        cand.score, cand.signals, cand.missing, cand.evidence = score, signals, missing, evidence
        db.add(cand)
    db.commit()


def strength(score: int) -> str:
    return "likely" if score >= LIKELY else "possible"
