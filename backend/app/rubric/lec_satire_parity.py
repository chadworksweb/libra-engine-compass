"""Dynamic satire score-parity run (Decoupling Part 1 / satire modifier).

Proves LEC's universal satire MODIFIER scores the same as RC's in-process
recalibrate_song_satire. The satire-carve coverage check (lec_satire_check)
already proved the carve dropped nothing; this is the real bar: run real songs
through the model under BOTH satire system prompts and compare the composed
charges. Same method as the 2026-06-18 cutover dynamic run (lec_dynamic_parity).

  arm A (composed): compose_satire_prompt(gospel, get_lens("rc-lyric"))    -- the
                    composed gospel rubric-def + the fresh le-satire modifier +
                    the verbatim calibration-format. What LEC produces after the
                    repoint.
  arm B (live):     RC's current in-process satire prompt, reconstructed from the
                    LIVE modules: the monolith RUBRIC_DEFINITION + the SAME preamble
                    + the live rc-lyric-satire.md overlay + the monolith
                    CALIBRATION_FORMAT. This mirrors RC's recalibrator.
                    _build_satire_prompt assembly exactly (RC's satire.md and
                    LEC's rc-lyric-satire.md are the same lockstep file).

The format half is byte-equal across arms (rc-lyric precedents_key == lyric), and
the preamble is held constant, so a charge delta isolates the two carves under
test together: the rubric-def (already cutover-validated equivalent) + the new
satire overlay. The bar is equivalent-or-better, not byte/score identity (the
gospel + le-satire are authored fresh). temperature=0; borderline satire songs
are noisy, so run repeated trials and read the distribution, not a single sample
(the lesson of the cutover re-score).

COMPLIANCE: scores through LEC's own calibrator internals (`_read_v3` ->
charge_composition.compose), so run ON the LEC server the Anthropic calls
originate server-side with the server key + metering. Terminal Anthropic for RC
stays banned: do NOT run this from a local terminal against a key. Ship it to
le-projects-01 (docker cp into lec-backend) and run it there.

Fixture: a JSON list of {"title","artist","lyrics"} (lyrics supplied at run time,
never committed -- same posture as the dd.txt backfill lyrics). `--trials N` reads
per arm per song (2 * N * songs Opus calls total), max_tokens 8192 (the satire
read emits five extra reasoning fields).

Run (on the server):
    cd /home/deploy/libra-engine-compass/backend
    python -m app.rubric.lec_satire_parity songs.json --trials 5 --out satire-parity.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from anthropic import AsyncAnthropic

from app.lec_config import settings
from app.rubric.lec_full_prompt import (
    SATIRE_OVERLAY_PREAMBLE, compose_cutover_prompt, compose_satire_prompt,
)
from app.rubric.lec_lens import get_lens, load_gospel
from app.services.agents.lec_calibrator import _SATIRE_USER_SUFFIX, _read_v3
from app.services.agents.lec_compass_agent_rubric import (
    CALIBRATION_FORMAT, build_calibration_prompt,
)
from app.services.agents.lec_rubric_builder import RUBRIC_DEFINITION
from app.services.lec_charge_composition import compose as compose_charge

HERE = Path(__file__).resolve().parent
LIVE_OVERLAY = (
    HERE.parent / "services" / "agents" / "rc-lyric-live" / "rc-lyric-satire.md"
)
SATIRE_MAX_TOKENS = 8192

ALIGN_TOLERANCE = 8  # diagnostic, not a gate: flag songs whose means diverge more


def _live_satire_prompt() -> str:
    """RC's current in-process satire prompt, reconstructed from the live modules:
    the monolith RUBRIC_DEFINITION + the held-constant preamble + the live satire
    overlay + the monolith CALIBRATION_FORMAT. Mirrors RC's recalibrator.
    _build_satire_prompt (rubric-def, preamble, satire tenets, '---', format)."""
    overlay = LIVE_OVERLAY.read_text(encoding="utf-8").strip() + "\n"
    return (
        RUBRIC_DEFINITION
        + SATIRE_OVERLAY_PREAMBLE
        + overlay
        + "\n---\n"
        + CALIBRATION_FORMAT
    )


def _composed_satire_prompt() -> str:
    return compose_satire_prompt(load_gospel(), get_lens("rc-lyric"))


def _literal_prompt() -> str:
    """The LITERAL control: the deployed live STANDARD composed prompt (no satire
    overlay), the read both satire arms are supposed to MOVE. Without this, agreeing
    satire arms could just be reproducing the literal read (a no-op modifier). The
    satire LIFT (satire mean - literal mean) is the proof the modifier does its
    job."""
    return compose_cutover_prompt(load_gospel(), get_lens("rc-lyric"))


def _summarize(trials: list[tuple]) -> dict:
    """Reduce a list of (charge, tier) reads to mean charge, sd, tier counts."""
    scored = [(c, t) for c, t in trials if c is not None]
    charges = [c for c, _ in scored]
    n = len(charges)
    mean = round(sum(charges) / n, 1) if n else None
    if n > 1:
        var = sum((c - mean) ** 2 for c in charges) / (n - 1)
        sd = round(var ** 0.5, 1)
    else:
        sd = 0.0 if n == 1 else None
    tiers: dict = {}
    for _, t in scored:
        tiers[t] = tiers.get(t, 0) + 1
    return {"mean": mean, "sd": sd, "n": n, "failed": len(trials) - n, "tiers": tiers}


async def _score_once(client, model, system_prompt, user_prompt, title, artist):
    read = await _read_v3(
        client, model, system_prompt, user_prompt,
        title=title, artist=artist, target_year=None,
        max_tokens=SATIRE_MAX_TOKENS,
    )
    if read is None:
        return None, None
    composed = compose_charge(read["components"])
    return composed.charge, composed.rubric_color


def _modal(summary: dict):
    return max(summary["tiers"], key=summary["tiers"].get) if summary["tiers"] else None


def _lift(satire: dict, literal: dict):
    """satire mean - literal mean: how far the modifier moved the read. Positive =
    earned up (the expected direction for genuine exposure)."""
    if satire["mean"] is None or literal["mean"] is None:
        return None
    return round(satire["mean"] - literal["mean"], 1)


async def _score_song(client, model, prompt_lit, prompt_a, prompt_b, song, trials):
    title, artist = song["title"], song.get("artist", "")
    _, base_user = build_calibration_prompt(
        title, artist, lyrics=song["lyrics"], artifact_type="lyric"
    )
    sat_user = base_user + _SATIRE_USER_SUFFIX  # the two satire arms only

    # All reads for this song concurrently: trials x 3 arms (literal, composed
    # satire, live satire). The literal arm uses the STANDARD user prompt (no satire
    # suffix); both satire arms share the satire user prompt.
    tasks = []
    for _ in range(trials):
        tasks.append(_score_once(client, model, prompt_lit, base_user, title, artist))
        tasks.append(_score_once(client, model, prompt_a, sat_user, title, artist))
        tasks.append(_score_once(client, model, prompt_b, sat_user, title, artist))
    flat = await asyncio.gather(*tasks)
    lit, a, b = _summarize(flat[0::3]), _summarize(flat[1::3]), _summarize(flat[2::3])

    lit_tier, a_tier, b_tier = _modal(lit), _modal(a), _modal(b)
    delta = (
        round(abs(a["mean"] - b["mean"]), 1)
        if a["mean"] is not None and b["mean"] is not None else None
    )
    return {
        "title": title, "artist": artist,
        "literal": lit, "composed": a, "live": b,
        "literal_modal_tier": lit_tier,
        "composed_modal_tier": a_tier, "live_modal_tier": b_tier,
        "composed_lift": _lift(a, lit), "live_lift": _lift(b, lit),
        "delta": delta,
        "tier_match": a_tier == b_tier,
        "aligned": delta is not None and delta <= ALIGN_TOLERANCE and a_tier == b_tier,
    }


async def run(fixture_path: Path, trials: int) -> dict:
    songs = json.loads(fixture_path.read_text(encoding="utf-8"))
    model = settings.agent_model
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt_lit = _literal_prompt()
    prompt_a = _composed_satire_prompt()
    prompt_b = _live_satire_prompt()

    rows = []
    for i, song in enumerate(songs, 1):
        print(f"  scoring {i}/{len(songs)} ({trials}x x 3 arms): {song['title']}", flush=True)
        rows.append(await _score_song(client, model, prompt_lit, prompt_a, prompt_b, song, trials))

    scored = [r for r in rows if r["delta"] is not None]
    deltas = [r["delta"] for r in scored]
    summary = {
        "model": model, "trials_per_arm": trials, "align_tolerance": ALIGN_TOLERANCE,
        "songs": len(songs), "scored": len(scored),
        "tier_match": sum(1 for r in scored if r["tier_match"]),
        "aligned": sum(1 for r in scored if r["aligned"]),
        "max_delta": max(deltas) if deltas else None,
        "mean_delta": round(sum(deltas) / len(deltas), 2) if deltas else None,
    }
    return {"summary": summary, "rows": rows}


def _cell(summary: dict, tier) -> str:
    return (f"{summary['mean']} {tier} sd{summary['sd']}"
            if summary["mean"] is not None else "FAILED")


def _print_report(result: dict) -> None:
    s = result["summary"]
    print()
    print(f"{'song':<26} {'literal':>16} {'composed-sat':>18} {'live-sat':>18} "
          f"{'liftC/liftL':>12} {'d':>5}  flag")
    for r in result["rows"]:
        lit = _cell(r["literal"], r["literal_modal_tier"])
        cs = _cell(r["composed"], r["composed_modal_tier"])
        gs = _cell(r["live"], r["live_modal_tier"])
        lifts = f"{r['composed_lift']}/{r['live_lift']}"
        d = "" if r["delta"] is None else str(r["delta"])
        flag = "ok" if r["aligned"] else ("TIER" if not r["tier_match"] else "DELTA")
        if r["delta"] is None:
            flag = "READ"
        print(f"{r['title'][:26]:<26} {lit:>16} {cs:>18} {gs:>18} {lifts:>12} {d:>5}  {flag}")
    print()
    print("  liftC = composed-satire mean - literal mean; liftL = live-satire - literal.")
    print("  A modifier that WORKS shows a clear lift in BOTH satire arms vs literal;")
    print("  composed-vs-live agreement (d, flag) shows the carve reproduces RC's satire.")
    print(f"  scored {s['scored']}/{s['songs']}  "
          f"tier-match {s['tier_match']}/{s['scored']}  "
          f"aligned {s['aligned']}/{s['scored']}  "
          f"max delta {s['max_delta']}  mean {s['mean_delta']}  "
          f"({s['trials_per_arm']}x/arm)")


def main() -> int:
    ap = argparse.ArgumentParser(description="LEC dynamic satire score-parity run")
    ap.add_argument("fixture", help="JSON list of {title, artist, lyrics}")
    ap.add_argument("--trials", type=int, default=1, help="reads per arm per song")
    ap.add_argument("--out", help="write the full result JSON here")
    args = ap.parse_args()

    result = asyncio.run(run(Path(args.fixture), args.trials))
    _print_report(result)
    if args.out:
        Path(args.out).write_text(
            json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
