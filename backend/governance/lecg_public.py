"""The public constitution surface -- governance-owned, hosted by the instrument.

The tenets are the LEC tenets: they live ON LEC and are served from
lec.libraengine.com. This router carries the public, read-only constitution
surface (the law display); the lec instrument includes it (app/lec_main.py) and
mounts the tenets page static dir. Keeping the code here in governance/ preserves
ownership -- the constitution is governance-owned `le-` law -- while the
instrument HOSTS it. (Cut 2's separate lecg venue is the amendment machinery, not
the tenets display.)

Routes (all public, NO service-key gate):
  GET /api/constitution            -> the full canonical governed constitution
  GET /api/constitution/version    -> the governed version (pin/cache probe)
  GET /tenets/tenets-data.js       -> window.TENETS_DATA, LIVE from the constitution
  GET /api/calibrator-changelog      -> the calibrator changelog timeline (rules + lenses + versions)
  GET /changelog/changelog-data.js   -> window.CHANGELOG_DATA, LIVE from the changelog

The tenets page UI (index.html + tenets.css + tenets.js) is the static dir
STATIC_TENETS; the host app mounts it at /tenets (StaticFiles, html=True) AFTER
including this router so the live /tenets/tenets-data.js route wins.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from governance.lecg_constitution import load_constitution
from governance.lecg_tenets_view import render_data_js
from governance.lecg_changelog_view import build_changelog, render_data_js as render_changelog_data_js

# governance/static/tenets/{index.html,tenets.css,tenets.js} (no tenets-data.js --
# that is served live by the route below).
STATIC_TENETS = Path(__file__).resolve().parent / "static" / "tenets"
STATIC_CHANGELOG = Path(__file__).resolve().parent / "static" / "changelog"

router = APIRouter(tags=["constitution"])


@router.get("/api/constitution")
async def get_constitution():
    """The full canonical governed constitution: the domain-neutral le- law merged
    with its governance metadata + changelog + the governed constitution_version.
    The single source of truth the tenets page renders and the instrument pins."""
    return load_constitution()


@router.get("/api/constitution/version")
async def get_constitution_version():
    """Lightweight version probe -- the governed law version."""
    c = load_constitution()
    return {
        "version": c["constitution_version"],
        "schema_version": c.get("schema_version"),
        "ratified_at": c.get("ratified_at"),
    }


@router.get("/tenets/tenets-data.js")
async def tenets_data_js():
    """window.TENETS_DATA served LIVE from the canonical constitution. The static
    /tenets/ page loads this; never a hand-maintained file."""
    return Response(content=render_data_js(), media_type="application/javascript")


@router.get("/api/calibrator-changelog")
async def get_calibrator_changelog():
    """The public Calibrator Changelog timeline: changes to the calibrator itself
    (rule changes + reading-lens additions + law versions), sourced from LEC's own
    changelog + constitution. Never reads Rising Compass; the per-song calibration
    log is RC product data."""
    return build_changelog()


@router.get("/changelog/changelog-data.js")
async def changelog_data_js():
    """window.CHANGELOG_DATA served LIVE from the governed changelog. The static
    /changelog/ page loads this; never a hand-maintained file."""
    return Response(content=render_changelog_data_js(), media_type="application/javascript")
