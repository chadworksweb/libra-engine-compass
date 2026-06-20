# LECG -- governance venue deploy (lecg.libraengine.com)

> Decoupling Part 2, Cut 1. The Libra Engine Compass GOVERNANCE venue (the
> `lecg-` app) goes live on its own subdomain, a second container beside the
> `lec-` instrument on le-projects-01. Cut 1 is READ-ONLY + PUBLIC: it serves the
> canonical constitution. Cut 2 adds the write surfaces (Motion Desk / Chamber /
> amendments) behind shared Clerk + a governance DB.

Topology mirrors `lec` (see `DEPLOY.md`): one container (`lecg-backend`) on the
external `le-proxy` network as alias `lecg`, bound to `127.0.0.1:8014`. The host
proxy `le-nginx` (`/root/proxy/`) serves the domain via `deploy/nginx-lecg.conf`
and proxies to the container. No DB, no secrets, no Anthropic key in Cut 1 -- the
constitution is baked into the image (the `le-baseline` files) and served
read-only, so there is nothing to provision but DNS + cert.

## One-time setup (GATED -- needs sign-off)

1. **DNS (GoDaddy, manual).** Add an `A` record so the cert can resolve:
   `libraengine.com` -> DNS -> Add: Type `A`, Name `lecg`, Value `138.197.111.66`,
   TTL 600. Verify: `dig +short lecg.libraengine.com` -> `138.197.111.66`.
2. **Ship the tree + bring up both containers.** `bash deploy/deploy.sh` packages
   HEAD and runs `docker compose up -d --build`, which now builds the new `lecg`
   service alongside `lec`. (The instrument's pinning change rides in the same
   tree -- behavior-neutral; `rubric_version` unchanged.)
   - Internal smoke: `ssh deploy@138.197.111.66 "curl -fsS http://127.0.0.1:8014/health"`
     -> `{"status":"ok","service":"lecg","constitution_version":"1373218dda6e"}`.
3. **nginx block + cert (host proxy = le-nginx).**
   - Copy the block: `scp deploy/nginx-lecg.conf deploy@138.197.111.66:/tmp/lecg.conf`
     then on the server `sudo cp /tmp/lecg.conf /root/proxy/nginx/conf.d/lecg.conf`
     (mirror how `lec.conf` was installed).
   - Issue the cert: `docker exec le-certbot certbot certonly --webroot -w /var/www/certbot -d lecg.libraengine.com`.
   - Reload: `docker exec le-nginx nginx -t && docker exec le-nginx nginx -s reload`.
4. **Verify public.**
   - `curl -fsS https://lecg.libraengine.com/health`
   - `curl -fsS https://lecg.libraengine.com/api/constitution/version`
     -> `{"version":"1373218dda6e",...}`
   - `curl -fsS https://lecg.libraengine.com/api/constitution | head -c 200`

## Steady-state redeploys

`bash deploy/deploy.sh` (push to GitHub first if the server pulls; current flow
ships via `git archive | scp | tar`). It rebuilds + restarts both `lec` and
`lecg` and smoke-tests `lec`'s `/health`.

## The tenets view (LE site)

The public `/tenets/` page on `libraengine.com` renders the generated
`tenets/tenets-data.js`. Regenerate it from the canonical constitution with
`python -m governance.lecg_build_tenets_view` (run in `backend/`) after any
ratified amendment, then deploy the LE site. (Later: switch the page to fetch
`https://lecg.libraengine.com/api/constitution` live instead of the static file.)

## Notes

- The `lec` instrument now imports the governance package (the constitution pin).
  The image already copies `governance/`, so the import resolves in the `lec`
  container; it is fail-soft regardless.
- No `lecg` env today. Cut 2 introduces `LECG_DATABASE_URL` + the shared-Clerk
  vars (CLERK_*) + admin auth, all forwarded explicitly in `docker-compose.yml`
  like `lec`'s block.
