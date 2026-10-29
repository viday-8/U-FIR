import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["STORAGE_DIR"] = "./test_storage"
os.environ["EXTRACTOR"] = "rules"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Case, Document  # noqa: E402
from app.services import resolve  # noqa: E402
from app.services.ingest import process_document  # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def fresh_db():
    """Every test module starts from freshly seeded, fully processed synthetic data."""
    seed.main()
    with SessionLocal() as db:
        ids = [d.id for d in db.query(Document)]
    for i in ids:
        process_document(i)
    yield


def hdr(username):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": seed.DEMO_PASSWORD})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def case_id(case_no):
    with SessionLocal() as db:
        return db.query(Case).filter_by(case_no=case_no).one().id


def doc_text(case_no, doc_type):
    from app.seed_data import CASES
    return next(t for n, _, _, _, docs in CASES if n == case_no for d, t in docs if d == doc_type)
