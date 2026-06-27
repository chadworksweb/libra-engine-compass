#!/usr/bin/env bash
# Deploy Libra Engine Compass to production (le-projects-01).
#
# The server CANNOT `git pull` -- its deploy key has no access to the private LEC
# repo -- so this ships the committed tree via `git archive | scp | tar` instead.
# The server-side `.env` (secrets) and the `lec-data` volume are PRESERVED: the
# archive carries only tracked files (`.env` is gitignored), and extracting over
# the existing dir leaves it untouched.
#
# One-time setup (DB + user + schema-owner grant, prod `.env`, nginx block +
# cert) is in deploy/DEPLOY.md. This script is the steady-state redeploy.
# Usage: bash deploy/deploy.sh
set -euo pipefail

SERVER="${LEC_DEPLOY_SERVER:-deploy@138.197.111.66}"
REMOTE_DIR="${LEC_REMOTE_DIR:-/home/deploy/libra-engine-compass}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Packaging committed tree (HEAD)"
git -C "$REPO_ROOT" archive --format=tar.gz -o /tmp/lec-deploy.tgz HEAD

echo "==> Shipping to $SERVER:$REMOTE_DIR (mirror with deletes; preserving .env + data volume)"
scp -q /tmp/lec-deploy.tgz "$SERVER:/tmp/lec-deploy.tgz"
# Mirror the committed tree onto the server with rsync --delete so files DELETED
# from the repo are also removed on prod (a plain `tar` extract-over only adds and
# overwrites -- it NEVER deletes, so a removed file lingers in the build context and
# gets re-baked into the image; that bit us with the retired monolith 2026-06-27).
# Any file named .env (root or nested) is excluded so server-side secrets survive;
# the lec-data docker volume lives outside this dir and is untouched.
ssh "$SERVER" "set -e
  STAGE=\$(mktemp -d)
  tar xzf /tmp/lec-deploy.tgz -C \"\$STAGE\"
  mkdir -p '$REMOTE_DIR'
  rsync -a --delete --exclude='.env' \"\$STAGE\"/ '$REMOTE_DIR'/
  rm -rf \"\$STAGE\" /tmp/lec-deploy.tgz"
rm -f /tmp/lec-deploy.tgz

echo "==> Building + starting"
ssh "$SERVER" "cd '$REMOTE_DIR' && docker compose up -d --build && docker compose ps"

# Recreating the container gives it a new IP on the shared le-proxy network, but
# le-nginx resolved the 'lec' upstream at config-load and caches it, so the public
# domain 502s until the proxy re-resolves. A graceful reload fixes it.
echo "==> Reloading shared proxy (re-resolve the recreated upstream)"
ssh "$SERVER" "docker exec le-nginx nginx -s reload" || echo "WARN: le-nginx reload failed; run: ssh $SERVER \"docker exec le-nginx nginx -s reload\""

echo "==> Smoke test (internal /health, retrying through container boot)"
ssh "$SERVER" "curl -fsS --retry 10 --retry-delay 2 --retry-all-errors --max-time 60 http://127.0.0.1:8012/health" && echo
echo "==> Done. Public check: curl -fsS https://lec.libraengine.com/health"
