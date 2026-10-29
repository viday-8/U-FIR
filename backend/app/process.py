"""Run LLM extraction for every document still in 'received' state. python -m app.process"""
from .db import SessionLocal
from .models import Document
from .services.ingest import process_document

with SessionLocal() as db:
    ids = [d.id for d in db.query(Document).filter(Document.status == "received")]
for i in ids:
    process_document(i)
    print("processed document", i)

from .services import resolve  # noqa: E402

with SessionLocal() as db:
    resolve.refresh(db)
    print("identity candidates refreshed")
