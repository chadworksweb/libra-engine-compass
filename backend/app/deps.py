"""Shared FastAPI dependencies for LEC.

Service-key auth on /api/score. LEC issues + verifies the keys its clients (RC,
LT, future chargers) present in the X-Api-Key header, checked against
api_client_keys (sha256 of the raw key). Enforcement is gated on
settings.auth_required so local + the Phase 0 parity harness run open; flip
LEC_AUTH_REQUIRED=true once keys are issued.
"""

import hashlib
from datetime import datetime

from fastapi import Header, HTTPException

from app.config import settings
from app.database import SessionLocal
from app.models import ApiClientKey


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Verify the X-Api-Key header against a live (non-revoked) api_client_keys
    row. No-op when auth is not required. Raises 401 on a missing/unknown key."""
    if not settings.auth_required:
        return
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-Api-Key required")
    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    db = SessionLocal()
    try:
        row = (
            db.query(ApiClientKey)
            .filter(ApiClientKey.key_hash == key_hash, ApiClientKey.revoked_at.is_(None))
            .first()
        )
        if not row:
            raise HTTPException(status_code=401, detail="Invalid API key")
        row.last_used_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
