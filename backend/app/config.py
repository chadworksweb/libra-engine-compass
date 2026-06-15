"""LEC configuration.

The lifted brain reads `from app.config import settings`; the attribute names
here (anthropic_api_key, agent_model, escalation_*) MATCH RC's so the verbatim
calibrator resolves unchanged. Every env var carries the `LEC_` prefix so LEC's
config can never collide with RC's when both run on the same droplet.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Anthropic (LEC's own workspace/key) ---
    # The model MUST match RC's for scoring parity (claude-opus-4-6); LEC's
    # difference from RC is the METER pricing (correct $5/$25 Opus), not the
    # model. LEC's own key is a Phase 0/1 open item -- per-product cost + blast
    # radius, the same principle as Lyric Transformer's key.
    anthropic_api_key: str = ""
    agent_model: str = "claude-opus-4-6"

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
    # LEC_-prefixed env: LEC_ADMIN_LOGIN_TOKEN, LEC_ADMIN_PASSWORD,
    # LEC_ADMIN_SECRET.
    admin_login_token: str = ""
    admin_password: str = ""
    admin_secret: str = ""  # HMAC key signing the session cookie
    admin_session_hours: int = 12

    # --- Service-key auth on /api/score (X-Api-Key) ---
    # False (local/parity default) leaves scoring open. True enforces a valid key
    # from api_client_keys. LEC issues + verifies its own keys for its clients
    # (RC, LT, future chargers).
    auth_required: bool = False

    model_config = {
        "env_prefix": "LEC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
