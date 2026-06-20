"""LECG FastAPI service -- Libra Engine Compass Governance.

The public-participation venue of the Libra Engine Compass. This is the SECOND
app in the libra-engine-compass repo (Decoupling Part 2, Decision 4), separate
from the lec- instrument: the instrument applies the law, this venue is where the
public authors it.

Cut 1 (this skeleton) is READ-ONLY. It owns and serves the LEC tenets: the
canonical governed constitution lives ON LEC and is served from here, both as
JSON (the API) and as the public /tenets/ page (the view), live from the
canonical constitution -- never a hand-maintained static snapshot. No database,
no auth; the constitution is public. Cut 2 adds the write surfaces (Motion Desk /
Deliberation Chamber / amendment pipeline) behind the shared Clerk identity.

Surfaces:
  GET /                          -> redirect to /tenets/
  GET /tenets/                   -> the public tenets page (static UI)
  GET /tenets/tenets-data.js     -> window.TENETS_DATA, LIVE from the constitution
  GET /api/constitution          -> the full canonical governed constitution
  GET /api/constitution/version  -> the governed version (pin/cache probe)
  GET /health                    -> liveness + version

Run locally:  uvicorn governance.lecg_main:app --port 8014
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse
from fastapi.staticfiles import StaticFiles

from governance.lecg_constitution import load_constitution, constitution_version
from governance.lecg_tenets_view import render_data_js

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_STATIC_TENETS = Path(__file__).resolve().parent / "static" / "tenets"

app = FastAPI(
    title="Libra Engine Compass Governance",
    description="The public participation venue of the Libra Engine Compass: "
                "the home of the constitution the public governs.",
    version="0.1.0",
)

# The constitution JSON is public data other surfaces may read cross-origin (the
# LE site, RC). Read-only GETs, so a scoped allow-list is enough; widen the
# methods only when Cut 2 introduces authenticated writes. (The /tenets/ page is
# same-origin, so it needs no CORS.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://libraengine.com",
        "https://www.libraengine.com",
        "https://risingcompass.net",
        "http://localhost:8777",
        "http://127.0.0.1:8777",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Liveness probe + the version the venue currently publishes."""
    return {
        "status": "ok",
        "service": "lecg",
        "constitution_version": constitution_version(),
    }


@app.get("/api/constitution")
async def get_constitution():
    """The full canonical governed constitution: the domain-neutral le- law (tiers,
    tenets, notes, contamination modifier, dogma flag, rules R1-R15, read-method)
    merged with its governance metadata (per-item version/ratified_at/status) and
    the amendment changelog, plus the governed constitution_version. This is the
    single source of truth the tenets view renders and the instrument pins."""
    return load_constitution()


@app.get("/api/constitution/version")
async def get_constitution_version():
    """Lightweight version probe -- the governed law version, for pin/cache checks
    without transferring the whole constitution."""
    c = load_constitution()
    return {
        "version": c["constitution_version"],
        "schema_version": c.get("schema_version"),
        "ratified_at": c.get("ratified_at"),
    }


@app.get("/tenets/tenets-data.js")
async def tenets_data_js():
    """window.TENETS_DATA served LIVE from the canonical constitution. The static
    /tenets/ page loads this; it is never a hand-maintained file. Registered
    before the StaticFiles mount so it wins over a (non-existent) static file."""
    return Response(content=render_data_js(), media_type="application/javascript")


@app.get("/")
async def root():
    return RedirectResponse(url="/tenets/")


# The tenets page UI (index.html + tenets.css + tenets.js). tenets-data.js is
# intentionally NOT in this dir -- it is served live by the route above. Mounted
# last so the explicit routes above take precedence.
app.mount("/tenets", StaticFiles(directory=str(_STATIC_TENETS), html=True), name="tenets")
