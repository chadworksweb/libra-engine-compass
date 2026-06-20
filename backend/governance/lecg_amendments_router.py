"""Amendment log + governed-constitution public API (lecg-).

Surface (all public, read-only):
  GET /api/amendments                    the merged amendment log (config + live motions)
  GET /api/governed-constitution         the live governed law (genesis + ratified amendments)
  GET /api/governed-constitution/version the governed law version (pin/cache probe)

Note: the FROZEN canonical constitution + its genesis version live on the lec
instrument's public surface (governance/lecg_public.py: /api/constitution). THIS
surface is the venue's LIVE governed view -- it differs from the frozen one only
once an amendment has been ratified here but not yet adopted into an edition.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from governance.lecg_database import get_db
from governance import lecg_amendments as amendments_svc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["amendments"])


@router.get("/api/amendments")
def get_amendment_log(db: Session = Depends(get_db)):
    return amendments_svc.load_amendment_log(db)


@router.get("/api/governed-constitution")
def get_governed_constitution(db: Session = Depends(get_db)):
    return amendments_svc.governed_constitution(db)


@router.get("/api/governed-constitution/version")
def get_governed_version(db: Session = Depends(get_db)):
    return {"version": amendments_svc.governed_version(db)}
