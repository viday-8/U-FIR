"""Synthetic archive generator and timing script for the scale claims. `python -m app.bench 2000` (uses a scratch SQLite file)."""
import os
import random
import sys
import time

FIRST = ["Ramesh", "Suresh", "Venkata", "Satyam", "Gangadhar", "Muni", "Appala", "Srinu", "Koteswara", "Naresh", "Ravi", "Anil", "Mohan", "Prasad", "Krishna", "Lakshmi", "Padma", "Raju", "Chinna", "Sathya", "Narayana", "Subba", "Ganesh", "Hari"]
LAST = ["Naidu", "Rao", "Reddy", "Raju", "Babu", "Kumar", "Murthy", "Subbaiah", "Swamy", "Prasad", "Sharma", "Varma"]
VILLAGES = ["Gavarapalem", "Paderu", "Kuppam", "Tenali", "Rentachintala", "Santhipuram", "Narsipatnam", "Bheemili", "Punganur", "Mangalagiri", "Anakapalle", "Palamaner"]
VARIANTS = [("Ramesh", "Rameshbabu"), ("Sathya", "Satya"), ("Reddy", "Reddi"), ("Naidu", "Naiduu"), ("Muni", "Muniswamy"), ("Venkata", "Venkat")]


def generate(db, n_cases: int, seed: int = 1, start: int = 0):
    """Adds n_cases cases (one FIR page each, 1-3 persons, a vehicle). About 15% of people are re-used with a spelling variant."""
    from .models import Case, Document, Fact, Page
    from .services.normalise import norm_value
    rnd = random.Random(seed)
    pool = []
    for i in range(start, start + n_cases):
        case = Case(case_no=f"BENCH/{i:05d}/2026", district=rnd.choice(["Visakhapatnam", "Guntur", "Chittoor"]), station=f"Station {i % 40}",
                    registered_on=f"2026-{1 + i % 12:02d}-{1 + i % 27:02d}")
        db.add(case)
        db.flush()
        doc = Document(case_id=case.id, doc_type="fir", path="-", checksum=f"bench{i}", status="indexed")
        db.add(doc)
        db.flush()
        db.add(Page(document_id=doc.id, number=1, text=f"FIR {case.case_no}"))
        for _ in range(rnd.choice([1, 1, 2, 3])):
            if pool and rnd.random() < 0.15:
                first, last, father, village, age = rnd.choice(pool)
                for a, b in VARIANTS:
                    if rnd.random() < 0.5:
                        first, last = first.replace(a, b), last.replace(a, b)
            else:
                first, last, father, village, age = rnd.choice(FIRST), rnd.choice(LAST), f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", rnd.choice(VILLAGES), str(rnd.randint(20, 60))
                pool.append((first, last, father, village, age))
            name = f"{first} {last}"
            db.add(Fact(case_id=case.id, document_id=doc.id, page=1, type="person", original=name, normalised=norm_value("person", name),
                        span=name, model="bench", attributes={"relation": "S/o", "father_or_spouse": father, "age": age, "resident": village}))
        v = f"AP 31 TX {rnd.randint(1000, 9999)}"
        db.add(Fact(case_id=case.id, document_id=doc.id, page=1, type="vehicle", original=v, normalised=norm_value("vehicle", v), span=v, model="bench"))
    db.commit()


def main(n: int):
    os.environ["DATABASE_URL"] = "sqlite:///./bench.db"
    if os.path.exists("bench.db"):
        os.remove("bench.db")
    from .db import Base, SessionLocal, engine
    from .models import Candidate, User
    from .services import graph, profile, resolve
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        t = time.perf_counter(); generate(db, n); print(f"generated {n} cases: {time.perf_counter() - t:.1f}s")
        t = time.perf_counter(); resolve.refresh(db); full = time.perf_counter() - t
        ents = resolve.refresh_entities(db)
        pairs = sum(1 for _ in resolve.candidate_pairs(ents, None))
        print(f"{len(ents)} people · full refresh {full:.1f}s · pairs scored {pairs:,} of {len(ents) * (len(ents) - 1) // 2:,} possible ({100 * pairs / max(1, len(ents) * (len(ents) - 1) // 2):.2f}%) · {db.query(Candidate).count()} candidate links")
        generate(db, 1, seed=99, start=n)
        t = time.perf_counter(); resolve.refresh(db, {db.query(__import__('app.models', fromlist=['Case']).Case).count()}); print(f"adding one case (incremental refresh): {time.perf_counter() - t:.2f}s")
        admin = User(username="b", password_hash="-", role="admin", district=None)
        for label, kw in (("whole archive", {}), ("linked networks only", {"linked_only": True}), ("focused neighbourhood", {"focus": "case:1", "depth": 2})):
            t = time.perf_counter(); g = graph.build_graph(db, admin, **kw)
            print(f"graph ({label}): {time.perf_counter() - t:.2f}s · shows {g['scope']['shown_nodes']:,} of {g['scope']['total_nodes']:,} nodes · {len(g['edges']):,} edges")
        cases = {c.id: c for c in db.query(__import__('app.models', fromlist=['Case']).Case)}
        t = time.perf_counter(); profile.profiles(db, cases); print(f"case metadata for all {len(cases)} cases: {time.perf_counter() - t:.2f}s")
    os.remove("bench.db")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
