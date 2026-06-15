"""LEC schema baseline (001).

LEC is a brand-new database, so the baseline IS create_all over the ORM models:
  - api_clients, api_client_keys  (service-key auth)
  - claude_api_usage              (calibration-spend meter, $5/$25 Opus)
  - precedent_songs               (precedent corpus projection; populated Phase 1)

main.py runs this same create_all on startup (lifespan), so a fresh deploy
self-initializes. Run this directly to (re)create the schema against
LEC_DATABASE_URL without booting the service:

    cd backend && python -m migrations.001_lec_baseline

New schema changes after this baseline get numbered migrations (002+),
PG-compatible (the prod DB is Postgres on the shared DO cluster).
"""

import os
import sys

# Allow running as a bare script from backend/ (python migrations/001_lec_baseline.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401  (import registers the models on Base)


def upgrade() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    upgrade()
    tables = ", ".join(sorted(Base.metadata.tables))
    print(f"LEC baseline applied against {engine.url}\n  tables: {tables}")
