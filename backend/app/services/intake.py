"""Reads an uploaded file just enough to suggest where it belongs. Nothing is saved here: the officer confirms
the document type and case before anything is stored (so uncertain matches never attach silently)."""
import hashlib
import re

from sqlalchemy.orm import Session

from ..access import scoped_cases
from ..models import Document, User

HEADINGS = [("fir", r"FIRST INFORMATION REPORT"), ("seizure", r"SEIZURE PANCHANAMA|MAHAZAR|PANCHANAMA"),
            ("diary", r"CASE DIARY"), ("progress", r"PROGRESS REPORT"), ("remand", r"REMAND REPORT")]
CASE_REF = re.compile(r"(?:Cr\.?\s*No\.?|Crime\s*No\.?)\s*:?\s*(\d{1,5})\s*/\s*(\d{4})", re.I)
REG_DATE = re.compile(r"Date of registration:?\s*(\d{2})[./-](\d{2})[./-](\d{4})", re.I)
CASE_NO_PARTS = re.compile(r"(\d{1,5})\s*/\s*(\d{4})")


def guess_doc_type(text: str) -> str | None:
    head = text[:500]
    for key, pattern in HEADINGS:
        if re.search(pattern, head, re.I):
            return key
    return None


def find_case_ref(text: str) -> tuple[int, int] | None:
    m = CASE_REF.search(text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def find_registered_on(text: str) -> str | None:
    m = REG_DATE.search(text)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def match_cases(db: Session, user: User, ref: tuple[int, int] | None) -> list[dict]:
    """Only cases the user may access are ever considered, so another district's case cannot be suggested or confirmed."""
    if not ref:
        return []
    out = []
    for c in db.scalars(scoped_cases(user)):
        if any((int(n), int(y)) == ref for n, y in CASE_NO_PARTS.findall(c.case_no)):
            out.append({"id": c.id, "case_no": c.case_no, "station": c.station})
    return out


def duplicate_of(db: Session, user: User, data: bytes) -> dict | None:
    checksum = hashlib.sha256(data).hexdigest()
    ids = {c.id: c for c in db.scalars(scoped_cases(user))}
    d = db.query(Document).filter(Document.checksum == checksum, Document.case_id.in_(list(ids) or [0])).first()
    return {"document_id": d.id, "case_id": d.case_id, "case_no": ids[d.case_id].case_no} if d else None
