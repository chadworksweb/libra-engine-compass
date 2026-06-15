"""Phase 0 parity harness: LEC `/api/score` vs RC's calibrator over HTTP.

Goal: prove the extraction changed NO scoring logic. Score N known artifacts
through LEC and through RC, then diff the SCORING outputs (tier, charge_value,
contaminated). The lyric system prompt is already proven byte-identical to RC
master (same rubric + CALIBRATION_FORMAT), and LEC's calibrator is RC's verbatim,
so at temperature=0 the reads should match; this harness verifies it on real
artifacts.

NO ANTHROPIC FROM THE TERMINAL. This harness makes ZERO Anthropic calls -- it is
an HTTP client. Both sides run the model SERVER-SIDE:
  - LEC: a running `uvicorn app.main:app` (POST /api/score).
  - RC:  a running scorer exposing the same `/api/score` contract -- the WIP
         shared_brain endpoint on the rc-tracks/shared-brain worktree (:8010),
         or later the deployed LEC itself. Optional: omit --rc-base to capture
         LEC-only results.

Stateless first: use_precedents=false on both sides (the precedent corpus is a
Phase 1 sync item).

Fixtures: a JSON list of {title, artist, type, text}. Lyrics are copyrighted --
do NOT commit them. Point --fixtures at a PRIVATE file (e.g. under Dropbox/Debug)
for real-song parity; `fixtures.example.json` ships only public-domain/original
text so the harness runs out of the box.

Usage:
    python -m parity.run_parity --fixtures parity/fixtures.example.json \
        --lec-base http://localhost:8012 --rc-base http://localhost:8010
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

# The scoring fields that MUST match for parity. Prose/ether enrichment is RC's,
# not LEC's, so it is deliberately out of scope here.
PARITY_FIELDS = ("status", "color_key", "charge_value", "contaminated")


async def _score(client: httpx.AsyncClient, base: str, fx: dict, api_key: str | None) -> dict:
    headers = {"X-Api-Key": api_key} if api_key else {}
    body = {
        "type": fx.get("type", "lyric"),
        "text": fx["text"],
        "title": fx.get("title", ""),
        "artist": fx.get("artist", ""),
        "use_precedents": False,
    }
    r = await client.post(f"{base.rstrip('/')}/api/score", json=body, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


def _slim(result: dict) -> dict:
    return {k: result.get(k) for k in PARITY_FIELDS}


async def main() -> int:
    ap = argparse.ArgumentParser(description="LEC-vs-RC scoring parity harness (HTTP, server-side Anthropic only).")
    ap.add_argument("--fixtures", required=True, help="path to a JSON list of {title, artist, type, text}")
    ap.add_argument("--lec-base", default="http://localhost:8012", help="LEC service base URL")
    ap.add_argument("--rc-base", default=None, help="RC scorer base URL (same /api/score contract); omit for LEC-only")
    ap.add_argument("--lec-key", default=None, help="X-Api-Key for LEC (only if LEC_AUTH_REQUIRED=true)")
    ap.add_argument("--rc-key", default=None, help="X-Api-Key for the RC scorer")
    ap.add_argument("--out", default=None, help="write the full report JSON here")
    args = ap.parse_args()

    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    rows = []
    mismatches = 0

    async with httpx.AsyncClient() as client:
        for fx in fixtures:
            label = f'{fx.get("title", "?")} / {fx.get("artist", "?")} [{fx.get("type", "lyric")}]'
            row = {"label": label}
            try:
                lec = await _score(client, args.lec_base, fx, args.lec_key)
                row["lec"] = _slim(lec)
            except Exception as exc:
                row["lec"] = {"error": f"{type(exc).__name__}: {exc}"}

            if args.rc_base:
                try:
                    rc = await _score(client, args.rc_base, fx, args.rc_key)
                    row["rc"] = _slim(rc)
                except Exception as exc:
                    row["rc"] = {"error": f"{type(exc).__name__}: {exc}"}
                row["match"] = row.get("lec") == row.get("rc")
                if not row["match"]:
                    mismatches += 1
            rows.append(row)

    # Report
    print(f"\nParity: {len(rows)} artifact(s)" + (f", {mismatches} mismatch(es)" if args.rc_base else " (LEC-only capture)"))
    print("-" * 88)
    for row in rows:
        if args.rc_base:
            flag = "OK " if row.get("match") else "XX "
            print(f"{flag}{row['label']}")
            print(f"     LEC: {row['lec']}")
            print(f"     RC : {row['rc']}")
        else:
            print(f"    {row['label']}")
            print(f"     LEC: {row['lec']}")
    print("-" * 88)

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"report -> {args.out}")

    if args.rc_base and mismatches:
        print(f"\nFAIL: {mismatches} scoring mismatch(es) -- extraction is NOT parity-clean.")
        return 1
    if args.rc_base:
        print("\nPASS: every artifact scored identically on tier + charge_value + contamination.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
