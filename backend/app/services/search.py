"""Search. This is the only module allowed to branch on DB dialect.
SQLite: FTS5. Postgres backend (tsvector + pg_trgm) is added in the Postgres pass."""
import re

from rapidfuzz import fuzz
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..access import scoped_cases
from ..models import Case, Document, Fact, Page, User
from .normalise import norm_name, phonetic

NAME_THRESHOLD = 85


def reset_index(db: Session) -> None:
    db.execute(text("DROP TABLE IF EXISTS page_fts"))
    db.execute(text("CREATE VIRTUAL TABLE page_fts USING fts5(text, tokenize='unicode61')"))
    db.commit()


def index_page(db: Session, page: Page) -> None:
    db.execute(text("INSERT INTO page_fts(rowid, text) VALUES (:id, :t)"), {"id": page.id, "t": page.text})


def _fts_query(q: str) -> str | None:
    tokens = re.findall(r"\w+", q)
    return " ".join(f'"{t}"*' for t in tokens) if tokens else None


def ranked_pages(db: Session, case_ids: list[int], terms: list[str], limit: int = 40) -> list[tuple[int, int, int]]:
    """(case_id, document_id, page_number) best-first for ANY of the terms, limited to the given cases.
    Callers pass only cases the user may access; nothing outside that list can be returned."""
    if not terms or not case_ids:
        return []
    q = " OR ".join(f'"{t}"*' for t in terms)
    rows = db.execute(text(
        "SELECT d.case_id, d.id, p.number FROM page_fts f JOIN page p ON p.id = f.rowid "
        "JOIN document d ON d.id = p.document_id WHERE page_fts MATCH :q ORDER BY rank LIMIT 400"), {"q": q}).all()
    allowed = set(case_ids)
    return [tuple(r) for r in rows if r[0] in allowed][:limit]


def _partial(q: str, name: str) -> int:
    """Score for queries that are only part of a name ("Rameshbabu", "Naidu", "ramesh naidu"): every query word must
    appear inside the name, or sound like one of its words."""
    tokens = [t for t in norm_name(q).split() if len(t) >= 3]
    flat, words = name.replace(" ", ""), name.split()
    if not tokens:
        return 0
    for t in tokens:
        if t in flat or phonetic(t) in phonetic(name):
            continue
        if not any(fuzz.ratio(t, w) >= 85 for w in words):
            return 0
    return 90


def search(db: Session, user: User, q: str, limit: int = 30, doc_type: str | None = None, station: str | None = None,
           only_cases: set[int] | None = None) -> dict:
    allowed = {c.id: c for c in db.scalars(scoped_cases(user)) if (not station or c.station == station) and (only_cases is None or c.id in only_cases)}  # access scope applied first
    text_hits = []
    fts = _fts_query(q)
    if fts and allowed:
        rows = db.execute(text(
            "SELECT d.case_id, d.id, p.number, snippet(page_fts, 0, '[', ']', '…', 14), d.doc_type "
            "FROM page_fts f JOIN page p ON p.id = f.rowid JOIN document d ON d.id = p.document_id "
            "WHERE page_fts MATCH :q ORDER BY rank LIMIT 200"), {"q": fts}).all()
        for case_id, doc_id, page_no, snippet, dtype in rows:
            if case_id in allowed and len(text_hits) < limit and (not doc_type or dtype == doc_type):
                text_hits.append({"case_id": case_id, "case_no": allowed[case_id].case_no, "document_id": doc_id,
                                  "page": page_no, "snippet": snippet, "why": "text match"})

    name_matches = []
    target = norm_name(q).replace(" ", "")
    if target and allowed:
        facts = db.scalars(select(Fact).where(Fact.type.in_(["person", "alias"]), Fact.case_id.in_(list(allowed))))
        docs = {d.id: d.doc_type for d in db.query(Document).filter(Document.case_id.in_(list(allowed)))}
        for f in facts:
            if doc_type and docs.get(f.document_id) != doc_type:
                continue
            score = max(fuzz.ratio(target, f.normalised.replace(" ", "")), fuzz.ratio(phonetic(q), phonetic(f.normalised)), _partial(q, f.normalised))
            if score >= NAME_THRESHOLD:
                name_matches.append({"case_id": f.case_id, "case_no": allowed[f.case_id].case_no,
                                     "fact_id": f.id, "name": f.original, "document_id": f.document_id,
                                     "page": f.page, "span": f.span, "score": round(score),
                                     "why": f"similar name ({round(score)}%), original spelling kept"})
        best = {}  # one row per (case, spelling): the same name repeated across documents is shown once
        for m in sorted(name_matches, key=lambda m: -m["score"]):
            best.setdefault((m["case_id"], m["name"]), m)
        name_matches = list(best.values())
    return {"query": q, "text_hits": text_hits, "name_matches": name_matches[:limit]}
