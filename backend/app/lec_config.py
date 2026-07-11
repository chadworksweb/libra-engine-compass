"""LEC configuration.

The lifted brain reads `from app.lec_config import settings`; the attribute names
here (anthropic_api_key, agent_model, escalation_*) MATCH RC's so the verbatim
calibrator resolves unchanged. Every env var carries the `LEC_` prefix so LEC's
config can never collide with RC's when both run on the same droplet.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Anthropic (LEC's own workspace/key) ---
    # LATEST Opus (per Chad 2026-07-11): the calibrator tracks the newest Opus
    # rather than staying pinned to RC's historical model. This DELIBERATELY breaks
    # the old score-parity pin (was claude-opus-4-6) and re-baselines scoring; bump
    # this when a newer Opus ships (there is no "latest" alias in the API). LEC's
    # difference from RC is the METER pricing (correct $5/$25 Opus), not the model.
    anthropic_api_key: str = ""
    agent_model: str = "claude-opus-4-8"

    # Calibrator v3 escalation gate. Defaults mirror RC (Opus everywhere, re-pass
    # off -> the gate only records triggers; no second model call).
    escalation_model: str = ""
    escalation_repass_enabled: bool = False
    escalation_confidence_floor: float = 0.6

    # --- LEC's own database ---
    # Local default is a self-contained SQLite file (no infra). Prod points at
    # the dedicated libra_engine_compass DB on the shared DO Managed Postgres
    # cluster via the PgBouncer pool.
    database_url: str = "sqlite:///./data/lec.db"

    # --- Admin panel (obscured-token login + signed session cookie) ---
    # The dashboard at /admin is gated behind a secret login URL
    # (/lec-admin-<admin_login_token>) plus an HttpOnly signed session cookie,
    # mirroring RC's admin pattern. ALL THREE values must be set or every admin
    # route 404s (fail-closed, so the panel is simply absent until configured).
    # LEC_-prefixed env: LEC_ADMIN_LOGIN_TOKEN, LEC_ADMIN_USERNAME,
    # LEC_ADMIN_PASSWORD, LEC_ADMIN_SECRET.
    admin_login_token: str = ""
    admin_username: str = ""
    admin_password: str = ""
    admin_secret: str = ""  # HMAC key signing the session cookie
    admin_session_hours: int = 12

    # --- Service-key auth on /api/score (X-Api-Key) ---
    # False (local/parity default) leaves scoring open. True enforces a valid key
    # from api_client_keys. LEC issues + verifies its own keys for its clients
    # (RC, LT, future chargers).
    auth_required: bool = False

    # --- Decoupling cutover flag (Part 1) ---
    # When True, the calibrator builds the lyric system prompt by COMPOSING the
    # gospel (le-cores/le-scaffold/le-method) + the rc-lyric lens via
    # lec_full_prompt.compose_cutover_prompt, instead of rendering the monolithic
    # rc-lyric-rubric.json. Default False (dark): zero behavior change until it is
    # flipped. Fail-closed -- any composition error falls back to the monolith.
    # Only the lyric path is wired (the score-parity-validated lens). Env:
    # LEC_COMPOSE_RUBRIC.
    compose_rubric: bool = False

    model_config = {
        "env_prefix": "LEC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
