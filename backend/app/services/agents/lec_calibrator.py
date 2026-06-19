"""The Compass calibration engine -- LEC's scoring core.

Lifted from Rising Compass and reduced to the SCORING half: the Opus call,
component validation, the retry/guard logic, and the charge composition. The
cache lookup, the enrichment chain (effects/ether/societal prose), and all
persistence stayed in RC (the boundary is the old db-gated branch). LEC reads an
artifact against the rubric and returns the charge package; RC enriches +
persists on its side.
"""

import asyncio
import json
import logging
import re
from typing import Callable

from anthropic import AsyncAnthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.services.lec_charge_composition import (
    CompositionError,
    compose,
    evaluate_escalation,
    validate_components,
)
from app.services.claude_meter import tracked_create_async
from app.services.agents.lec_compass_agent_rubric import build_calibration_prompt
from app.services.agents.summary_guard import (
    CORRECTIVE_NUDGE as _SUMMARY_NUDGE,
    summary_from_json_text,
    summary_has_absence_framing,
)

logger = logging.getLogger(__name__)

AGENT_MODEL = settings.agent_model

# The structured format (CALIBRATION_FORMAT) requires an explicit
# "Contamination: none" / "Contamination: <artifact>" line before the VERDICT.
# This is a binary determination made independently of charge_value; folding an
# artifact into the charge and skipping the flag is the failure this guards.
_CONTAM_LINE_RE = re.compile(r"(?im)^\s*Contamination:\s*\S")


async def _read_v3(
    client: AsyncAnthropic,
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    title: str,
    artist: str,
    target_year: int | None,
) -> dict | None:
    """Run ONE calibration read at `model`: call, split reasoning from JSON,
    run the output guards, parse, and validate into v3 components -- with one
    corrective retry shared across every failure kind. Failure kinds:

      1. CONTAMINATION guard -- the format requires an explicit
         "Contamination:" line in the reasoning (guard_trips).
      2. charge_summary absence/verdict framing (guard_trips; see
         summary_guard.py).
      3. Unparseable JSON or components failing validation (parse_retries).

    Guards keep the v2 proceed-with-warning posture: a read whose components
    validate but whose guards still trip after the retry is returned with
    guard_trip_survived=True (an escalation trigger). A read whose JSON never
    validates returns None -- the caller turns that into the explicit
    needs-human-review failure, never a defaulted verdict."""
    messages = [{"role": "user", "content": user_prompt}]
    guard_trips = 0
    parse_retries = 0
    best: dict | None = None
    attempts = 2
    for attempt in range(1, attempts + 1):
        response = await tracked_create_async(
            client,
            call_site="calibrator",
            context={"title": title, "artist": artist, "target_year": target_year},
            model=model,
            max_tokens=3500,
            temperature=0,
            system=system_prompt,
            messages=messages,
        )
        raw = response.content[0].text.strip()

        # Split reasoning from JSON -- reasoning comes first, JSON starts at
        # the first {. Strip a trailing ``` fence if the JSON got wrapped.
        reasoning = ""
        json_str = raw
        brace_idx = raw.find("{")
        if brace_idx > 0:
            reasoning = raw[:brace_idx].strip()
            json_str = raw[brace_idx:]
        if json_str.rstrip().endswith("```"):
            json_str = json_str.rstrip()[:-3]
        json_str = json_str.strip()

        problems: list[str] = []
        corrective_parts: list[str] = []

        contam_ok = bool(_CONTAM_LINE_RE.search(reasoning))
        summary_ok = not summary_has_absence_framing(
            summary_from_json_text(json_str)
        )
        guards_ok = contam_ok and summary_ok
        if not guards_ok:
            guard_trips += 1
        if not contam_ok:
            problems.append("omitted the mandatory 'Contamination:' line")
            corrective_parts.append(
                "Re-run the full structured format with an explicit "
                "'Contamination: none' or 'Contamination: <artifact>' line "
                "before the VERDICT. "
            )
        if not summary_ok:
            problems.append("used absence/verdict framing in charge_summary")
            corrective_parts.append(_SUMMARY_NUDGE)

        parsed = None
        components = None
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            parse_retries += 1
            problems.append("output did not end in a parseable JSON object")
            corrective_parts.append(
                "Re-emit the full structured reasoning followed by ONE valid "
                "JSON object in the exact required shape. "
            )
        if parsed is not None:
            try:
                components = validate_components(parsed)
            except CompositionError as exc:
                parse_retries += 1
                problems.append(f"JSON failed component validation ({exc})")
                corrective_parts.append(
                    "Fix the JSON fields named above to the required types and "
                    "ranges from the JSON contract. "
                )

        read = None
        if components is not None:
            read = {
                "raw": raw,
                "reasoning": reasoning,
                "parsed": parsed,
                "components": components,
                "confidence": float(parsed.get("confidence") or 0.0),
                "guard_trips": guard_trips,
                "parse_retries": parse_retries,
                "guard_trip_survived": not guards_ok,
                "model": model,
            }
        if read is not None:
            # A usable read -- components validated and the charge composes.
            # Ship it immediately, whether the soft guards (contamination line /
            # charge_summary framing) were clean or drifted. A drifted guard is
            # already recorded on the read (guard_trip_survived) and surfaces as
            # an escalation signal downstream, exactly as it did when the old
            # second pass also tripped. We deliberately do NOT spend a second
            # full-rubric Opus call just to re-coax formatting: that turned every
            # submission into TWO calibrator calls (the dominant latency in the
            # public charger). The corrective retry below is reserved for the
            # genuine no-usable-read case -- unparseable JSON or failed component
            # validation -- where a second attempt is the only path to a result.
            return read

        logger.warning(
            "calibrator output problems for '%s' by %s at %s (attempt %d/%d): %s",
            title, artist, model, attempt, attempts, "; ".join(problems),
        )
        if attempt < attempts:
            corrective = (
                "Your response had these problems: " + "; ".join(problems)
                + ". " + "".join(corrective_parts)
            )
            messages = [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": raw},
                {"role": "user", "content": corrective},
            ]
    return best


