"""LECG governance schema baseline (001).

The governance venue is a brand-new database, so the baseline IS create_all over
the ORM models:
  - citizens                  shared-Clerk-keyed local participant records
  - motions                   the Motion Desk
  - motion_arguments          the Deliberation Chamber
  - constitution_amendments   the ratification write-back ledger

lecg_main.py runs this same create_all on startup (lifespan), so a fresh deploy
self-initializes. Run this directly to (re)create the schema against
LECG_DATABASE_URL without booting the venue:

    cd backend && python -m migrations.001_lecg_baseline

This is SEPARATE from 001_lec_baseline (the instrument's schema) -- the venue
owns a distinct database (Decision 1/4). New governance schema changes after this
baseline get numbered lecg migrations, PG-compatible (prod is Postgres on the
shared DO cluster).
"""

import os
import sys

# Allow running as a bare script from backend/ (python migrations/001_lecg_baseline.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from governance.lecg_database import Base, engine  # noqa: E402
from governance import lecg_models  # noqa: E402,F401  (import registers the models on Base)


def upgrade() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    upgrade()
    tables = ", ".join(sorted(Base.metadata.tables))
    print(f"LECG governance baseline applied against {engine.url}\n  tables: {tables}")
