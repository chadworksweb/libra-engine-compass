"""Auth for the lecg- governance venue: shared-Clerk citizen auth + admin cookie.

Two independent surfaces:

1. CITIZEN auth (the public participants). The venue rides the SHARED Clerk spine
   (LIBRA-ENGINE-ACCOUNT-ARCHITECTURE.md): it verifies the same Clerk session
   JWTs RC does (same instance / JWKS) and lazily provisions its OWN citizens row
   keyed to clerk_user_id. It does NOT invent auth and does NOT migrate RC's
   users. The Tier-2 "verified human" bit is a SHARED identity credential
   (Decision 3): read off the Clerk identity (a custom JWT claim), never stored
   on the citizen row. Ported from RC's app/services/clerk.py + app/auth.py.

   GATED ON CLERK PRO: the satellite-origin wiring on the shared Clerk app needs
   Pro. Until clerk_enabled() (LECG_CLERK_JWKS_URL set), the write surfaces are
   inert. For local end-to-end exercise, LECG_DEV_AUTH=true resolves every authed
   call to a single verified dev citizen.

2. ADMIN auth (the lifecycle console). Mirrors the lec- instrument's
   lec_admin_auth exactly: an obscured login URL + a self-contained signed HMAC
   cookie, 404 (not 401) on every admin route until all four secrets are set.

PyJWT + httpx are imported LAZILY inside the Clerk functions so the venue (and
its dev path) boots even before PyJWT is installed; they are only needed once
Clerk Pro is wired.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from governance.lecg_config import settings, clerk_enabled, dev_auth_active
from governance.lecg_database import get_db
from governance.lecg_models import Citizen

logger = logging.getLogger(__name__)


# ======================================================================
# Citizen auth -- the shared Clerk spine
# ======================================================================

_jwks_client_lock = threading.Lock()
_jwks_client = None  # type: ignore  (PyJWKClient, lazily built)


def _get_jwks_client():
    """Process-wide PyJWKClient against the shared Clerk JWKS. Lazily built (and
    PyJWT lazily imported) so config-less boots never touch it."""
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    with _jwks_client_lock:
        if _jwks_client is None:
            if not settings.clerk_jwks_url:
                raise RuntimeError(
                    "LECG_CLERK_JWKS_URL is not set; Clerk verification is "
                    "disabled (gated on Clerk Pro). Set it to enable citizen auth."
                )
            from jwt import PyJWKClient  # lazy
            _jwks_client = PyJWKClient(settings.clerk_jwks_url, cache_keys=True)
    return _jwks_client


def verify_clerk_jwt(token: str) -> dict:
    """Verify a shared-Clerk session JWT and return its claims. Raises
    jwt.PyJWTError subclasses on any failure (caller maps to HTTPException).
    Ported from RC's clerk.verify_clerk_jwt."""
    import jwt  # lazy

    if not token:
        raise jwt.InvalidTokenError("Empty token")

    signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key

    decode_kwargs: dict = {
        "algorithms": ["RS256"],
        "options": {"require": ["exp", "iat", "sub"]},
    }
    if settings.clerk_jwks_url:
        issuer = settings.clerk_jwks_url.rsplit("/.well-known/", 1)[0]
        decode_kwargs["issuer"] = issuer

    claims = jwt.decode(token, signing_key, **decode_kwargs)

    if settings.clerk_authorized_party:
        azp = claims.get("azp")
        if azp and azp != settings.clerk_authorized_party:
            raise jwt.InvalidTokenError(f"Unexpected azp: {azp}")

    return claims


def _generate_anon_id() -> str:
    """Opaque, stable, non-sequential public id. Mirrors RC's scheme."""
    return f"Citizen-{secrets.token_hex(4)}"


def ensure_citizen_for_clerk_id(db: Session, clerk_user_id: str) -> Citizen:
    """Return the local citizens row for this Clerk subject, creating it on first
    sight (lazy provisioning, the satellite pattern). handle is NULL until the
    citizen claims one. Mirrors RC's ensure_user_for_clerk_id, minus the RC-only
    subscriber-link tail."""
    citizen = db.query(Citizen).filter(Citizen.clerk_user_id == clerk_user_id).first()
    if citizen is not None:
        return citizen

    for _ in range(5):
        candidate = _generate_anon_id()
        if not db.query(Citizen).filter(Citizen.anon_id == candidate).first():
            break
    else:
        raise RuntimeError("Could not generate unique anon_id after 5 attempts")

    citizen = Citizen(clerk_user_id=clerk_user_id, anon_id=candidate, status="active")
    db.add(citizen)
    db.commit()
    db.refresh(citizen)
    logger.info("Provisioned new citizen for clerk_user_id=%s (anon=%s)", clerk_user_id, candidate)
    return citizen


