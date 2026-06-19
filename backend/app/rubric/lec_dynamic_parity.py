"""Dynamic score-parity run (Decoupling Part 1, next-in-order step 2).

Proves the fresh-authored `gospel + rc-lyric lens` SCORES the same as the live
calibrator. Static parity already proved the carve dropped nothing; this is the
real bar: run real songs through the model under BOTH system prompts and compare
the composed charges.

  arm A (composed): compose_full_prompt(gospel, get_lens("rc-lyric"))  -- the
                    Decoupling's fresh rubric-definition half + the calibration-
                    format method (precedent table via lens.precedents_key).
  arm B (golden):   lec-golden-2026-06-18/system_prompt_lyric.txt        -- the
                    current live rendered prompt (post-R15 re-snapshot).

The two prompts differ ONLY in the rubric-definition half (fresh register-A
authoring vs the live rendered text); the calibration-format half is byte-equal.
So a charge delta isolates the effect of the fresh authoring -- exactly what the
cutover needs to clear. temperature=0 (the calibrator default) keeps the read
near-deterministic, so deltas reflect the prompt, not sampling.

COMPLIANCE: this scores through LEC's own calibrator internals (`_read_v3` ->
`charge_composition.compose`), so when run ON the LEC server the Anthropic calls
originate server-side with the server key + metering. Terminal Anthropic for RC
stays banned: do NOT run this from a local terminal against a local key. Ship it
to le-projects-01 and run it there.

Fixture: a JSON list of {"title","artist","lyrics"} (lyrics supplied at run time,
never committed -- same posture as the dd.txt backfill lyrics). One Opus call per
arm per song (2N calls total).

Run (on the server):
    cd /home/deploy/libra-engine-compass/backend
    python -m app.rubric.lec_dynamic_parity songs.json --out parity-result.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from anthropic import AsyncAnthropic

from app.config import settings
from app.rubric.lec_full_prompt import compose_full_prompt
from app.rubric.lec_lens import get_lens, load_gospel
from app.services.agents.lec_calibrator import _read_v3
from app.services.agents.lec_compass_agent_rubric import build_calibration_prompt
from app.services.lec_charge_composition import compose as compose_charge

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "lec-golden-2026-06-18"

# Aligned if the composed charge lands within this many points of the golden AND
# in the same tier. A diagnostic threshold, not a hard gate: surface every song
# that exceeds it for a human read before cutover.
ALIGN_TOLERANCE = 8


def _golden_system_prompt() -> str:
    return (GOLDEN / "system_prompt_lyric.txt").read_text(encoding="utf-8")


def _composed_system_prompt() -> str:
    return compose_full_prompt(load_gospel(), get_lens("rc-lyric"))


async def _score(client, model, system_prompt, user_prompt, title, artist):
    """One read under one system prompt -> (charge, tier) or (None, None)."""
    read = await _read_v3(
        client, model, system_prompt, user_prompt,
        title=title, artist=artist, target_year=None,
    )
    if read is None:
        return None, None
    composed = compose_charge(read["components"])
    return composed.charge, composed.rubric_color


async def _score_song(client, model, prompt_a, prompt_b, song):
    title, artist = song["title"], song.get("artist", "")
    _, user_prompt = build_calibration_prompt(
        title, artist, lyrics=song["lyrics"], artifact_type="lyric"
    )
    # Both arms concurrently; same user prompt, different system prompt.
    (a_charge, a_tier), (b_charge, b_tier) = await asyncio.gather(
        _score(client, model, prompt_a, user_prompt, title, artist),
        _score(client, model, prompt_b, user_prompt, title, artist),
    )
    delta = (
        abs(a_charge - b_charge)
        if a_charge is not None and b_charge is not None
        else None
    )
    aligned = (
        delta is not None and delta <= ALIGN_TOLERANCE and a_tier == b_tier
    )
    return {
        "title": title,
        "artist": artist,
        "composed": {"charge": a_charge, "tier": a_tier},
        "golden": {"charge": b_charge, "tier": b_tier},
        "delta": delta,
        "tier_match": a_tier == b_tier,
        "aligned": aligned,
    }


async def run(fixture_path: Path) -> dict:
    songs = json.loads(fixture_path.read_text(encoding="utf-8"))
    model = settings.agent_model
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt_a = _composed_system_prompt()
    prompt_b = _golden_system_prompt()

    rows = []
    for i, song in enumerate(songs, 1):
        print(f"  scoring {i}/{len(songs)}: {song['title']}", flush=True)
        rows.append(await _score_song(client, model, prompt_a, prompt_b, song))

    scored = [r for r in rows if r["delta"] is not None]
    deltas = [r["delta"] for r in scored]
    summary = {
        "model": model,
        "golden": GOLDEN.name,
        "align_tolerance": ALIGN_TOLERANCE,
        "songs": len(songs),
        "scored": len(scored),
        "failed_reads": len(rows) - len(scored),
        "tier_match": sum(1 for r in scored if r["tier_match"]),
        "aligned": sum(1 for r in scored if r["aligned"]),
        "max_delta": max(deltas) if deltas else None,
        "mean_delta": round(sum(deltas) / len(deltas), 2) if deltas else None,
    }
    return {"summary": summary, "rows": rows}


def _print_report(result: dict) -> None:
    s = result["summary"]
    print()
    print(f"{'song':<34} {'composed':>14} {'golden':>14} {'delta':>6}  flag")
    for r in result["rows"]:
        c, g = r["composed"], r["golden"]
        cs = f"{c['charge']} {c['tier']}" if c["charge"] is not None else "FAILED"
        gs = f"{g['charge']} {g['tier']}" if g["charge"] is not None else "FAILED"
        d = "" if r["delta"] is None else str(r["delta"])
        flag = "ok" if r["aligned"] else ("TIER" if not r["tier_match"] else "DELTA")
        if r["delta"] is None:
            flag = "READ"
        print(f"{r['title'][:34]:<34} {cs:>14} {gs:>14} {d:>6}  {flag}")
    print()
    print(f"  scored {s['scored']}/{s['songs']}  "
          f"tier-match {s['tier_match']}/{s['scored']}  "
          f"aligned {s['aligned']}/{s['scored']}  "
          f"max delta {s['max_delta']}  mean {s['mean_delta']}")
    if s["failed_reads"]:
        print(f"  WARNING: {s['failed_reads']} read(s) failed validation")


def main() -> int:
    ap = argparse.ArgumentParser(description="LEC dynamic score-parity run")
    ap.add_argument("fixture", help="JSON list of {title, artist, lyrics}")
    ap.add_argument("--out", help="write the full result JSON here")
    args = ap.parse_args()

    result = asyncio.run(run(Path(args.fixture)))
    _print_report(result)
    if args.out:
        Path(args.out).write_text(
            json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
