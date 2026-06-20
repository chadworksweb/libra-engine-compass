"""LECG configuration -- the Libra Engine Compass Governance venue (Cut 2).

The governance venue is the SECOND app in the libra-engine-compass repo
(Decision 4). It owns its own database and its own env, namespaced under the
`LECG_` prefix so it can never collide with the `lec-` instrument's `LEC_`
config when both run on the same droplet (le-projects-01).

Identity is the SHARED Clerk spine (LIBRA-ENGINE-ACCOUNT-ARCHITECTURE.md): the
venue verifies the same Clerk session JWTs RC does (same instance, same JWKS),
and lazily provisions its OWN local citizen records keyed to clerk_user_id. The
satellite-origin wiring on the shared Clerk app needs Clerk Pro; until then the
Clerk vars are simply unset and clerk_enabled() is False, so the write surfaces
are inert (they 503 "identity not yet wired") while the read surfaces and the
whole pipeline can be exercised locally with the dev-auth bypass.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- The venue's own database ---
    # Local default is a self-contained SQLite file (no infra). Prod points at a
    # dedicated `libra_engine_compass_gov` DB on the shared DO Managed Postgres
    # cluster via the PgBouncer pool -- DISTINCT from the lec- instrument's DB
    # (Decision 1: distinct app, distinct DB, distinct deploy).
    database_url: str = "sqlite:///./data/lecg.db"

    # --- Shared Clerk identity spine ---
    # Same Clerk instance as RC (the Libra Engine identity). The VALUE of the
    # JWKS URL is shared with RC; the var is namespaced LECG_ for this app. Unset
    # (the default) => clerk_enabled() False => write surfaces inert until the
    # Clerk-Pro satellite origin is wired. authorized_party binds tokens to the
    # Compass origin in prod; leave empty in dev. secret_key is server-side only
    # (used to read shared verified-human metadata + ban, Decision 3).
    clerk_jwks_url: str = ""
    clerk_authorized_party: str = ""
    clerk_secret_key: str = ""

    # --- Tier-2 "verified human" as a SHARED identity credential (Decision 3) ---
    # The verified-human bit lives on the shared Clerk identity (user metadata),
    # not on this venue's local citizen row. This is the JWT/metadata claim the
    # venue reads to decide Tier-2. RC writes it (Stripe Identity webhook) onto
    # the shared identity; every property reads the same bit. Default matches the
    # claim RC would mint; override per deploy if the JWT template differs.
    clerk_verified_claim: str = "verified_human"

    # --- Local dev auth bypass (NEVER enable in prod) ---
    # When clerk is not wired (no Clerk Pro yet), set LECG_DEV_AUTH=true locally
    # to exercise the full file-motion -> deliberate -> ratify pipeline without a
    # real Clerk session. Every authed call resolves to a single dev citizen
    # (dev_citizen_clerk_id), treated as Tier-2 verified. Fail-closed: ignored
    # entirely unless clerk is disabled AND this is explicitly true.
    dev_auth: bool = False
    dev_citizen_clerk_id: str = "lecg_dev_citizen"

    # --- Admin console (obscured login + signed session cookie) ---
    # Mirrors the lec- instrument's lec_admin_auth posture exactly: a secret login
    # URL + a self-contained HMAC session cookie, 404 (not 401) on every admin
    # route until all four values are set (fail-closed -- the panel is simply
    # absent until configured). LECG_-prefixed env.
    admin_login_token: str = ""
    admin_username: str = ""
    admin_password: str = ""
    admin_secret: str = ""  # HMAC key signing the session cookie
    admin_session_hours: int = 12

    # --- CORS allow-list ---
    # The public read surfaces (the amendment log, the motion ledger) may be
    # fetched cross-origin by the LE site / RC. Comma-separated origins; "*" for
    # local dev. The write surfaces are same-origin (the venue's own frontend).
    cors_allow_origins: str = "*"

    model_config = {
        "env_prefix": "LECG_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()


def clerk_enabled() -> bool:
    """True once the shared Clerk spine is wired (JWKS URL set). Gates the live
    write surfaces. While False, write endpoints 503 unless dev_auth is on."""
    return bool(settings.clerk_jwks_url)


def dev_auth_active() -> bool:
    """The local dev bypass is active ONLY when Clerk is not wired AND the
    operator explicitly opted in. Belt and braces so it can never shadow a real
    Clerk deploy."""
    return settings.dev_auth and not clerk_enabled()
