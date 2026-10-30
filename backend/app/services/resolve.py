"""Identity resolution. Conservative by design: a name match alone never reaches the threshold,
nothing is auto-confirmed, and every candidate lists signals for AND against."""
from collections import defaultdict

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ..models import Candidate, Entity, Fact
from .. import cache
from .normalise import norm_name, phonetic

NAME_MIN = 80       # below this similarity the pair is not even considered
SHOW_MIN = 50       # below this score the pair is not surfaced
LIKELY = 75


def _flat(s: str) -> str:
    return s.replace(" ", "")


def _age(e) -> int | None:
    a = (e.attributes or {}).get("age")
    return int(a) if a and a.isdigit() else None


def refresh_entities(db: Session, case_ids: set[int] | None = None) -> list[Entity]:
    """One Entity per (case, normalised name). With case_ids, only those cases are rebuilt; entities whose person
    facts have all been removed are deleted together with their candidate links."""
    q = db.query(Fact).filter_by(type="person").order_by(Fact.id)
    if case_ids is not None:
        q = q.filter(Fact.case_id.in_(list(case_ids) or [0]))
    groups = defaultdict(list)
    for f in q:
        if (f.attributes or {}).get("role") == "witness":
            continue  # witnesses are not matched, to keep false links down
        groups[(f.case_id, f.normalised)].append(f)
    eq = db.query(Entity)
    if case_ids is not None:
        eq = eq.filter(Entity.case_id.in_(list(case_ids) or [0]))
    existing = {(e.case_id, e.key): e for e in eq}
    for (case_id, key), facts in groups.items():
        best = max(facts, key=lambda f: len(f.attributes or {}))
        e = existing.get((case_id, key)) or Entity(case_id=case_id, key=key)
        e.label, e.attributes, e.fact_ids = best.original, best.attributes, [f.id for f in facts]
        db.add(e)
    for k, e in existing.items():
        if k not in groups:  # the person is no longer recorded in this case
            db.query(Candidate).filter((Candidate.entity_a == e.id) | (Candidate.entity_b == e.id)).delete(synchronize_session=False)
            db.delete(e)
    db.flush()
    return db.query(Entity).all()


BUCKET_CAP = 600   # safety valve only: blocks are normally tiny because they combine a name key with a person-level key


def _name_keys(key: str) -> set[str]:
    keys = set()
    words = [w for w in key.split() if len(w) >= 3]
    for w in words:
        p = phonetic(w)
        keys.add("p:" + p[:3])
        keys.add("s:" + "".join(c for c in p if c not in "aeiou")[:3])
    if len(words) > 1:  # "Ramesh Babu Naidu" and "Rameshbabu Naidu" both have this
        joined = phonetic("".join(words))
        keys.add("p:" + joined[:3])
        keys.add("s:" + "".join(c for c in joined if c not in "aeiou")[:3])
    return keys


def _person_keys(e: Entity) -> set[str]:
    """A link needs a father/spouse or residence match (see score_pair), so a pair that shares neither can be skipped."""
    a, keys = e.attributes or {}, set()
    if a.get("resident"):
        keys.add("r:" + a["resident"].lower())
    father = (a.get("father_or_spouse") or "").lower()
    for w in father.split():
        if len(w) >= 3:
            keys.add("f:" + phonetic(w)[:3])
    if len(father.split()) > 1:
        keys.add("f:" + phonetic(father.replace(" ", ""))[:3])
    return keys


def _block_keys(e: Entity) -> set[str]:
    """Blocking keys = name sound x person-level key. 'Naidu' alone is far too common to block on; 'Naidu' + 'son of
    Appala…' or 'Naidu' + 'resident of Gavarapalem' is a handful of people. Replaces comparing every pair (O(n^2))."""
    pk = _person_keys(e)
    return {n + "|" + p for n in _name_keys(e.key) for p in pk}


def candidate_pairs(entities: list[Entity], changed_cases: set[int] | None):
    """Yield (a, b) pairs worth scoring."""
    by_key = defaultdict(list)
    for e in entities:
        for k in _block_keys(e):
            by_key[k].append(e)
    shared = set()
    for bucket in by_key.values():
        if len(bucket) > BUCKET_CAP:
            continue
        for i, a in enumerate(bucket):
            for b in bucket[i + 1:]:
                if a.case_id != b.case_id and (changed_cases is None or a.case_id in changed_cases or b.case_id in changed_cases):
                    shared.add((a.id, b.id) if a.id < b.id else (b.id, a.id))
    by_id = {e.id: e for e in entities}
    for (x, y) in shared:
        yield by_id[x], by_id[y]


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


def refresh(db: Session, case_ids: set[int] | None = None) -> None:
    """Recompute entities and candidate pairs. With case_ids only pairs touching those cases are rescored, so adding
    one document does not re-compare the whole archive. Reviewed decisions are always preserved."""
    entities = refresh_entities(db, case_ids)
    vehicles = defaultdict(lambda: defaultdict(list))
    for f in db.query(Fact).filter_by(type="vehicle"):
        vehicles[f.case_id][f.normalised].append(f.id)
    old = {(c.entity_a, c.entity_b): c for c in db.query(Candidate)}
    seen = set()
    for a, b in candidate_pairs(entities, case_ids):
        a, b = (a, b) if a.id < b.id else (b, a)
        seen.add((a.id, b.id))
        r = score_pair(a, b, vehicles)
        cand = old.get((a.id, b.id))
        if r is None or (r[0] < SHOW_MIN and not cand):
            if cand and cand.status == "unreviewed":
                db.delete(cand)
            continue
        score, signals, missing, evidence = r
        if cand is None:
            cand = Candidate(entity_a=a.id, entity_b=b.id)
        cand.score, cand.signals, cand.missing, cand.evidence = score, signals, missing, evidence
        db.add(cand)
    case_of = {e.id: e.case_id for e in entities}
    for (x, y), cand in old.items():  # links that are no longer plausible and were never reviewed go away
        if cand.status == "unreviewed" and (x, y) not in seen and x in case_of and y in case_of \
                and (case_ids is None or case_of[x] in case_ids or case_of[y] in case_ids):
            db.delete(cand)
    db.commit()
    cache.bump()


def strength(score: int) -> str:
    return "likely" if score >= LIKELY else "possible"
