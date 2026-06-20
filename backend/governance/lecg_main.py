"""LECG FastAPI service -- Libra Engine Compass Governance (Cut 2).

The public-participation VENUE of the Libra Engine Compass: the SECOND app in the
libra-engine-compass repo (Decoupling Part 2, Decision 4), separate from the lec-
instrument (distinct app, distinct DB, distinct deploy). Its job is the amendment
MACHINERY -- the Motion Desk, the Deliberation Chamber, and the amendment pipeline
(with the ratification write-back) -- behind the SHARED Clerk identity, on its own
governance DB.

It self-initializes its own schema on startup (create_all over the lecg_models,
the 001 baseline). It connects only to its own governance DB; it never reads RC
or the instrument's DB. The constitution it serves (genesis) is read from the
le-baseline files baked into the image, shared with the instrument (the
shared-repo law, Decision 4).

  Public read surfaces : the amendment log, the motion ledger, the governed
                         constitution, the (frozen) constitution + tenets page.
  Write surfaces       : file a motion, post in the chamber -- Tier-2 gated on
                         the shared Clerk spine (GATED ON CLERK PRO; inert until
                         wired, unless LECG_DEV_AUTH locally).
  Admin                : the lifecycle console + the ratification write-back.

Run locally:  LECG_DEV_AUTH=true uvicorn governance.lecg_main:app --port 8014
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from governance.lecg_config import settings, clerk_enabled, dev_auth_active
from governance.lecg_constitution import constitution_version
from governance.lecg_database import Base, engine
from governance import lecg_models  # noqa: F401  (registers the models on Base before create_all)
from governance.lecg_admin_router import router as admin_router
from governance.lecg_amendments_router import router as amendments_router
from governance.lecg_chamber_router import router as chamber_router
from governance.lecg_motions_router import router as motions_router
from governance.lecg_public import router as constitution_router, STATIC_TENETS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = STATIC_TENETS.parent  # governance/static/ (tenets/, motion-desk/, amendments/)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The venue owns a brand-new DB; create_all from the ORM models is the 001
    # baseline. New schema after this gets numbered lecg migrations.
    Base.metadata.create_all(bind=engine)
    logger.info("LECG governance schema ensured against %s", engine.url)
    logger.info(
        "LECG up: clerk_enabled=%s dev_auth=%s constitution_version=%s",
        clerk_enabled(), dev_auth_active(), constitution_version(),
    )
    yield


app = FastAPI(
    title="Libra Engine Compass Governance",
    description="The public participation venue of the Libra Engine Compass "
                "(the Motion Desk, Deliberation Chamber, and amendment pipeline).",
    version="1.0.0",
    lifespan=lifespan,
)

# The public read surfaces may be fetched cross-origin by the LE site / RC.
_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The amendment machinery + the public read surfaces.
app.include_router(motions_router)
app.include_router(chamber_router)
app.include_router(amendments_router)
app.include_router(admin_router)
# The frozen canonical constitution + the live tenets-data.js (governance-owned;
# also hosted by the instrument). The venue serves it too so /tenets/ resolves here.
app.include_router(constitution_router)


@app.get("/health")
async def health():
    """Liveness probe for the nginx upstream check + the deploy smoke test."""
    return {
        "status": "ok",
        "service": "lecg",
        "constitution_version": constitution_version(),
        "clerk_enabled": clerk_enabled(),
        "dev_auth": dev_auth_active(),
    }


@app.get("/", include_in_schema=False)
async def root():
    """The venue front door -> the Motion Desk (the participation surface)."""
    return RedirectResponse(url="/motion-desk/")


# The public venue pages (Motion Desk, Deliberation Chamber, amendments, tenets).
# tenets-data.js is served live by constitution_router (included first, so it
# wins); the static dir is mounted last so explicit routes take precedence.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
