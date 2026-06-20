"""Motion Desk admin console (lecg-) -- the lifecycle + the ratification write-back.

Gated by an obscured login URL (/lecg-admin-<token>) + a signed HMAC cookie
(governance.lecg_auth), 404 on every protected route until admin is configured --
same posture as RC + the lec instrument. Admin gets lifecycle control only
(move-to-deliberation, ratify, reject, covered); there is NO back-door tenet
editor. The ONLY way the law changes is the ratify path, which records a
constitution_amendment tied to the motion (Integrity notes).

Surface:
  GET  /lecg-admin-{token}                         obscured login page
  POST /lecg-admin-{token}/login                   authenticate -> session cookie
  POST /admin/logout                               clear cookie
  GET  /api/admin/motions                          queue (status-ordered)
  GET  /api/admin/motions/{id}                     detail
  POST /api/admin/motions/{id}/move-to-deliberation
  POST /api/admin/motions/{id}/ratify              ratify + WRITE BACK to the law
  POST /api/admin/motions/{id}/reject
  POST /api/admin/motions/{id}/covered
  GET  /api/admin/edition/preview                  the governed constitution to adopt
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from governance.lecg_auth import (
    ADMIN_COOKIE_NAME, check_admin_credentials, check_admin_login_token,
    mint_admin_session, require_admin,
)
from governance.lecg_config import settings
from governance.lecg_database import get_db
from governance.lecg_models import Motion
from governance import lecg_amendments as amendments_svc
from governance import lecg_motions as motions_svc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["motions-admin"])


# ---------- minimal obscured login ----------

_LOGIN_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Compass Governance</title>
<style>body{font-family:Cardo,Georgia,serif;background:#f4efe6;color:#3a3026;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
form{background:#fffdf8;border:1px solid #d8cdb8;border-radius:10px;padding:2rem;
width:320px;box-shadow:0 2px 16px rgba(80,60,30,.08)}h1{font-size:1.1rem;margin:0 0 1rem;
font-variant:small-caps;letter-spacing:.04em}input{width:100%;box-sizing:border-box;
padding:.6rem;margin:.35rem 0;border:1px solid #cdbfa6;border-radius:6px;background:#fdfbf6}
button{width:100%;padding:.65rem;margin-top:.7rem;border:0;border-radius:6px;
background:#6b4f2c;color:#f7f1e6;font-size:1rem;cursor:pointer}.err{color:#9b2c2c;
font-size:.85rem;min-height:1.1em}</style></head><body>
<form id="f"><h1>Compass Governance</h1>
<input id="u" placeholder="username" autocomplete="username">
<input id="p" type="password" placeholder="password" autocomplete="current-password">
<button type="submit">Enter</button><div class="err" id="e"></div></form>
<script>document.getElementById('f').addEventListener('submit',async e=>{e.preventDefault();
const r=await fetch('__LOGIN_ACTION__',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({username:u.value,password:p.value})});
if(r.ok){const j=await r.json();location.href=j.redirect||'/motion-desk/'}
else{e_.textContent='Wrong username or password'}});
const e_=document.getElementById('e');</script></body></html>"""


class LoginIn(BaseModel):
    username: str
    password: str


@router.get("/lecg-admin-{token}", response_class=HTMLResponse)
def login_page(token: str):
    if not check_admin_login_token(token):
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(_LOGIN_HTML.replace("__LOGIN_ACTION__", f"/lecg-admin-{token}/login"))


@router.post("/lecg-admin-{token}/login")
def login(token: str, body: LoginIn, request: Request):
    if not check_admin_login_token(token):
        raise HTTPException(status_code=404, detail="Not found")
    if not check_admin_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    resp = JSONResponse({"ok": True, "redirect": "/motion-desk/"})
    ttl = settings.admin_session_hours * 3600
    resp.set_cookie(
        ADMIN_COOKIE_NAME, mint_admin_session(ttl), max_age=ttl,
        httponly=True, samesite="lax", secure=(request.url.scheme == "https"), path="/",
    )
    return resp


