"""LEC FastAPI service -- the Libra Engine Compass.

Stands up the scoring brain over HTTP: POST /api/score + GET /api/rubric (in
routers/lec_score.py). On startup it self-initializes its OWN database schema
(create_all over the ORM models -- the 001 baseline), so a fresh deploy needs no
manual migration step. LEC connects only to its own libra_engine_compass DB; it
never reads Rising Compass.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.lec_database import Base, engine
from app import lec_models  # noqa: F401  (registers the models on Base before create_all)
from app.routers import lec_admin, lec_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fresh install / new column safety net: the brand-new LEC DB is created from
    # the ORM models. New schema after the 001 baseline gets numbered migrations.
    Base.metadata.create_all(bind=engine)
    logger.info("LEC schema ensured against %s", engine.url)
    yield


app = FastAPI(
    title="Libra Engine Compass",
    description="The standalone calibration brain of the Libra Engine.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(lec_score.router)
app.include_router(lec_admin.router)


@app.get("/health")
async def health():
    """Liveness probe for the co-located RC client + the nginx upstream check."""
    return {
        "status": "ok",
        "service": "lec",
        "rubric_version": lec_score.rubric_version(),
        "constitution": lec_score.constitution_pin(),
    }
