# LEC parity harness (Phase 0)

Proves the extraction changed no scoring logic: score the same artifacts through
LEC and through RC, diff tier + charge_value + contamination. The lyric system
prompt is already byte-identical to RC master (verified), and LEC's calibrator is
RC's verbatim, so at temperature=0 the reads should match.

## Rules

- **No Anthropic from the terminal.** The harness is an HTTP client and makes
  zero model calls. Both sides run Opus SERVER-SIDE (inside a uvicorn process).
- **Stateless first.** `use_precedents=false` on both sides (the precedent corpus
  is a Phase 1 sync item).
- **Never commit lyrics.** `fixtures.example.json` ships only public-domain text.
  For real-song parity, point `--fixtures` at a PRIVATE file (e.g. under
  `Dropbox/Debug/`), lyrics sourced the usual way (`Dropbox/Debug/dd.txt`).

## Run

1. Start LEC locally (its own Anthropic key + DB in `backend/.env`):

   ```
   cd backend
   .venv/Scripts/uvicorn app.main:app --port 8012
   ```

2. Start an RC scorer exposing the same `POST /api/score` contract -- the WIP
   shared_brain endpoint on the `rc-tracks/shared-brain` worktree (:8010). Omit
   `--rc-base` to capture LEC-only results without a diff.

3. Run the harness:

   ```
   python -m parity.run_parity \
     --fixtures parity/fixtures.example.json \
     --lec-base http://localhost:8012 \
     --rc-base  http://localhost:8010 \
     --out parity/report.json
   ```

Exit code is non-zero if any artifact's tier / charge_value / contamination
differs between LEC and RC.

## Scope

Only the SCORING fields are compared (`status`, `color_key`, `charge_value`,
`contaminated`). The enrichment outputs (listener/effects/ether/societal prose)
are RC's, not LEC's, and are intentionally out of scope.
