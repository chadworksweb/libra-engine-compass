# Libra Engine Compass (LEC)

The standalone calibration brain of the Libra Engine. LEC reads a creative
artifact (lyric, poem, prose, message) against the rubric and returns its
charge: the tier, charge value, visceral read, and the listener-effects prose.

Extracted from Rising Compass so the calibrator can be tuned continuously on its
own line without colliding with RC feature work. RC, Lyric Transformer, and
future chargers consume LEC as HTTP clients.

## Architecture (locked 2026-06-14)

Full plan: `Dropbox/Libra Engine/Libra Engine Compass (LEC)/plans and docs/LEC-EXTRACTION-PLAN.md`

- **HTTP-everywhere.** RC + LT both call LEC over HTTP. No in-process path.
- **Co-located** on the same DO cluster/droplet as RC (loopback hop, negligible next to the Opus call).
- **Owns the rubric.** `tenets/core.json` + `precedents.json` are canonical here. RC's Motion Desk proposes amendments applied to LEC's tenets.
- **Own database** (`libra_engine_compass` on the shared DO cluster): service keys, the calibration-spend meter, and the precedent corpus (projected from RC).
- **Domain:** `lec.libraengine.com`.
- **API:** `POST /api/score` (with optional `use_precedents`), `GET /api/rubric`. Service-key auth.

## Status: Phase 0 in progress (extract + parity)

**Done:** brain-core modules lifted VERBATIM from RC (for parity diffing) into a mirrored `backend/app/...` layout:
- `services/charge_composition.py`, `services/agents/{calibrator,compass_agent_rubric,rubric_builder,summary_guard}.py`
- `services/agents/tenets/{core.json,precedents.json,satire.md}`

**Next (new session):**
1. `app/constants.py` (lift COLOR_LABELS/COLOR_HEX + add ARTIFACT_TYPES/labels from the RC WIP commit `042d995`).
2. `app/config.py` (LEC settings: own Anthropic key/model, DB URL) so the lifted `from app.config import settings` resolves to LEC's config.
3. `app/services/claude_meter.py` (LEC's metered Anthropic wrapper -> own `claude_api_usage`, correct $5/$25 Opus pricing) so `from app.services.claude_meter import tracked_create_async` resolves to LEC's.
4. Coupling cuts in `calibrator.py`: remove the db-gated enrichment branch (`if db and not skip_cache: ensure_full_calibration`) + the `Song` query - LEC is the SCORING half only; RC keeps enrichment/persistence.
5. `compass_agent_rubric.py`: rewire the precedent query off `app.models.Song` to LEC's own corpus (defer; stateless `use_precedents=false` parity first).
6. `app/routers/score.py` (from RC WIP `routers/shared_brain.py`) + `main.py` (FastAPI).
7. DB models for LEC's own DB (`api_client_keys`, `claude_api_usage`, precedent corpus).
8. **Parity harness:** LEC-as-service vs RC's calibrator on known songs (server-side Anthropic only - never terminal, per the RC rule). Stateless parity first.

## Provenance

Lifted from `rising-compass` at master (2026-06-14). The verbatim modules can be
diffed against RC to prove no scoring logic changed during extraction.