async def calibrate_song_async(
    title: str,
    artist: str,
    lyrics: str | None = None,
    db: Session | None = None,
    target_year: int | None = None,
    skip_cache: bool = False,
    progress_cb: Callable[[str], None] | None = None,
    artifact_type: str = "lyric",
) -> dict:
    """The scoring path -- LEC's whole job. Read an artifact against the rubric
    and return the charge package (tier, charge_value, contamination, the v3
    listener components). LEC is the SCORING HALF ONLY: the cache lookup and the
    enrichment chain (effects prose, ether tagging, societal prose) stayed in RC,
    which calls /api/score for the read and then enriches + persists the result.

    `db` and `skip_cache` are accepted but unused here -- kept so the signature
    stays diffable against RC's calibrator (proving no scoring logic changed) and
    so RC's call sites and the score router pass through unchanged. LEC never
    opens a session.

    `artifact_type` selects how the user prompt frames the read (lyric default,
    byte-for-byte unchanged; poem/essay/script/message/email/article reuse the
    same rubric + precedent discipline).
    """
    # No text, no read. A calibration cannot exist without the page, so return
    # the explicit null result without burning an API call (v3 short-circuit).
    if not lyrics:
        logger.info("No text for '%s' by %s; returning null calibration "
                    "without an API call", title, artist)
        return _null_result(title, artist)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Few-shot examples disabled. The tenet definitions + the curated precedent
    # table carry the anchoring without a corpus draw (the Song-backed few-shot
    # builder was a stateless-scoring coupling and was removed entirely).
    examples = ""

    system_prompt, user_prompt = build_calibration_prompt(
        title, artist, lyrics=lyrics, examples=examples, artifact_type=artifact_type
    )

    # Decoupling cutover (Part 1), dark by default. When LEC_COMPOSE_RUBRIC is on,
    # swap the lyric rubric-definition for the composed gospel + rc-lyric lens (the
    # score-parity-validated path: compose_cutover_prompt == arm A of the
    # 2026-06-18 dynamic run). Fail-closed: any composition error keeps the
    # monolith prompt built above, so a bad lens can never blank a calibration.
    # Lazy import so the flag-off path never touches app.rubric.
    if settings.compose_rubric and artifact_type == "lyric":
        try:
            from app.rubric.lec_full_prompt import compose_cutover_prompt
            from app.rubric.lec_lens import get_lens, load_gospel
            system_prompt = compose_cutover_prompt(load_gospel(), get_lens("rc-lyric"))
        except Exception:
            logger.exception(
                "composed rubric failed for '%s' by %s; using the monolith rubric",
                title, artist,
            )

    # First pass at the default model. The model emits components only; the
    # server composes the charge and derives the tier (charge_composition).
    if progress_cb:
        progress_cb("calibrating")
    read = await _read_v3(
        client, AGENT_MODEL, system_prompt, user_prompt,
        title=title, artist=artist, target_year=target_year,
    )
    if read is None:
        # Output never validated, even after the corrective retry. Explicit
        # needs-human-review failure -- never a defaulted verdict.
        logger.error("Calibration read failed validation for %s by %s", title, artist)
        return _fallback_result(title, artist, "")

    composed = compose(read["components"])
    triggers = evaluate_escalation(
        composed, read["components"],
        guard_trip_survived=read["guard_trip_survived"],
        # Server feeders read original-language lyrics; translated runs exist
        # only on the terminal path, which stamps its own flag.
        translated=False,
        confidence=read["confidence"],
        confidence_floor=settings.escalation_confidence_floor,
    )

    # Escalation gate (spec 2.4). Triggers are ALWAYS recorded on the run;
    # the re-pass only fires when config enables it AND the escalation model
    # actually differs (with Opus-everywhere defaults the gate logs only).
    escalated = False
    first_pass = None
    escalation_model = settings.escalation_model or AGENT_MODEL
    if triggers and settings.escalation_repass_enabled and escalation_model != AGENT_MODEL:
        logger.warning("Escalation re-pass for '%s' by %s (triggers: %s)",
                       title, artist, ", ".join(triggers))
        repass = await _read_v3(
            client, escalation_model, system_prompt, user_prompt,
            title=title, artist=artist, target_year=target_year,
        )
        if repass is not None:
            first_pass = {
                "model": AGENT_MODEL,
                "charge": composed.charge,
                "tier": composed.rubric_color,
                "triggers": triggers,
            }
            read = repass
            composed = compose(read["components"])
            triggers = evaluate_escalation(
                composed, read["components"],
                guard_trip_survived=read["guard_trip_survived"],
                translated=False,
                confidence=read["confidence"],
                confidence_floor=settings.escalation_confidence_floor,
            )
            escalated = True
    elif triggers:
        logger.warning("Escalation triggers recorded for '%s' by %s (no re-pass): %s",
                       title, artist, ", ".join(triggers))

    if read["reasoning"]:
        logger.info("Agent reasoning for '%s' by %s:\n%s", title, artist, read["reasoning"])

    c = read["components"]
    parsed = read["parsed"]

    # Contamination is cross-derived from the axis data (a discrete harm
    # artifact on a read the harm axis does not govern). The model's own flag
    # is a cross-check: a mismatch is recorded, the derivation wins. The note
    # stays the model's words, kept only when the flag holds.
    contaminated = composed.contaminated
    signals = list(composed.signals)
    if bool(parsed.get("contaminated", False)) != contaminated:
        signals.append("contamination_flag_mismatch")
        logger.warning(
            "contamination flag mismatch for '%s' by %s: model=%s derived=%s",
            title, artist, bool(parsed.get("contaminated", False)), contaminated,
        )

    escalation_flags = None
    if triggers or signals or first_pass:
        escalation_flags = {"triggers": triggers, "signals": signals}
        if first_pass:
            escalation_flags["first_pass"] = first_pass

    calibration = {
        "rubric_color": composed.rubric_color,
        "charge_value": composed.charge,
        "contaminated": contaminated,
        "contamination_note": parsed.get("contamination_note") if contaminated else None,
        "dogma_referenced": bool(parsed.get("dogma_referenced", False)),
        "dogma_note": parsed.get("dogma_note"),
        "charge_summary": parsed.get("charge_summary", ""),
        "confidence": read["confidence"],
        # The agent's structured argument (the prose before the JSON). Carried
        # through to the calibration run, where log_run's _guard_reasoning
        # scrubs any verbatim lyric runs before it is stored.
        "reasoning": read["reasoning"] or None,
        # v3 components + incoherence signals -> calibration_runs columns
        # (log_run). Internal-only; song_sync's column whitelist keeps them
        # off the songs row.
        "visceral_charge": c.visceral_charge,
        "route": c.route,
        "harm": {"value": c.harm_value, "pervasive": c.harm_pervasive},
        "transcendence": {"value": c.transcendence_value},
        "governing_axis": composed.governing_axis,
        "center": c.center,
        "vernier": c.vernier,
        "precedent_refs": c.precedent_refs,
        "gut_divergence": composed.gut_divergence,
        "guard_trips": read["guard_trips"],
        "parse_retries": read["parse_retries"],
        "escalation_flags": escalation_flags,
        "escalated": escalated,
    }

    # If the summary STILL carries absence/verdict framing after the retry, ship
    # it (a false-positive must never blank a valid summary) but log loudly so the
    # drift is visible. Mirrors the proceed-with-warning posture of the guards.
    if lyrics and summary_has_absence_framing(calibration["charge_summary"]):
        logger.warning(
            "charge_summary retained absence/verdict framing after retry for '%s' by %s: %r",
            title, artist, calibration["charge_summary"],
        )

    # Verbatim-lyric backstop on the calibrator's quote-prone short fields, both of
    # which render on the public song page. The rubric now asks for paraphrase; if a
    # verbatim run slips through anyway, clear the field so no copyrighted lyric text
    # ever ships. contaminated / dogma_referenced flags stay set, so the indicators
    # still show and the page falls back to generic copy.
    if lyrics:
        from app.services.lyric_quote_guard import has_verbatim_overlap
        for _field in ("contamination_note", "dogma_note"):
            if calibration.get(_field) and has_verbatim_overlap(calibration[_field], lyrics):
                logger.warning("%s carried verbatim lyric quotes for %s / %s; cleared",
                               _field, title, artist)
                calibration[_field] = None

    # Enrichment (effects prose, ether tagging, societal prose) is RC's, not
    # LEC's: LEC returns the scored charge package and stops here. RC takes this
    # result from /api/score and runs the generation chain + persistence on its
    # own side. visceral_charge + the v3 components are already on the dict.
    return calibration


