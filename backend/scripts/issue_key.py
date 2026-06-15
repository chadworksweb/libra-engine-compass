"""Issue a service API key for a LEC client (RC, Lyric Transformer, a charger).

Creates the ApiClient if absent, mints one ApiClientKey, prints the RAW key
ONCE (only the sha256 is stored). Run it INSIDE the container so it uses the
prod DSN + network:

    docker compose exec lec python scripts/issue_key.py \
        --client lyric-transformer --name "Lyric Transformer" --label prod

Then paste the printed key into that client's config (LT: RC_SERVICE_KEY ->
repointed at LEC; RC: lec_api_key). Re-running with the same --client adds
another key to the same client (rotation); revoke old keys in the DB.
"""

import argparse
import hashlib
import os
import secrets
import sys

# Make `app` importable when run as `python scripts/issue_key.py` (adds the
# backend/ root to sys.path, so no PYTHONPATH is needed).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (register models on Base)
from app.models import ApiClient, ApiClientKey


def main() -> int:
    ap = argparse.ArgumentParser(description="Issue a LEC service API key.")
    ap.add_argument("--client", required=True, help="client slug, e.g. lyric-transformer")
    ap.add_argument("--name", help="display name (defaults to the slug)")
    ap.add_argument("--label", default="prod", help="key label (default: prod)")
    ap.add_argument("--contact", default=None, help="optional contact email")
    args = ap.parse_args()

    # Ensure tables exist (no-op once main.py has run create_all on startup).
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        client = db.query(ApiClient).filter(ApiClient.slug == args.client).first()
        if client is None:
            client = ApiClient(
                slug=args.client,
                name=args.name or args.client,
                contact_email=args.contact,
                status="active",
            )
            db.add(client)
            db.flush()
            created = True
        else:
            created = False

        raw = "lec_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        prefix = raw[:12]
        db.add(ApiClientKey(
            client_id=client.id,
            key_hash=key_hash,
            key_prefix=prefix,
            label=args.label,
        ))
        db.commit()
    finally:
        db.close()

    print()
    print(f"  client : {args.client} ({'created' if created else 'existing'})")
    print(f"  label  : {args.label}")
    print(f"  prefix : {prefix}")
    print()
    print("  RAW KEY (shown once -- copy it now):")
    print(f"    {raw}")
    print()
    print("  Set LEC_AUTH_REQUIRED=true so the key is enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
