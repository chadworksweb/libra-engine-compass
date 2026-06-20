"""LECG database engine + session factory -- the governance venue's OWN DB.

Decision 1/4: the lecg- venue is a distinct app with a distinct database from
the lec- instrument. This engine is wholly separate from app.lec_database; the
two never share a session or a Base. The venue owns: citizens (lazily
provisioned on the shared Clerk spine), motions, motion_arguments, and the
constitution-amendment ledger (the ratification write-back's record of every
change to the law).

Mirrors the instrument's plain-engine setup (Postgres MVCC + PgBouncer pool in
prod, a self-contained SQLite file locally so the venue boots with zero infra).
"""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from governance.lecg_config import settings

logger = logging.getLogger(__name__)


def _build_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        # Create the parent dir so a fresh clone boots with no mkdir step.
        prefix = "sqlite:///"
        if url.startswith(prefix):
            db_path = url[len(prefix):]
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """The governance venue's declarative base. Distinct from the instrument's
    app.lec_database.Base -- the two schemas never mix."""
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
