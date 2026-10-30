from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # investigator|supervisor|analyst|admin
    district: Mapped[str | None] = mapped_column(String(50))  # None = all districts (admin)
    active: Mapped[bool] = mapped_column(default=True)


class Case(Base):
    __tablename__ = "case"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_no: Mapped[str] = mapped_column(String(40), unique=True)
    district: Mapped[str] = mapped_column(String(50), index=True)
    station: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="open")
    registered_on: Mapped[str] = mapped_column(String(10))
    documents: Mapped[list["Document"]] = relationship(back_populates="case")


class Document(Base):
    __tablename__ = "document"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(30))  # fir|diary|seizure|progress
    path: Mapped[str] = mapped_column(String(300))
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="received")
    language: Mapped[str] = mapped_column(String(8), default="en")  # en | te | mixed (detected)
    reviewed_by: Mapped[str | None] = mapped_column(String(50))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    case: Mapped[Case] = relationship(back_populates="documents")
    pages: Mapped[list["Page"]] = relationship(back_populates="document")


class Page(Base):
    __tablename__ = "page"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    ocr: Mapped[bool] = mapped_column(default=False)  # True when the text was machine-read from an image
    document: Mapped[Document] = relationship(back_populates="pages")


class Audit(Base):
    """Append-only: no update/delete code paths exist."""
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actor: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50))
    resource: Mapped[str] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(60))
    evidence: Mapped[list | None] = mapped_column(JSON)
    outcome: Mapped[str | None] = mapped_column(String(30))


class Fact(Base):
    """An extracted fact. `original` is exactly what the source says; `normalised` is for search/matching."""
    __tablename__ = "fact"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), index=True)
    page: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20), index=True)
    original: Mapped[str] = mapped_column(String(300))
    normalised: Mapped[str] = mapped_column(String(300), index=True)
    span: Mapped[str] = mapped_column(Text)  # verbatim quote from the page
    attributes: Mapped[dict | None] = mapped_column(JSON)  # e.g. father, age, resident
    model: Mapped[str] = mapped_column(String(60))
    corrected: Mapped[bool] = mapped_column(default=False)  # an officer edited or added this fact
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Entity(Base):
    """A person as described within one case. Cross-case sameness is only ever a Candidate until reviewed."""
    __tablename__ = "entity"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    key: Mapped[str] = mapped_column(String(300))  # normalised name, unique per case
    label: Mapped[str] = mapped_column(String(300))  # original spelling of the richest mention
    attributes: Mapped[dict | None] = mapped_column(JSON)
    fact_ids: Mapped[list] = mapped_column(JSON)


class Candidate(Base):
    """Possible same-person link between two entities. status: unreviewed|confirmed|rejected|deferred."""
    __tablename__ = "candidate"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_a: Mapped[int] = mapped_column(ForeignKey("entity.id"), index=True)
    entity_b: Mapped[int] = mapped_column(ForeignKey("entity.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    signals: Mapped[list] = mapped_column(JSON)
    missing: Mapped[list] = mapped_column(JSON)
    evidence: Mapped[list] = mapped_column(JSON)  # fact ids
    status: Mapped[str] = mapped_column(String(15), default="unreviewed")
    decided_by: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LegalSuggestion(Base):
    """Advisory only. status: suggested|insufficient|accepted|rejected."""
    __tablename__ = "legal_suggestion"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    ref_id: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(15))
    rationale: Mapped[str] = mapped_column(Text)
    fact_ids: Mapped[list] = mapped_column(JSON)
    passages: Mapped[list] = mapped_column(JSON)  # [{document_id, page, span}] verbatim quotes
    already_cited: Mapped[bool] = mapped_column(default=False)
    catalogue_version: Mapped[str] = mapped_column(String(20))
    decided_by: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Draft(Base):
    """Case diary / chargesheet draft. status: draft|in_review|approved|returned. Never official until approved."""
    __tablename__ = "draft"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(20))  # case_diary|chargesheet
    status: Mapped[str] = mapped_column(String(12), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    sections: Mapped[list] = mapped_column(JSON)
    author: Mapped[str] = mapped_column(String(50))
    reviewer: Mapped[str | None] = mapped_column(String(50))
    comments: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DraftVersion(Base):
    __tablename__ = "draft_version"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("draft.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    sections: Mapped[list] = mapped_column(JSON)
    author: Mapped[str] = mapped_column(String(50))
    note: Mapped[str] = mapped_column(String(100))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FactCorrection(Base):
    """History of officer changes to extracted facts. The source document itself is never modified."""
    __tablename__ = "fact_correction"
    id: Mapped[int] = mapped_column(primary_key=True)
    fact_id: Mapped[int] = mapped_column(Integer, index=True)  # kept even after a fact is removed
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    action: Mapped[str] = mapped_column(String(10))  # edit | remove | add
    old_value: Mapped[str | None] = mapped_column(String(300))
    new_value: Mapped[str | None] = mapped_column(String(300))
    fact_type: Mapped[str] = mapped_column(String(20))
    by: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CaseTag(Base):
    """Officer override of the automatic offence-type tags for one case."""
    __tablename__ = "case_tag"
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    tags: Mapped[list] = mapped_column(JSON)
    by: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Accused(Base):
    """A person in custody/bail terms. Separate from extracted persons: an officer decides who is an accused."""
    __tablename__ = "accused"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    father_or_spouse: Mapped[str | None] = mapped_column(String(200))
    age: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(15), default="named")  # named|arrested|remanded|bailed|absconding
    arrested_on: Mapped[str | None] = mapped_column(String(10))
    remand_till: Mapped[str | None] = mapped_column(String(10))
    bail_on: Mapped[str | None] = mapped_column(String(10))


class Property(Base):
    """Seizure register entry (malkhana): what was seized, where it is, and sample/lab status."""
    __tablename__ = "property"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # liquor|ganja|vehicle|other
    description: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[str | None] = mapped_column(String(100))
    custody: Mapped[str] = mapped_column(String(120), default="Station malkhana")
    status: Mapped[str] = mapped_column(String(20), default="seized")  # seized|sample_sent|lab_report_received|produced_in_court|released|destroyed
    sample_sent_on: Mapped[str | None] = mapped_column(String(10))
    lab_report_on: Mapped[str | None] = mapped_column(String(10))


class Milestone(Base):
    """A date that must not be missed: chargesheet limit, remand expiry, court hearing, lab report."""
    __tablename__ = "milestone"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    due_on: Mapped[str] = mapped_column(String(10), index=True)
    done: Mapped[bool] = mapped_column(default=False)


class CaseCheck(Base):
    """Manual ticks on the compliance checklist (the other items are derived from the records)."""
    __tablename__ = "case_check"
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    done: Mapped[bool] = mapped_column(default=False)
    by: Mapped[str] = mapped_column(String(50))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
