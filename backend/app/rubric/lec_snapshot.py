"""Freeze the current LEC calibrator as an IMMUTABLE rubric snapshot (a parity +
rollback baseline). Snapshots land in app/rubric/_snapshots/rubric-snapshot-<date>/.

Why: the gospel and lyric lens are authored fresh, so a composed prompt is NOT
byte-identical to an older render. A snapshot is the fixed reference a composition
change is SCORE-parity-checked against (see lec_parity_check) and the rollback point.
NOTE: as of the 2026-06-27 cutover the composed gospel+lens is the LIVE instrument;
snapshots are history/regression baselines, never the canonical rubric.

Captures the exact rendered lyric SYSTEM prompt (the composed gospel+lens definition
+ the calibration-format method), the rubric_version, the model id, and verbatim
copies of the composed-instrument SOURCE files (gospel + lens + live lens data),
plus a manifest with hashes and the git commit. The retired monolith
(rc-lyric-rubric.json) is NOT part of a snapshot anymore.

Run:
    cd backend
    SNAPSHOT_COMMIT=$(git rev-parse HEAD) .venv/Scripts/python.exe -m app.rubric.lec_snapshot
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

from app.services.agents.lec_compass_agent_rubric import build_calibration_prompt
from app.rubric.lec_lens import load_gospel
from app.routers.lec_score import rubric_version

try:
    from app.lec_config import settings
    MODEL = settings.agent_model
except Exception:  # pragma: no cover - config should always import
    MODEL = "unknown"

SNAPSHOT_DATE = os.environ.get("SNAPSHOT_DATE", os.environ.get("GOLDEN_DATE", "2026-06-18"))
HERE = Path(__file__).resolve().parent
OUT = HERE / "_snapshots" / f"rubric-snapshot-{SNAPSHOT_DATE}"

# The composed instrument's verbatim source files: the gospel (le-baseline), the
# rc-lyric lens bundle, and the live lens data still read at runtime. Together they
# reconstruct the composed prompt. (dest_name, source_path)
LIVE_LENS = HERE.parent / "services" / "agents" / "rc-lyric-live"
SOURCE_FILES = [
    ("le-cores.json", HERE / "le-baseline" / "le-cores.json"),
    ("le-scaffold.json", HERE / "le-baseline" / "le-scaffold.json"),
    ("le-method.json", HERE / "le-baseline" / "le-method.json"),
    ("le-satire.json", HERE / "le-baseline" / "le-satire.json"),
    ("rc-lyric-bundle.json", HERE / "rc-lyric" / "rc-lyric-bundle.json"),
    ("rc-lyric-precedents.json", LIVE_LENS / "rc-lyric-precedents.json"),
    ("rc-lyric-satire.md", LIVE_LENS / "rc-lyric-satire.md"),
    ("rc-lyric-inhabited-voice.md", LIVE_LENS / "rc-lyric-inhabited-voice.md"),
]


def main() -> int:
    system_prompt, user_prompt = build_calibration_prompt(
        "<TITLE>", "<ARTIST>", "<LYRICS>", artifact_type="lyric"
    )
    sp_sha = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "system_prompt_lyric.txt").write_text(system_prompt, encoding="utf-8")
    (OUT / "user_prompt_lyric.txt").write_text(user_prompt, encoding="utf-8")
    for dest_name, src in SOURCE_FILES:
        shutil.copyfile(src, OUT / dest_name)

    gospel = load_gospel()
    manifest = {
        "snapshot_date": SNAPSHOT_DATE,
        "purpose": (
            "Immutable snapshot of the live composed LEC instrument (gospel + "
            "rc-lyric lens) for SCORE-parity checks and rollback. Captured "
            "post-cutover; never the canonical rubric (that is whatever prod serves)."
        ),
        "git_commit": os.environ.get(
            "SNAPSHOT_COMMIT",
            os.environ.get("GOLDEN_COMMIT", "(unset: re-run with SNAPSHOT_COMMIT)"),
        ),
        "model": MODEL,
        "rubric_version": rubric_version(),
        "system_prompt_sha256": sp_sha,
        "system_prompt_chars": len(system_prompt),
        "counts": {
            "tiers": len(gospel["tiers"]),
            "tenets": sum(len(t["tenets"]) for t in gospel["tiers"]),
            "modifiers": len(gospel["modifiers"]),
            "flags": len(gospel["flags"]),
            "rules": len(gospel["rules"]),
        },
        "files": ["system_prompt_lyric.txt", "user_prompt_lyric.txt"]
        + [dest for dest, _ in SOURCE_FILES],
    }
    with open(OUT / "MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
        f.write("\n")

    print(f"RUBRIC SNAPSHOT written to {OUT.relative_to(HERE.parent.parent)}")
    print(f"  rubric_version       : {manifest['rubric_version']}")
    print(f"  system_prompt_sha256 : {sp_sha}")
    print(f"  system_prompt_chars  : {len(system_prompt)}")
    print(f"  model                : {MODEL}")
    print(f"  git_commit           : {manifest['git_commit']}")
    print(f"  counts               : {manifest['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
