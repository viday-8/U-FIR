from sqlalchemy.orm import Session

from . import cache
from .models import Audit


def log(db: Session, actor: str, action: str, resource: str, *, model=None, evidence=None, outcome=None):
    db.add(Audit(actor=actor, action=action, resource=resource, model=model, evidence=evidence, outcome=outcome))
    db.commit()
    cache.bump()  # every consequential action is audited, so this also invalidates cached read models
