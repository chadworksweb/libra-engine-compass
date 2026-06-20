"""Adopt an edition: bake the pending ratified amendments into le-baseline (lecg-).

RULED (Chad, 2026-06-20): the lec instrument adopts a ratified edition by
materializing the governed constitution back into the le-baseline files, then a
git commit (tag edition-<version>) + redeploy re-pins it. Git is the edition
ledger; genesis lives on as the v1 tag. This CLI is the materialize step of that
gated procedure; the git + deploy steps stay a human/CI act (the live scorer only
moves by a deliberate hand).

Procedure (on le-projects-01, deliberate, gated):
  1. Preview     python -m governance.lecg_adopt --dry-run
                 (or the admin GET /api/admin/edition/preview)
  2. Materialize python -m governance.lecg_adopt --apply
                 (bakes pending amendments into le-baseline/*.json + marks them adopted)
  3. Review the git diff, commit, tag edition-<version>
  4. Redeploy lec (deploy.sh) -> the instrument re-pins the new constitution_version

Until step 4, lec /health reports the pin out of sync (the pending adoption,
surfaced). --dry-run touches nothing and just reports the would-be version + count.
"""

from __future__ import annotations

import argparse
import logging

from governance.lecg_database import Base, SessionLocal
from governance import lecg_amendments as A


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Adopt an edition into le-baseline (lecg-).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Report what would adopt; touch nothing.")
    group.add_argument("--apply", action="store_true", help="Bake pending amendments into le-baseline + mark adopted.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    Base.metadata.create_all(bind=SessionLocal().get_bind())
    db = SessionLocal()
    try:
        report = A.materialize_to_baseline(db, dry_run=args.dry_run)
    finally:
        db.close()

    print("Edition adoption:" + (" (dry-run)" if args.dry_run else ""))
    for key, value in report.items():
        print(f"  {key}: {value}")
    if not args.dry_run and report["amendments_adopted"]:
        print(
            "\nNext (gated, human): review the git diff, commit, tag "
            f"edition-{report['version']}, then redeploy lec to re-pin the instrument."
        )
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