def _extract_clerk_token(authorization: Optional[str], session_cookie: Optional[str]) -> Optional[str]:
    """Authorization: Bearer beats the __session cookie. Ported from RC."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1].strip()
        if token:
            return token
    if session_cookie:
        return session_cookie
    return None


def _dev_citizen(db: Session) -> Citizen:
    """Resolve (and verify-stamp) the single dev citizen for the local bypass.
    Gives it a handle so the Tier-2 gate passes end-to-end. NEVER reachable when
    Clerk is wired (dev_auth_active is False then)."""
    citizen = ensure_citizen_for_clerk_id(db, settings.dev_citizen_clerk_id)
    if not citizen.handle:
        citizen.handle = "dev-citizen"
        db.commit()
        db.refresh(citizen)
    return citizen


def require_citizen(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    __session: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Citizen:
    """Tier-1 citizen auth. Verifies the shared-Clerk session JWT, lazily
    provisions a citizens row, stamps request.state, returns the row (handle may
    be NULL pre-onboarding). The verified-human bit is read off the claims and
    stashed on request.state for the Tier-2 gate (Decision 3).

    When Clerk is not wired and LECG_DEV_AUTH is on, resolves to the dev citizen.
    Otherwise 503 (identity not yet wired -- the honest Cut-2/Clerk-Pro state).
    """
    if dev_auth_active():
        citizen = _dev_citizen(db)
        request.state.citizen_id = citizen.id
        request.state.clerk_user_id = citizen.clerk_user_id
        request.state.lecg_verified = True  # dev citizen is treated as verified
        return citizen

    if not clerk_enabled():
        raise HTTPException(
            status_code=503,
            detail="Citizen identity is not yet wired (gated on Clerk Pro).",
        )

    import jwt  # lazy
    token = _extract_clerk_token(authorization, __session)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = verify_clerk_jwt(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.PyJWTError as exc:
        logger.warning("Clerk JWT verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid session")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    citizen = ensure_citizen_for_clerk_id(db, clerk_user_id)
    if citizen.status == "banned":
        raise HTTPException(status_code=403, detail="Account banned")

    request.state.citizen_id = citizen.id
    request.state.clerk_user_id = clerk_user_id
    # The Tier-2 verified-human bit is a SHARED identity credential (Decision 3):
    # read it straight off the Clerk claims, never off a local column.
    request.state.lecg_verified = bool(claims.get(settings.clerk_verified_claim))
    return citizen


def require_verified_citizen(
    request: Request,
    citizen: Citizen = Depends(require_citizen),
) -> Citizen:
    """Tier-2 gate for the write surfaces (filing a motion, posting in the
    chamber). Requires: an active citizen, a claimed handle, AND the shared
    verified-human credential. Mirrors RC's _require_tier2, but the verified bit
    comes from the shared identity, not a local tier column (Decision 3)."""
    if citizen.status != "active":
        raise HTTPException(status_code=403, detail="Account not active")
    if not getattr(request.state, "lecg_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Participation requires identity verification (a verified human).",
        )
    if not citizen.handle:
        raise HTTPException(status_code=403, detail="Claim a handle before participating.")
    return citizen


# ======================================================================
# Admin auth -- obscured login + signed HMAC cookie (mirrors lec_admin_auth)
# ======================================================================

ADMIN_COOKIE_NAME = "lecg_admin_session"


def admin_configured() -> bool:
    return bool(
        settings.admin_login_token
        and settings.admin_username
        and settings.admin_password
        and settings.admin_secret
    )


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload_b64: str) -> str:
    sig = hmac.new(
        settings.admin_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64e(sig)


def mint_admin_session(ttl_seconds: int) -> str:
    exp = int(time.time()) + ttl_seconds
    payload = _b64e(json.dumps({"exp": exp, "u": settings.admin_username}).encode("utf-8"))
    return f"{payload}.{_sign(payload)}"


def _verify_admin_session(cookie: Optional[str]) -> Optional[str]:
    """Return the admin username on a valid cookie, else None."""
    if not cookie or not admin_configured():
        return None
    try:
        payload, sig = cookie.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(payload)):
        return None
    try:
        data = json.loads(_b64d(payload))
    except Exception:
        return None
    if int(data.get("exp", 0)) <= int(time.time()):
        return None
    return data.get("u")


def check_admin_login_token(token: str) -> bool:
    if not admin_configured():
        return False
    return hmac.compare_digest(token, settings.admin_login_token)


def check_admin_credentials(username: str, password: str) -> bool:
    if not admin_configured():
        return False
    user_ok = hmac.compare_digest(username or "", settings.admin_username)
    pass_ok = hmac.compare_digest(password or "", settings.admin_password)
    return user_ok and pass_ok


def require_admin(
    request: Request,
    lecg_admin_session: Optional[str] = Cookie(default=None),
) -> str:
    """Dependency for every protected admin route. 404 (not 401) when not authed,
    so the whole admin surface is invisible to an unauthenticated caller -- same
    posture as RC + the lec instrument. Returns the admin username."""
    username = _verify_admin_session(lecg_admin_session)
    if not username:
        raise HTTPException(status_code=404, detail="Not found")
    request.state.admin_username = username
    return username