@router.post("/admin/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return resp


# ---------- lifecycle ----------

class ResolutionIn(BaseModel):
    resolution_summary: str = Field(..., min_length=10, max_length=4000)


class AmendmentIn(BaseModel):
    change: str = Field(..., description="add | amend | remove")
    target_kind: str = Field(..., description="tenet|rule|modifier|flag|note|tier|method|process")
    target_ref: Optional[str] = Field(None, description="the amended item id (e.g. 'violet-01', 'R1')")
    to_version: Optional[str] = Field(None, description="the new item version, e.g. '1.1'")
    new_core: Optional[str] = Field(None, description="the new neutral law text (required for amend)")
    summary: str = Field(..., min_length=10, max_length=2000, description="the changelog line")


class RatifyIn(BaseModel):
    resolution_summary: str = Field(..., min_length=10, max_length=4000)
    amendment: Optional[AmendmentIn] = Field(
        None,
        description="The write-back payload. Supply the FINAL ratified law text. "
                    "Omit for a process motion that blesses without retexting.",
    )


@router.get("/api/admin/motions")
def admin_list_motions(
    status: Optional[str] = None,
    motion_type: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    q = db.query(Motion)
    if status:
        if status not in motions_svc.VALID_STATUSES:
            raise HTTPException(422, f"Unknown status: {status}")
        q = q.filter(Motion.status == status)
    if motion_type:
        if motion_type not in motions_svc.VALID_MOTION_TYPES:
            raise HTTPException(422, f"Unknown motion_type: {motion_type}")
        q = q.filter(Motion.motion_type == motion_type)
    rows = q.order_by(Motion.filed_at.desc()).limit(max(1, min(limit, 500))).all()
    status_priority = {"filed": 0, "in_deliberation": 1, "ratified": 2, "covered": 3, "rejected": 4}
    rows.sort(key=lambda m: (status_priority.get(m.status, 99), -(m.filed_at.timestamp() if m.filed_at else 0)))
    return [motions_svc.motion_to_dict(db, m) for m in rows]


@router.get("/api/admin/motions/{motion_id}")
def admin_get_motion(motion_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    motion = db.query(Motion).get(motion_id)
    if motion is None:
        raise HTTPException(404, "Motion not found")
    return motions_svc.motion_to_dict(db, motion)


@router.post("/api/admin/motions/{motion_id}/move-to-deliberation")
def admin_move_to_deliberation(motion_id: int, db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    motion = db.query(Motion).get(motion_id)
    if motion is None:
        raise HTTPException(404, "Motion not found")
    motion = motions_svc.transition_status(db, motion, "in_deliberation", admin_username=admin)
    return motions_svc.motion_to_dict(db, motion)


@router.post("/api/admin/motions/{motion_id}/ratify")
def admin_ratify(motion_id: int, data: RatifyIn, db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    """Ratify the motion AND write the amendment back to the constitution. The
    amendment payload carries the FINAL ratified law text -- the one place the law
    can change, and only through this pipeline (no back-door editor)."""
    motion = db.query(Motion).get(motion_id)
    if motion is None:
        raise HTTPException(404, "Motion not found")
    amendment = data.amendment.model_dump() if data.amendment else None
    motion, amendment_row = amendments_svc.ratify_motion(
        db, motion, resolution_summary=data.resolution_summary,
        admin_username=admin, amendment=amendment,
    )
    out = motions_svc.motion_to_dict(db, motion)
    if amendment_row is not None:
        out["amendment"] = {
            "id": amendment_row.id,
            "change": amendment_row.change,
            "target_kind": amendment_row.target_kind,
            "target_ref": amendment_row.target_ref,
            "from_version": amendment_row.from_version,
            "to_version": amendment_row.to_version,
            "constitution_version_before": amendment_row.constitution_version_before,
            "constitution_version_after": amendment_row.constitution_version_after,
        }
    return out


@router.post("/api/admin/motions/{motion_id}/reject")
def admin_reject(motion_id: int, data: ResolutionIn, db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    motion = db.query(Motion).get(motion_id)
    if motion is None:
        raise HTTPException(404, "Motion not found")
    motion = motions_svc.transition_status(db, motion, "rejected", admin_username=admin, resolution_summary=data.resolution_summary)
    return motions_svc.motion_to_dict(db, motion)


@router.post("/api/admin/motions/{motion_id}/covered")
def admin_covered(motion_id: int, data: ResolutionIn, db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    motion = db.query(Motion).get(motion_id)
    if motion is None:
        raise HTTPException(404, "Motion not found")
    motion = motions_svc.transition_status(db, motion, "covered", admin_username=admin, resolution_summary=data.resolution_summary)
    return motions_svc.motion_to_dict(db, motion)


@router.get("/api/admin/edition/preview")
def admin_edition_preview(db: Session = Depends(get_db), admin: str = Depends(require_admin)):
    """The governed constitution the instrument would adopt next -- genesis +
    every ratified amendment. Adopting it (writing le-baseline + re-pinning) stays
    a deliberate, gated act outside this endpoint."""
    return amendments_svc.materialize_edition(db)
