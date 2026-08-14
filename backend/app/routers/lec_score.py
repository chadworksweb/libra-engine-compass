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
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.lec_config import settings
from app.lec_constants import (
    ARTIFACT_TYPES, COLOR_HEX, COLOR_LABELS, TIER_ORDER,
)
from app.lec_deps import require_api_key
from app.services.agents.lec_calibrator import calibrate_song_async
from app.services.agents.lec_compass_agent_rubric import CALIBRATION_FORMAT
# RUBRIC_DEFINITION / load_tenets (the retired monolith) are no longer imported:
# the published rubric is composed (published_definition) and the tenet count comes
# from the gospel (_tenet_count). See lec_rubric_builder for the cutover note.

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["compass"])


# The lens /api/rubric publishes when the caller names none. RC's terminal
# read-gate pins the version of THIS composition, so the default must never
# move as a side effect of another lens being published.
PUBLISHED_LENS = "rc-lyric"


@lru_cache(maxsize=4)
def _composed_definition(lens_key: str = PUBLISHED_LENS) -> str:
    """The composed rubric-definition half (gospel + a lens) -- the live
    instrument since the cutover. Static at runtime (the gospel + lens files do not
    change while the process runs), so build it once per lens and cache."""
    from app.rubric.lec_lens import compose, load_gospel, get_lens
    return compose(load_gospel(), get_lens(lens_key, fallback=lens_key))


def published_definition(lens_key: str = PUBLISHED_LENS) -> str:
    """The rubric-definition half IN FORCE for a lens: the composed gospel + that
    lens. Defaults to rc-lyric, the song instrument. The monolith is retired
    (cutover 2026-06-27), so this is UNCONDITIONAL and FAIL-LOUD -- a composition
    error propagates (there is no monolith fallback), and an unknown lens raises
    rather than falling back to the song lens. This is what /api/rubric publishes
    and what rubric_version hashes, so the published version tracks what actually
    scores."""
    return _composed_definition(lens_key)


def _calibration_format(lens_key: str = PUBLISHED_LENS) -> str:
    """The calibration METHOD half for a lens. The default lens serves the live
    CALIBRATION_FORMAT constant verbatim, so the published song format stays
    byte-identical to what the calibrator sends. Any other lens composes its own,
    which is how the album lens's method half (a different procedure, not just a
    different vocabulary -- see Lens.method_key) reaches an operator at all."""
    if lens_key == PUBLISHED_LENS:
        return CALIBRATION_FORMAT
    from app.rubric.lec_full_prompt import compose_calibration_format
    from app.rubric.lec_lens import get_lens
    return compose_calibration_format(get_lens(lens_key, fallback=lens_key))


def rubric_version(lens_key: str = PUBLISHED_LENS) -> str:
    """Stable short version derived from a lens's in-force rubric definition.
    Changes whenever that rubric text changes, so consumers can cache + detect
    staleness. Each lens versions independently: publishing the album instrument
    cannot move the song version RC's read-gate pins."""
    return hashlib.sha256(published_definition(lens_key).encode("utf-8")).hexdigest()[:12]


# The constitution version this instrument is BUILT + verified against. The
# instrument is a CONSUMER of the governance-owned le- law (Decoupling Part 2):
# it PINS a constitution version, composes against it, and adopting a newer
# ratified version is a DELIBERATE act (bump this + re-verify scoring), never an
# automatic pickup. Decision 1/4 -- shared-repo version pin, no inter-service
# HTTP. Override via env for ops; the code default tracks what shipped.
PINNED_CONSTITUTION_VERSION = os.getenv("LEC_PINNED_CONSTITUTION_VERSION", "46528e8caeed")


def _governed_constitution_version() -> str | None:
    """The CURRENT constitution version governance publishes. Fail-soft: returns
    None if the governance package is unavailable (e.g. not yet deployed beside
    the instrument), never raising into a response or onto the scoring path."""
    try:
        from governance.lecg_constitution import constitution_version
        return constitution_version()
    except Exception:
        logger.exception("governed constitution version unavailable")
        return None


