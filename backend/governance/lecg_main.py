"""LECG FastAPI service -- Libra Engine Compass Governance (Cut 2).

The public-participation VENUE of the Libra Engine Compass: the second app in the
libra-engine-compass repo (Decoupling Part 2, Decision 4), separate from the lec-
instrument. Its job is the amendment MACHINERY -- the Motion Desk, the
Deliberation Chamber, and the amendment pipeline -- behind the shared Clerk
identity, with its own governance DB.

This is a STUB. It is not deployed in Cut 1. The TENETS are the LEC tenets: they
live on LEC and are served by the lec instrument (lec.libraengine.com/tenets/ +
/api/constitution, via governance/lecg_public.py). This venue is built out in
Cut 2 (gated on Clerk Pro for the shared-identity wiring).

Run locally (Cut 2):  uvicorn governance.lecg_main:app --port 8014
"""

import logging

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Libra Engine Compass Governance",
    description="The public participation venue of the Libra Engine Compass "
                "(Cut 2: the Motion Desk, Deliberation Chamber, and amendment pipeline).",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Liveness probe. Cut 2 adds the venue's write surfaces."""
    return {"status": "ok", "service": "lecg", "cut": "stub (Cut 2 pending)"}
