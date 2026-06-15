#!/usr/bin/env bash
# Deploy Libra Engine Compass to production (le-projects-01).
# Requires: code pushed to GitHub first, then this pulls + rebuilds on the server.
# First-time setup (DB, .env, le-proxy network, nginx block, cert) is a one-time
# manual run -- see deploy/DEPLOY.md. This script is the steady-state redeploy.
#
# Usage: bash deploy/deploy.sh
set -euo pipefail

SERVER="${LEC_DEPLOY_SERVER:-deploy@138.197.111.66}"
REMOTE_DIR="${LEC_REMOTE_DIR:-/root/libra-engine-compass}"

echo "==> Deploying LEC to $SERVER:$REMOTE_DIR"
ssh "$SERVER" "set -e; cd '$REMOTE_DIR'; git pull --ff-only; docker compose up -d --build; docker compose ps"

echo "==> Smoke test (/health via the lec container)"
ssh "$SERVER" "curl -fsS http://127.0.0.1:8012/health" && echo

echo "==> Done. Public check: curl -fsS https://lec.libraengine.com/health"
