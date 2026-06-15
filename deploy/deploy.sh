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

echo "==> Shipping to $SERVER:$REMOTE_DIR (preserving .env + data volume)"
scp -q /tmp/lec-deploy.tgz "$SERVER:/tmp/lec-deploy.tgz"
ssh "$SERVER" "set -e; mkdir -p '$REMOTE_DIR' && tar xzf /tmp/lec-deploy.tgz -C '$REMOTE_DIR' && rm -f /tmp/lec-deploy.tgz"
rm -f /tmp/lec-deploy.tgz

echo "==> Building + starting"
ssh "$SERVER" "cd '$REMOTE_DIR' && docker compose up -d --build && docker compose ps"

echo "==> Smoke test (internal /health)"
ssh "$SERVER" "curl -fsS http://127.0.0.1:8012/health" && echo
echo "==> Done. Public check: curl -fsS https://lec.libraengine.com/health"
