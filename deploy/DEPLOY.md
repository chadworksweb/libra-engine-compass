# LEC -- Phase 1 deploy (lec.libraengine.com)

Deploys the Compass scoring service to **le-projects-01** (the same droplet as
Rising Compass), on its own domain, with its own `libra_engine_compass` Postgres
DB on the shared DO Managed cluster. RC reaches it internally at
`http://lec:8012`; external clients (Lyric Transformer) hit
`https://lec.libraengine.com`.

Topology: LEC runs ONE container (`lec-backend`) joined to the existing external
`le-proxy` network as alias `lec`. It does **not** run its own nginx/certbot --
the host nginx (RC's, the only thing binding :80/:443) serves the domain via
`deploy/nginx-lec.conf` and proxies to the container.

Artifacts in this repo: `backend/Dockerfile`, `docker-compose.yml`,
`deploy/nginx-lec.conf`, `backend/scripts/issue_key.py`, `deploy/deploy.sh`.

---

## Prerequisites (decide / confirm first)

- [ ] **DNS: `libraengine.com` is on GoDaddy.** Add an `A` record so the cert
      step can resolve:
      GoDaddy -> My Products -> Domains -> `libraengine.com` -> DNS / Manage DNS
      -> Add New Record: **Type** `A`, **Name** `lec`, **Value** `138.197.111.66`,
      **TTL** 600s (or 1 hour). Save. Verify: `dig +short lec.libraengine.com`
      returns `138.197.111.66` (propagation: minutes, up to ~1h).
- [ ] **LEC's own Anthropic key** -- already provisioned (in local `backend/.env`).
      Reuse it or mint a prod-scoped one.
- [ ] GitHub: repo pushed. `deploy.sh` does `git pull` on the server.

---

## 1. Database (DO Managed Postgres, shared cluster)

Create LEC's own database + user + a PgBouncer pool (mirrors RC's `rc-pool`).
Via the DO console (Databases -> the cluster) or `doctl`:

- [ ] Create database `libra_engine_compass`.
- [ ] Create user `lec_app` (note the generated password).
- [ ] Create a **connection pool** `lec-pool` on db `libra_engine_compass`, mode
      **transaction**, user `lec_app` (port **25061**, like `rc-pool`).
- [ ] DSN (goes in the prod `.env` below):
      `postgresql+psycopg://lec_app:PASS@<cluster-host>:25061/lec-pool?sslmode=require`

LEC self-creates its schema on startup (`Base.metadata.create_all` in
`app/main.py`), so there is no separate migration step for the baseline.

## 2. Server: clone + prod .env

- [ ] `ssh deploy@138.197.111.66`
- [ ] `git clone git@github.com:chadworksweb/libra-engine-compass.git /root/libra-engine-compass`
      (or `cd` there if already cloned)
- [ ] Create `/root/libra-engine-compass/.env` (root level, next to
      `docker-compose.yml` -- compose substitutes `${...}` from here). NOT in git.

```
LEC_ANTHROPIC_API_KEY=sk-ant-...
LEC_AGENT_MODEL=claude-opus-4-6
LEC_DATABASE_URL=postgresql+psycopg://lec_app:PASS@<host>:25061/lec-pool?sslmode=require
LEC_AUTH_REQUIRED=true
LEC_ADMIN_LOGIN_TOKEN=<unguessable>
LEC_ADMIN_USERNAME=chadmin
LEC_ADMIN_PASSWORD=<strong>
LEC_ADMIN_SECRET=<python -c "import secrets;print(secrets.token_urlsafe(32))">
```

## 3. Bring up the container

- [ ] Confirm the external network exists: `docker network inspect le-proxy >/dev/null`
      (RC created it; LEC only joins it).
- [ ] `cd /root/libra-engine-compass && docker compose up -d --build`
- [ ] `docker compose ps` -> `lec-backend` healthy.
- [ ] Internal smoke: `curl -fsS http://127.0.0.1:8012/health` -> `{"status":"ok",...}`.
- [ ] RC -> LEC reachability (from the RC container):
      `docker exec rc-backend curl -fsS http://lec:8012/health`.

## 4. Issue service keys

With `LEC_AUTH_REQUIRED=true`, `/api/score` needs `X-Api-Key`. Mint one per client:

- [ ] `docker compose exec lec python scripts/issue_key.py --client lyric-transformer --name "Lyric Transformer" --label prod`
- [ ] `docker compose exec lec python scripts/issue_key.py --client rising-compass --name "Rising Compass" --label prod`

Copy each RAW key (printed once). LT key -> LT's `RC_SERVICE_KEY` (repointed at
LEC). RC key -> RC's `lec_api_key` (when RC routes through LEC, Phase 2).

## 5. nginx + cert (host nginx = RC's)

- [ ] DNS `lec.libraengine.com -> 138.197.111.66` is live (`dig +short lec.libraengine.com`).
- [ ] Make RC's nginx serve `deploy/nginx-lec.conf`: add a read-only volume line
      to RC's `nginx` service (in `/root/rising-compass/docker-compose.yml`):
      `- /root/libra-engine-compass/deploy/nginx-lec.conf:/etc/nginx/conf.d/lec.conf:ro`
      then `docker compose up -d nginx` in the RC dir. (The block references the
      `lec` alias on `le-proxy`; the RC nginx is already on that network.)
- [ ] Issue the cert via the shared certbot (webroot already mounted):
      `docker compose -f /root/rising-compass/docker-compose.yml run --rm certbot certonly --webroot -w /var/www/certbot -d lec.libraengine.com`
- [ ] Reload nginx: `docker compose -f /root/rising-compass/docker-compose.yml exec nginx nginx -s reload`
- [ ] Public smoke: `curl -fsS https://lec.libraengine.com/health`.
- [ ] Auth smoke: `curl -s -o /dev/null -w "%{http_code}" -X POST https://lec.libraengine.com/api/score -H "Content-Type: application/json" -d '{"type":"lyric","text":"..."}'`
      -> **401** without a key; **200** with `-H "X-Api-Key: <LT key>"` + real text.
- [ ] Admin: `https://lec.libraengine.com/lec-admin-<LEC_ADMIN_LOGIN_TOKEN>` -> sign in.

## 6. Steady-state redeploys

After the one-time setup above: `bash deploy/deploy.sh` (push to GitHub first;
it pulls + `docker compose up -d --build` + smoke-tests `/health`).

---

## Then: cut Lyric Transformer over (Phase 1 close-out)

- [ ] Point LT's `RC_API_BASE_URL` -> `https://lec.libraengine.com` and
      `RC_SERVICE_KEY` -> the LT key from step 4. Redeploy LT.
- [ ] Verify LT's Mirror scores through LEC (it grounds on `visceral_charge`;
      listener prose is client-enriched per the 2026-06-15 decision).
- [ ] Retire the local `:8010` shared-brain worktree + SSH tunnel LT used.

RC keeps its in-process calibrator until Phase 2 is proven; the RC->LEC client
is built on the `lec-integration` branch behind the fail-closed `lec.enabled`
flag, with `lec_base_url` set to `http://lec:8012` in RC's prod env when enabled.

## Notes / open items

- **`use_precedents`** scores statelessly today (the `precedent_songs` corpus is
  schema-only; sync mechanism is a later item).
- **Metering:** LEC logs calibration spend to its own `claude_api_usage` at the
  correct $5/$25 Opus rate; visible in the admin Console.