def constitution_pin() -> dict:
    """What constitution version the instrument pins, what governance currently
    publishes, and whether they agree. in_sync False means the law moved (a
    ratified amendment) and the instrument has not yet adopted it -- the signal to
    deliberately bump PINNED_CONSTITUTION_VERSION and re-verify, not an auto-adopt."""
    current = _governed_constitution_version()
    return {
        "pinned": PINNED_CONSTITUTION_VERSION,
        "current": current,
        "in_sync": current is not None and current == PINNED_CONSTITUTION_VERSION,
    }


def _tenet_count() -> int | None:
    """Best-effort count of numbered tenets across the five tiers. Returns None
    if the tenets JSON shape is not what we expect (never raises)."""
    try:
        from app.rubric.lec_lens import load_gospel
        data = load_gospel()
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
    satire: bool = Field(
        default=False,
        description="re-read through the universal satire MODIFIER (apply the "
                    "standard rubric first, then re-read for expose-vs-endorse). "
                    "Composed-only + lyric-only today; rejected (422) for any type "
                    "that cannot offer it.",
    )
    inhabited: bool = Field(
        default=False,
        description="re-read through the inhabited-voice lens: an earnest narrator "
                    "inhabiting a degraded/suffering state to WITNESS it, gated by "
                    "an in-lyric turn. Composed-only + lyric-only; rejected (422) "
                    "otherwise. Mutually exclusive with satire.",
    )


@router.get("/rubric")
async def get_rubric(lens: str | None = None, _: None = Depends(require_api_key)):
    """The current published rubric. Stateless, no model call -- just serializes
    the in-force definition (composed gospel + the lens) + version + tier table.
    Consumers cache this and fall back to their last good copy on failure.

    `lens` names which instrument to publish, defaulting to rc-lyric. The album
    instrument (`?lens=rc-album`) is published on the same endpoint so an operator
    read-gate file can be a real pull instead of a local compose -- which is what
    LEC-ALBUM-RUBRIC-LIVE.md was, its header saying so in as many words. Each lens
    hashes independently, so the default response is unchanged by any of this."""
    lens_key = (lens or PUBLISHED_LENS).strip()
    try:
        definition = published_definition(lens_key)
    except (KeyError, FileNotFoundError):
        raise HTTPException(
            status_code=422,
            detail=f"Unknown lens {lens_key!r}.",
        )
    return {
        "version": rubric_version(lens_key),
        "lens": lens_key,
        "constitution": constitution_pin(),
        "rubric_text": definition,
        # The calibration METHOD half (anonymous read -> visceral -> route tree ->
        # two-axis -> precedent placement + table -> vernier -> contamination /
        # summary checks -> verdict -> reconciliation -> JSON schema -> charge scale
        # -> the charge_summary Voice rules). The live calibrator sends
        # RUBRIC_DEFINITION + this; terminal/operator calibration MUST pull and obey
        # it from here (the access point), never from an SOP. Carried as its own
        # field so it does NOT enter rubric_version's hash (prose-only, no score
        # impact) -- consumers that cache on version still pick up the latest format
        # on their next fetch.
        "calibration_format": _calibration_format(lens_key),
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

    if body.satire:
        # The satire modifier is composed against a lens, and only the lyric path
        # runs the composed scorer today, so satire is lyric-only. The rc-lyric
        # lens must offer satire. Reject (not silently ignore) any other request.
        # Lazy import keeps app.rubric off the non-satire request path.
        from app.rubric.lec_lens import get_lens
        if artifact_type != "lyric" or not get_lens("rc-lyric").satire_available:
            raise HTTPException(
                status_code=422,
                detail="satire re-read is available only for type 'lyric'.",
            )

    if body.inhabited:
        # The inhabited-voice lens is lyric-native + composed-only, like satire,
        # and mutually exclusive with it (one re-read at a time).
        if body.satire:
            raise HTTPException(
                status_code=422,
                detail="satire and inhabited are mutually exclusive; pick one re-read.",
            )
        if artifact_type != "lyric":
            raise HTTPException(
                status_code=422,
                detail="inhabited-voice re-read is available only for type 'lyric'.",
            )

    calibration = await calibrate_song_async(
        body.title or "",
        body.artist or "",
        text,
        db=None,            # no session -> no read, no write (stateless)
        skip_cache=True,    # no cache lookup
        artifact_type=artifact_type,
        satire=body.satire,
        inhabited=body.inhabited,
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
        "satire": body.satire,  # echo: this read applied the satire modifier
        "inhabited": body.inhabited,  # echo: this read applied the inhabited-voice lens
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
