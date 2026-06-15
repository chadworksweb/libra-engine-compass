"""Admin-panel auth for LEC: an obscured login URL + a stateless signed session
cookie. Mirrors RC's posture (secret path, HttpOnly cookie, 404 when not authed)
but stays dependency-free -- the cookie is a self-contained HMAC token, so there
is no sessions table and nothing to migrate.

Fail-CLOSED: unless all three of admin_login_token / admin_password /
admin_secret are set, admin_configured() is False and every admin route 404s,
so the panel simply does not exist until it is configured.
"""

import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request

from app.config import settings

COOKIE_NAME = "lec_admin_session"


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


def mint_session(ttl_seconds: int) -> str:
    """A signed `<payload>.<sig>` cookie value carrying only an expiry."""
    exp = int(time.time()) + ttl_seconds
    payload = _b64e(json.dumps({"exp": exp}).encode("utf-8"))
    return f"{payload}.{_sign(payload)}"


def verify_session(cookie: str | None) -> bool:
    if not cookie or not admin_configured():
        return False
    try:
        payload, sig = cookie.split(".", 1)
    except ValueError:
        return False
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    try:
        data = json.loads(_b64d(payload))
    except Exception:
        return False
    return int(data.get("exp", 0)) > int(time.time())


def check_login_token(token: str) -> bool:
    """Constant-time match of a URL path token against the configured login
    token. False (and the caller 404s) when admin is not configured."""
    if not admin_configured():
        return False
    return hmac.compare_digest(token, settings.admin_login_token)


def check_credentials(username: str, password: str) -> bool:
    """Constant-time match of both username and password. Both are compared even
    on a username miss so the response time does not leak which one was wrong."""
    if not admin_configured():
        return False
    user_ok = hmac.compare_digest(username or "", settings.admin_username)
    pass_ok = hmac.compare_digest(password or "", settings.admin_password)
    return user_ok and pass_ok


def require_admin(request: Request) -> None:
    """Dependency for every protected admin route. 404 (not 401) when not
    authed, so the whole admin surface is invisible to an unauthenticated
    caller -- same posture as RC."""
    if not verify_session(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(status_code=404, detail="Not found")
