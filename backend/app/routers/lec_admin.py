"""LEC admin console routes.

A single dashboard at /admin, gated behind an obscured login URL
(/lec-admin-<token>) + an HttpOnly signed session cookie (app.services.lec_admin_auth).
All routes 404 unless admin is configured (LEC_ADMIN_LOGIN_TOKEN /
LEC_ADMIN_PASSWORD / LEC_ADMIN_SECRET all set), so the surface is invisible
until then. The dashboard markup is served whole; its data comes from
GET /admin/api/summary (services/dashboard.build_summary).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.lec_admin_ui import DASHBOARD_HTML, LOGIN_HTML, PIPELINE_HTML
from app.lec_config import settings
from app.lec_database import SessionLocal
from app.services.lec_admin_auth import (
    COOKIE_NAME, check_credentials, check_login_token, mint_session, require_admin,
)
from app.services.lec_dashboard import build_summary

router = APIRouter(tags=["admin"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.get("/lec-admin-{token}", response_class=HTMLResponse)
def login_page(token: str):
    """The obscured login page. Any token but the configured one 404s, so a
    scanner hitting /admin or a guessed path finds nothing."""
    if not check_login_token(token):
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(LOGIN_HTML.replace("__LOGIN_ACTION__", f"/lec-admin-{token}/login"))


@router.post("/lec-admin-{token}/login")
def login(token: str, body: LoginIn, request: Request):
    if not check_login_token(token):
        raise HTTPException(status_code=404, detail="Not found")
    if not check_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    resp = JSONResponse({"ok": True, "redirect": "/admin"})
    ttl = settings.admin_session_hours * 3600
    resp.set_cookie(
        COOKIE_NAME,
        mint_session(ttl),
        max_age=ttl,
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https"),
        path="/",
    )
    return resp


@router.post("/admin/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@router.get("/admin", response_class=HTMLResponse)
def dashboard(_: None = Depends(require_admin)):
    return HTMLResponse(DASHBOARD_HTML)


@router.get("/admin/pipeline", response_class=HTMLResponse)
def pipeline(_: None = Depends(require_admin)):
    return HTMLResponse(PIPELINE_HTML)


@router.get("/admin/api/summary")
def summary(_: None = Depends(require_admin)):
    db = SessionLocal()
    try:
        return build_summary(db)
    finally:
        db.close()
