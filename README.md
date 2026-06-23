# Libra Engine Compass (LEC + LECG)

The standalone calibration brain of the Libra Engine. LEC reads a creative
artifact (lyric, poem, prose, message) against the rubric and returns its
charge: the tier, charge value, visceral read, and the listener-effects prose.

Extracted from Rising Compass so the calibrator can be tuned continuously on its
own line without colliding with RC feature work. RC, Lyric Transformer, and
future chargers consume LEC as HTTP clients. **LEC is RC's SOLE live scorer since
2026-06-16** -- RC carries zero rubric/calibration code and consumes LEC through
the `rc-lyric` lens only.

## Two apps in this repo

This repo holds TWO apps that `deploy/deploy.sh` builds together:

- **LEC -- the INSTRUMENT** (scores). Container `lec-backend` on `:8012`,
  domain `lec.libraengine.com`. See `deploy/DEPLOY.md`.
- **LECG -- the GOVERNANCE VENUE** (Motion Desk + Deliberation Chamber +
  amendment pipeline + ratification write-back). Container `lecg-backend` on
  `:8014`, domain `lecg.libraengine.com`, its own governance DB
  (`libra_engine_compass_gov` + user `lecg_app`). Write surfaces are gated (503)
  until Clerk Pro. See `deploy/DEPLOY-LECG.md`.

LEC **owns the canonical constitution/tenets** (the tenets are the LEC tenets;
they live ON LEC and serve read-only at `lec.libraengine.com/tenets/`). The
public constitution API (`/api/constitution`, `/api/constitution/version`) is
served by the governance package's public surface (`governance/lecg_public.py`).
The governed `constitution_version` is `46528e8caeed`; the instrument's composed
`rubric_version` is `716339b3385f`. LEC pins the governed constitution version
(fail-soft) and adopts new editions deliberately (materialized into `le-baseline`
plus a git `edition-<version>` tag).

Bucket/prefix scheme: `le-` = universal LAW (constitution: cores, scaffold,
rules), `lec-` = the INSTRUMENT, `lecg-` = the GOVERNANCE venue, `<lens>-` =
domain lenses (`rc-lyric`, `cc-essay`, `lt-`).

## Architecture (locked 2026-06-14)

Full plan: `Dropbox/Libra Engine/Libra Engine Compass (LEC)/plans and docs/LEC-EXTRACTION-PLAN.md`

- **HTTP-everywhere.** RC + LT both call LEC over HTTP. No in-process path.
- **Co-located** on the same DO cluster/droplet as RC (loopback hop, negligible next to the Opus call).
- **Owns / hosts the constitution.** The canonical constitution + tenets live ON
  LEC, served read-only at `lec.libraengine.com/tenets/` + `/api/constitution`.
  The instrument composes its rubric from the gospel (`le-baseline/`) plus a
  domain lens. Amendments flow through the LECG governance venue's pipeline.
- **Own database** (`libra_engine_compass` on the shared DO cluster): service keys, the calibration-spend meter, and the precedent corpus (projected from RC).
- **Domain:** `lec.libraengine.com`.
- **API:** `POST /api/score` (with optional `use_precedents`), `GET /api/rubric`. Service-key auth.

## Status: LIVE -- LEC is RC's sole live scorer (deployed 2026-06-15/16)

LEC is deployed at `https://lec.libraengine.com` and is RC's sole live scorer
since 2026-06-16; the LECG governance venue is also deployed (write surfaces
gated until Clerk Pro). The history below is preserved as the Phase 0 extraction
record.

The scoring service runs (`uvicorn app.lec_main:app --port 8012` locally) against
LEC's own DB and **makes real Opus calls** (`POST /api/score`, `GET /api/rubric`,
`/health`). Verified: the Dickinson poem reads Ascended/violet, "Row Your Boat"
Decent/green; the meter logs each call at the correct $5/$25 Opus rate. The lyric
system prompt + the scoring core (`charge_composition`, `summary_guard`, the live
rubric module in `services/agents/rc-lyric-live/`, `_read_v3`) were extracted
**byte-for-byte identical to RC master** (sha256-verified) at the Phase 0 lift.

**Run it:** put a dedicated key in `backend/.env` (`LEC_ANTHROPIC_API_KEY`), then
`cd backend && .venv/Scripts/uvicorn app.lec_main:app --port 8012`.

**North star:** LEC is the prerequisite for the **Lyric Transformer** and
**Creative Charger** launches -- they consume it over HTTP. Finish LEC (deploy +
the listener-prose decision), then ship those. Full sequence in the plan doc.

**Done:**
- Brain-core lifted VERBATIM from RC (commit `390963e`): `services/charge_composition.py`,
  `services/agents/{calibrator,compass_agent_rubric,rubric_builder,summary_guard}.py`,
  `services/agents/tenets/{core.json,precedents.json,satire.md}`.
- `app/constants.py` (COLOR_* + TIER_ORDER + ARTIFACT_TYPES/labels).
- `app/lec_config.py` (LEC settings, `LEC_` env prefix; matches RC attribute names so the lift resolves).
- `app/services/claude_meter.py` (LEC's own meter -> own `claude_api_usage`, CORRECT $5/$25 Opus pricing).
- **Coupling cuts in `calibrator.py`:** removed the db-gated cache branch, the
  `lookup_calibrated` / `ensure_full_calibration` / `_ensure_generation` chain,
  the `Song` import, and the final enrichment call. LEC is the SCORING half only;
  RC keeps enrichment + persistence. Added the `artifact_type` param.
- **`compass_agent_rubric.py`:** dropped the Song-backed `build_few_shot_examples`
  (dead in v2) + the RC narrative/editorial builders; added the `artifact_type`
  prompt framing. `rubric_builder.py`: per-type precedent corpus loader (lyric fallback).
- `app/services/lyric_quote_guard.py` (lifted; the verbatim-quote scrub in the scoring path).
- `app/routers/lec_score.py` (from RC WIP `shared_brain.py`) + `app/lec_deps.py` (X-Api-Key auth) + `app/lec_main.py`.
- `app/lec_models.py` (`api_clients` / `api_client_keys`, `claude_api_usage`, `precedent_songs`) +
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
