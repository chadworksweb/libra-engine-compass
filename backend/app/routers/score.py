"""The Compass scoring API -- LEC's public surface.

Two endpoints, both behind service-key auth (X-Api-Key, gated on
LEC_AUTH_REQUIRED):
  - GET  /api/rubric  - the single published rubric (consumers cache + fall back).
  - POST /api/score   - one type-aware calibration of an artifact.

`POST /api/score` runs `calibrate_song_async(db=None, skip_cache=True)`: LEC is
stateless w.r.t. any Library. It reads the artifact against the rubric and
returns the charge package. Nothing is read or written. RC's own paths take this
result and run enrichment + persistence on their side.

Adapted from RC's WIP `routers/shared_brain.py` (commit 042d995). The
`use_precedents` flag (plan decision #4) is accepted; precedent injection comes
from LEC's OWN corpus and is a Phase 1 item (the corpus is not synced yet), so
true currently scores statelessly like false.
"""

import hashlib
import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.lec_constants import (
    ARTIFACT_TYPES, COLOR_HEX, COLOR_LABELS, TIER_ORDER,
)
from app.deps import require_api_key
from app.services.agents.lec_calibrator import calibrate_song_async
from app.services.agents.lec_rubric_builder import RUBRIC_DEFINITION, load_tenets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["compass"])


@lru_cache(maxsize=1)
def _composed_definition() -> str:
    """The composed rubric-definition half (gospel + rc-lyric lens) -- the lyric
    path's definition under the cutover. Static at runtime (the gospel + lens
    files do not change while the process runs), so build it once. Mirrors
    RUBRIC_DEFINITION being a module-level constant."""
    from app.rubric.lec_lens import compose, load_gospel, get_lens
    return compose(load_gospel(), get_lens("rc-lyric"))


def published_definition() -> str:
    """The rubric-definition half actually IN FORCE for the lyric path: the
    composed gospel + rc-lyric when LEC_COMPOSE_RUBRIC is on, else the monolith.
    Fail-closed -- any composition error serves the monolith, matching the
    calibrator. This is what /api/rubric publishes and what rubric_version hashes,
    so the published version tracks what actually scores."""
    if settings.compose_rubric:
        try:
            return _composed_definition()
        except Exception:
            logger.exception("composed rubric publish failed; serving the monolith definition")
    return RUBRIC_DEFINITION


def rubric_version() -> str:
    """Stable short version derived from the in-force rubric definition. Changes
    whenever the rubric text changes (including the monolith <-> composed swap),
    so consumers can cache + detect staleness. There is no RUBRIC_VERSION
    constant; off the flag it is rc-lyric-live/rc-lyric-rubric.json, on the flag
    it is the composed gospel + rc-lyric definition."""
    return hashlib.sha256(published_definition().encode("utf-8")).hexdigest()[:12]


def _tenet_count() -> int | None:
    """Best-effort count of numbered tenets across the five tiers. Returns None
    if the tenets JSON shape is not what we expect (never raises)."""
    try:
        data = load_tenets()
        total = 0
        for tier in data.get("tiers", []):
            total += len(tier.get("criteria", []) or tier.get("tenets", []) or [])
        return total or None
    except Exception:
        logger.exception("tenet count failed")
        return None


class ScoreIn(BaseModel):
    type: str = Field(..., description="artifact kind: lyric|poem|prose_essay|script_dialogue|message|email|article")
    text: str = Field(..., description="the work to read")
    intent: str | None = Field(default=None, description="author's stated intent (optional)")
    title: str | None = Field(default=None, description="optional label, frames the read only")
    artist: str | None = Field(default=None, description="optional byline (lyric type)")
    use_precedents: bool = Field(
        default=False,
        description="inject LEC's calibrated-song precedents (RC library reads). "
                    "Phase 1: the corpus is not synced yet, so true scores "
                    "statelessly for now.",
    )


@router.get("/rubric")
async def get_rubric(_: None = Depends(require_api_key)):
    """The current published rubric. Stateless, no model call -- just serializes
    the in-force definition (composed gospel + rc-lyric when the cutover flag is
    on, else the monolith) + version + tier table. Consumers cache this and fall
    back to their last good copy on failure."""
    return {
        "version": rubric_version(),
        "rubric_text": published_definition(),
        "tenet_count": _tenet_count(),
        "tiers": [
            {
                "name": COLOR_LABELS[key].lower(),
                "color_key": key,
                "rc_hex": COLOR_HEX[key],
            }
            for key in TIER_ORDER
        ],
    }


