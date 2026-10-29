import hashlib
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy.orm import Session

from .. import audit, config
from ..db import SessionLocal
from ..models import Document, Fact, Page
from . import extract, ocr, resolve, search

ALLOWED = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def _docx_text(data: bytes) -> str:
    from docx import Document as Word
    try:
        doc = Word(BytesIO(data))
    except Exception:
        raise HTTPException(422, "This Word file could not be read (is it a valid .docx?)")
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:  # many FIRs keep particulars in a table; read cells row by row
        for row in table.rows:
            lines.append("  ".join(c.text.strip() for c in row.cells if c.text.strip()))
    return "\n".join(l for l in lines if l.strip())


def _pages_from(filename: str, data: bytes) -> list[tuple[str, bool]]:
    """[(text, was_ocr)] per page. Selectable text is used directly; OCR only for pages without any."""
    name = filename.lower()
    if name.endswith((".png", ".jpg", ".jpeg")):
        pages = [(ocr.ocr_image_bytes(data), True)]
    elif name.endswith(".docx"):
        pages = [(_docx_text(data), False)]
    elif name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        pages = []
        for i, p in enumerate(reader.pages):
            text = (p.extract_text() or "").strip()
            pages.append((text, False) if len(text) >= 20 else (ocr.ocr_pdf_page(data, i), True))
    else:
        return [(data.decode("utf-8", errors="replace"), False)]
    if not any(t.strip() for t, _ in pages):
        raise HTTPException(422, "No readable text found in this file")
    return pages


def save_document(db: Session, case_id: int, doc_type: str, filename: str, data: bytes) -> Document:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, "Only .txt and .pdf are accepted")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large")
    checksum = hashlib.sha256(data).hexdigest()
    dup = db.query(Document).filter_by(case_id=case_id, checksum=checksum).first()
    if dup:
        return dup  # never silently delete or duplicate; return the existing source
    storage = Path(config.STORAGE_DIR)
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / f"{checksum[:16]}{ext}"  # server-chosen name; user filename never used on disk
    path.write_bytes(data)
    pages = _pages_from(filename, data)
    doc = Document(case_id=case_id, doc_type=doc_type, path=str(path), checksum=checksum,
                   language=ocr.language_of(" ".join(t for t, _ in pages)))
    db.add(doc)
    db.flush()
    for i, (text, was_ocr) in enumerate(pages, 1):
        page = Page(document_id=doc.id, number=i, text=text, ocr=was_ocr)
        db.add(page)
        db.flush()
        search.index_page(db, page)
    db.commit()
    return doc


def process_document(doc_id: int) -> None:
    """Background job: extract facts and audit the AI output. Uses its own session."""
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        extract.extract_document(db, doc)
        resolve.refresh(db)
        ids = [f.id for f in db.query(Fact).filter_by(document_id=doc_id)]
        audit.log(db, "system", "extract_facts", f"document:{doc_id}", model=config.MODEL_LABEL,
                  evidence=ids, outcome=doc.status)
