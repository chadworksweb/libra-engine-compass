"""Freeze today's LEC calibrator as the IMMUTABLE golden reference, taken before
the Decoupling rips the rubric into gospel + lenses.

Why: we author the gospel and the lyric lens fresh (not by lifting RC's text), so
the new composed prompt will NOT be byte-identical. RC keeps running on deployed
`main`; the freshly composed `gospel + lyric lens` is validated by SCORE PARITY
against this snapshot before any cutover. This is the rollback + parity baseline.

Captures the exact rendered lyric SYSTEM prompt RC uses today (RUBRIC_DEFINITION +
CALIBRATION_FORMAT), the rubric_version, the model id, and verbatim copies of the
tenet files, plus a manifest with hashes and the git commit.

Run:
    cd backend
    GOLDEN_COMMIT=$(git rev-parse HEAD) .venv/Scripts/python.exe -m app.rubric.lec_snapshot_golden
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

from app.services.agents.compass_agent_rubric import build_calibration_prompt
from app.services.agents.rubric_builder import load_tenets
from app.routers.score import rubric_version

try:
    from app.config import settings
    MODEL = settings.agent_model
except Exception:  # pragma: no cover - config should always import
    MODEL = "unknown"

SNAPSHOT_DATE = os.environ.get("GOLDEN_DATE", "2026-06-18")
HERE = Path(__file__).resolve().parent
OUT = HERE / f"lec-golden-{SNAPSHOT_DATE}"
TENETS = HERE.parent / "services" / "agents" / "tenets"


def main() -> int:
    system_prompt, user_prompt = build_calibration_prompt(
        "<TITLE>", "<ARTIST>", "<LYRICS>", artifact_type="lyric"
    )
    sp_sha = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "system_prompt_lyric.txt").write_text(system_prompt, encoding="utf-8")
    (OUT / "user_prompt_lyric.txt").write_text(user_prompt, encoding="utf-8")
    for name in ("rc-lyric-rubric.json", "rc-lyric-precedents.json", "rc-lyric-satire.md"):
        shutil.copyfile(TENETS / name, OUT / name)

    data = load_tenets()
    manifest = {
        "snapshot_date": SNAPSHOT_DATE,
        "purpose": (
            "Immutable golden reference of the LEC calibrator before the "
            "Decoupling. The fresh gospel + lyric-lens composition is score-parity "
            "checked against this. RC runs on deployed main until parity passes "
            "and a deliberate cutover."
        ),
        "git_commit": os.environ.get("GOLDEN_COMMIT", "(unset: re-run with GOLDEN_COMMIT)"),
        "model": MODEL,
        "rubric_version": rubric_version(),
        "system_prompt_sha256": sp_sha,
        "system_prompt_chars": len(system_prompt),
        "counts": {
            "tiers": len(data["tiers"]),
            "tenets": sum(len(t["tenets"]) for t in data["tiers"]),
            "modifiers": len(data["modifiers"]),
            "flags": len(data["flags"]),
            "rules": len(data["rules"]),
        },
        "files": [
            "system_prompt_lyric.txt",
            "user_prompt_lyric.txt",
            "rc-lyric-rubric.json",
            "rc-lyric-precedents.json",
            "rc-lyric-satire.md",
        ],
    }
    with open(OUT / "MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
        f.write("\n")

    print(f"GOLDEN SNAPSHOT written to {OUT.relative_to(HERE.parent.parent)}")
    print(f"  rubric_version       : {manifest['rubric_version']}")
    print(f"  system_prompt_sha256 : {sp_sha}")
    print(f"  system_prompt_chars  : {len(system_prompt)}")
    print(f"  model                : {MODEL}")
    print(f"  git_commit           : {manifest['git_commit']}")
    print(f"  counts               : {manifest['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