def calibrate_song(
    title: str,
    artist: str,
    lyrics: str | None = None,
    db: Session | None = None,
    target_year: int | None = None,
    skip_cache: bool = False,
) -> dict:
    """Sync wrapper around calibrate_song_async. For scripts and legacy sync
    callers (e.g. compass_agent.run_compass_agent)."""
    return asyncio.run(calibrate_song_async(
        title, artist, lyrics=lyrics, db=db,
        target_year=target_year, skip_cache=skip_cache,
    ))


def _fallback_result(title: str, artist: str, raw_response: str) -> dict:
    """Return an explicit failure when Claude's response can't be parsed or
    validated. rubric_color=None signals the song needs human intervention
    rather than silently defaulting to green/0; calibration_failed stamps the
    run so the failure stays visible in the ledger.
    """
    return {
        "rubric_color": None,
        "charge_value": None,
        "contaminated": False,
        "contamination_note": None,
        "dogma_referenced": False,
        "dogma_note": None,
        "charge_summary": f"Calibration failed: manual review needed for {title} by {artist}",
        "confidence": 0.0,
        "calibration_failed": True,
    }


def _null_result(title: str, artist: str) -> dict:
    """The null calibration for a song with no lyrics: nothing was read, so
    nothing is scored. Distinct from _fallback_result (a read that failed)."""
    return {
        "rubric_color": None,
        "charge_value": None,
        "contaminated": False,
        "contamination_note": None,
        "dogma_referenced": False,
        "dogma_note": None,
        "charge_summary": f"No lyrics available for {title} by {artist}; awaiting lyrics to calibrate",
        "confidence": 0.0,
    }
