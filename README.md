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

## Status: Phase 0 -- brain stands up locally; parity-ready

The full scoring service boots locally (`POST /api/score`, `GET /api/rubric`,
`/health`) against LEC's own DB. The lyric system prompt is **byte-for-byte
identical to RC master** (verified by sha256), so the scoring is unchanged.

**Done:**
- Brain-core lifted VERBATIM from RC (commit `390963e`): `services/charge_composition.py`,
  `services/agents/{calibrator,compass_agent_rubric,rubric_builder,summary_guard}.py`,
  `services/agents/tenets/{core.json,precedents.json,satire.md}`.
- `app/constants.py` (COLOR_* + TIER_ORDER + ARTIFACT_TYPES/labels).
- `app/config.py` (LEC settings, `LEC_` env prefix; matches RC attribute names so the lift resolves).
- `app/services/claude_meter.py` (LEC's own meter -> own `claude_api_usage`, CORRECT $5/$25 Opus pricing).
- **Coupling cuts in `calibrator.py`:** removed the db-gated cache branch, the
  `lookup_calibrated` / `ensure_full_calibration` / `_ensure_generation` chain,
  the `Song` import, and the final enrichment call. LEC is the SCORING half only;
  RC keeps enrichment + persistence. Added the `artifact_type` param.
- **`compass_agent_rubric.py`:** dropped the Song-backed `build_few_shot_examples`
  (dead in v2) + the RC narrative/editorial builders; added the `artifact_type`
  prompt framing. `rubric_builder.py`: per-type precedent corpus loader (lyric fallback).
- `app/services/lyric_quote_guard.py` (lifted; the verbatim-quote scrub in the scoring path).
- `app/routers/score.py` (from RC WIP `shared_brain.py`) + `app/deps.py` (X-Api-Key auth) + `app/main.py`.
- `app/models.py` (`api_clients` / `api_client_keys`, `claude_api_usage`, `precedent_songs`) +
  `migrations/001_lec_baseline.py` (create_all baseline; main.py also ensures it on startup).
- **Parity harness** `parity/run_parity.py` -- HTTP client, server-side Anthropic
  only, stateless (`use_precedents=false`); diffs tier + charge_value + contamination.

**Open (Phase 1):**
- Run the parity harness on real songs (start LEC + an RC `/api/score` scorer; needs a live Anthropic key).
- Precedent corpus sync mechanism (the `precedent_songs` projection is schema-only; `use_precedents=true` scores stateless for now).
- LEC's own Anthropic workspace/key; `libraengine.com` DNS registrar for `lec.libraengine.com`.
- Listener-prose ownership for external clients (LT's Mirror needs `listener_effects_prose`, which is currently RC enrichment, so LEC returns it null).

## Provenance

Lifted from `rising-compass` at master (2026-06-14). The verbatim modules diff
clean against RC; the lyric prompt sha256 matches RC master exactly.
