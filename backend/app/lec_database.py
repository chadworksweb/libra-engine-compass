"""LEC database engine + session factory.

LEC owns its OWN database (`libra_engine_compass` on the shared DO Managed
Postgres cluster): the calibration-spend meter (`claude_api_usage`), service
keys (`api_client_keys` / `api_clients`), and the precedent corpus
(`precedent_songs`). It does NOT read Rising Compass's tables. Locally it
defaults to a self-contained SQLite file so the brain runs with zero infra.

Mirrors RC's plain-engine setup (Postgres MVCC, PgBouncer transaction pool in
prod), minus RC's app-specific concerns.
"""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.lec_config import settings

logger = logging.getLogger(__name__)


def _build_engine():
    # SQLite (local default) needs check_same_thread off for the threaded meter
    # writer; Postgres takes the small client-side pool + pre-ping like RC.
    url = settings.database_url
    if url.startswith("sqlite"):
        # Ensure the parent dir exists so a fresh clone boots with no mkdir step
        # (sqlite won't create a missing directory).
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
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
