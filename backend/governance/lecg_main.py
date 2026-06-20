"""LECG FastAPI service -- Libra Engine Compass Governance.

The public-participation venue of the Libra Engine Compass. This is the SECOND
app in the libra-engine-compass repo (Decoupling Part 2, Decision 4), separate
from the lec- instrument: the instrument applies the law, this venue is where the
public authors it.

Cut 1 (this skeleton) is READ-ONLY: it serves the canonical governed constitution
and its version. No database, no auth -- the constitution is public. Cut 2 adds
the write surfaces (Motion Desk / Deliberation Chamber / amendment pipeline)
behind the shared Clerk identity, with their own tables; routers land then.

Run locally:  uvicorn governance.lecg_main:app --port 8013
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from governance.lecg_constitution import load_constitution, constitution_version

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Libra Engine Compass Governance",
    description="The public participation venue of the Libra Engine Compass: "
                "the home of the constitution the public governs.",
    version="0.1.0",
)

# The constitution is public data read cross-origin by the tenets view on the
# Libra Engine site. Read-only GETs, so a scoped allow-list is enough; widen the
# methods only when Cut 2 introduces authenticated writes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://libraengine.com",
        "https://www.libraengine.com",
        "http://localhost:8777",  # libra-engine-site local dev
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