@router.post("/score")
async def post_score(body: ScoreIn, _: None = Depends(require_api_key)):
    """Run one type-aware calibration and return the charge package + the v3
    listener components. Persists nothing (db=None, skip_cache=True)."""
    artifact_type = (body.type or "").strip()
    if artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown type '{artifact_type}'. Allowed: {sorted(ARTIFACT_TYPES)}",
        )

    text = (body.text or "").strip()
    # Minimal sanity gate. A real per-type quality gate (a poem is not 4+ lines
    # of lyrics) is a follow-up; this just blocks empty/trivial input.
    if len(text) < 20:
        raise HTTPException(status_code=422, detail="text is too short to read.")

    if body.use_precedents:
        # Phase 1 item: the precedent corpus (precedent_songs) is not synced yet,
        # so there is nothing to inject. Score statelessly and note the request.
        logger.info("use_precedents=true requested but the corpus is not synced yet; scoring stateless")

    calibration = await calibrate_song_async(
        body.title or "",
        body.artist or "",
        text,
        db=None,            # no session -> no read, no write (stateless)
        skip_cache=True,    # no cache lookup
        artifact_type=artifact_type,
    )

    color = calibration.get("rubric_color")
    if color is None:
        # Failed/null read: never a defaulted tier. Structured unscorable result.
        return {
            "status": "unscorable",
            "type": artifact_type,
            "reason": calibration.get("charge_summary")
            or "The text could not be read against the rubric.",
        }

    intent_source = "stated" if (body.intent and body.intent.strip()) else "none"

    return {
        "status": "scored",
        "type": artifact_type,
        "intent_source": intent_source,
        "tier": COLOR_LABELS[color].lower(),
        "color_key": color,  # consumer maps to its OWN palette; LEC hex != LT/charger hex
        "charge_value": calibration.get("charge_value"),
        "confidence": calibration.get("confidence", 0.0),
        # v3 LISTENER component -- the gut read LT's Mirror grounds on first-person.
        "visceral_charge": calibration.get("visceral_charge"),
        # listener_effects_prose / deadpan_line / topics are ENRICHMENT, not the
        # scoring half. DECIDED 2026-06-15: each client enriches its own listener
        # prose -- LEC stays the pure scoring brain and intentionally returns this
        # null. RC generates it post-/api/score via _ensure_generation; LT's Mirror
        # degrades gracefully on visceral_charge until it ports its own.
        "listener_effects_prose": calibration.get("listener_effects_prose"),
        # charge package extras.
        "charge_summary": calibration.get("charge_summary"),
        "contaminated": calibration.get("contaminated", False),
        "contamination_note": calibration.get("contamination_note"),
        "dogma_referenced": bool(calibration.get("dogma_referenced", False)),
        "dogma_note": calibration.get("dogma_note"),
        "deadpan_line": calibration.get("deadpan_line"),
        "topics": calibration.get("topics"),
        "precedent_refs": calibration.get("precedent_refs"),
        "rubric_version": rubric_version(),
        # Full v3 scoring internals so a stateful client (RC's Lyrical Charger)
        # can reconstruct its calibration_runs row losslessly -- these are the
        # columns log_run writes. `reasoning` is the agent's argument; the client
        # still runs its own verbatim-lyric guard before persisting it.
        "components": {
            "visceral_charge": calibration.get("visceral_charge"),
            "route": calibration.get("route"),
            "harm": calibration.get("harm"),
            "transcendence": calibration.get("transcendence"),
            "governing_axis": calibration.get("governing_axis"),
            "center": calibration.get("center"),
            "vernier": calibration.get("vernier"),
            "gut_divergence": calibration.get("gut_divergence"),
            "guard_trips": calibration.get("guard_trips"),
            "parse_retries": calibration.get("parse_retries"),
            "escalation_flags": calibration.get("escalation_flags"),
            "escalated": calibration.get("escalated"),
            "reasoning": calibration.get("reasoning"),
        },
    }
