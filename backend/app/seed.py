"""Synthetic demo data only. Run: python -m app.seed"""
import hashlib
from pathlib import Path

from .config import STORAGE_DIR
from .db import Base, SessionLocal, engine
from .models import Case, Document, Page, User
from .seed_data import CASES, USERS
from .services import search
from .security import hash_password

DEMO_PASSWORD = "demo123"  # synthetic demo accounts only


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    storage = Path(STORAGE_DIR)
    storage.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        search.reset_index(db)
        for name, role, district in USERS:
            db.add(User(username=name, password_hash=hash_password(DEMO_PASSWORD), role=role, district=district))
        for case_no, district, station, reg, docs in CASES:
            case = Case(case_no=case_no, district=district, station=station, registered_on=reg)
            db.add(case)
            db.flush()
            for i, (doc_type, text) in enumerate(docs, 1):
                path = storage / f"{case_no.replace('/', '_')}_{i}_{doc_type}.txt"
                path.write_text(text)
                doc = Document(case_id=case.id, doc_type=doc_type, path=str(path),
                               checksum=hashlib.sha256(text.encode()).hexdigest())
                db.add(doc)
                db.flush()
                page = Page(document_id=doc.id, number=1, text=text)
                db.add(page)
                db.flush()
                search.index_page(db, page)
        db.commit()
    from . import cache
    cache.bump()
    print(f"Seeded {len(USERS)} users, {len(CASES)} cases. Demo password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
