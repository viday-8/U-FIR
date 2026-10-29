"""The single access rule. Every endpoint, search, snippet, count and Copilot
retrieval must go through scoped_cases()/get_case_or_404()."""
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Case, User
from .security import read_token


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    username = read_token(token) if token else None
    user = db.scalar(select(User).where(User.username == username)) if username else None
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


def can_access(user: User, case: Case) -> bool:
    return user.district is None or user.district == case.district


def scoped_cases(user: User):
    """Base query for cases the user may see. Build every case-related query on this."""
    q = select(Case)
    if user.district is not None:
        q = q.where(Case.district == user.district)
    return q


def get_case_or_404(db: Session, user: User, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if not case or not can_access(user, case):
        raise HTTPException(404, "Not found")  # same response for missing and restricted
    return case


def require_role(user: User, *roles: str):
    if user.role not in roles:
        raise HTTPException(403, "Not permitted")
