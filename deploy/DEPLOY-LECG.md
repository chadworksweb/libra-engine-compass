# LECG -- governance venue deploy (lecg.libraengine.com)

> **STATUS: CUT 2 DEPLOYED DARK + LIVE (2026-06-20)** at `lecg.libraengine.com` (commit
> `4e9e2b9`). Own governance DB provisioned, `LECG_*` env set, nginx block re-added + dormant
> Cut-1 cert reused; `/health` ok, read surfaces + tenets live, write surfaces gated 503
> (Clerk Pro pending). The recipe below is what was run. The `lecg` venue app
> is built (Motion Desk + Deliberation Chamber + amendment pipeline + the
> ratification write-back), the `lecg` service is re-added to
> `docker-compose.yml`, and this nginx block exists. It now has its OWN
> governance DB + the shared-Clerk + admin env (no longer read-only). The
> `lecg.libraengine.com` DNS `A` record + cert (issued dormant in Cut 1) are
> reused. Deploy is GATED: the write surfaces are inert until Clerk Pro wires the
> shared-identity satellite, but the venue + its read surfaces + admin can deploy
> dark first. This doc is the deploy recipe.

> The Libra Engine Compass GOVERNANCE venue (the `lecg-` app) is a second
> container beside the `lec-` instrument on le-projects-01, on its own subdomain.

Topology mirrors `lec` (see `DEPLOY.md`): one container (`lecg-backend`, SAME
image as `lec`, command-overridden to `governance.lecg_main:app` on `:8014`) on
the external `le-proxy` network as alias `lecg`, bound to `127.0.0.1:8014`. The
host proxy `le-nginx` (`/root/proxy/`) serves the domain via
`deploy/nginx-lecg.conf` and proxies to the container. It needs its OWN
governance DB (a dedicated DB on the shared DO cluster) + admin secrets; the
shared-Clerk vars stay UNSET until Clerk Pro (the write surfaces 503 until then,
the read surfaces + admin work). No Anthropic key (the venue never scores).

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
   - The tenets page: open `https://lecg.libraengine.com/tenets/` -> the organ +
     all R1-R15 render; `https://lecg.libraengine.com/` redirects there.

## Steady-state redeploys

`bash deploy/deploy.sh` (push to GitHub first if the server pulls; current flow
ships via `git archive | scp | tar`). It rebuilds + restarts both `lec` and
`lecg` and smoke-tests `lec`'s `/health`.

## The tenets view (served BY lecg)

The tenets are the LEC tenets: they live ON LEC. lecg serves the public
`/tenets/` page itself (static UI in `governance/static/tenets/`) and serves
`/tenets/tenets-data.js` LIVE from the canonical constitution -- there is nothing
to regenerate after an amendment and no separate site to deploy; the page always
reflects the current constitution. (The old static copy on the libraengine.com
site is retired; that page can later redirect to `lecg.libraengine.com/tenets/`.)

## Notes

- The `lec` instrument now imports the governance package (the constitution pin).
  The image already copies `governance/`, so the import resolves in the `lec`
  container; it is fail-soft regardless.
- **`lecg` env (now in `docker-compose.yml`, forwarded explicitly like `lec`'s):**
  - `LECG_DATABASE_URL` -- the venue's OWN governance DB (a dedicated DB on the
    shared DO cluster, DISTINCT from `lec`'s). Provision it before deploy; the app
    runs create_all on startup (the 001 baseline).
  - `LECG_ADMIN_LOGIN_TOKEN` / `LECG_ADMIN_USERNAME` / `LECG_ADMIN_PASSWORD` /
    `LECG_ADMIN_SECRET` -- the admin lifecycle console (all four or it 404s).
  - `LECG_CLERK_JWKS_URL` / `LECG_CLERK_AUTHORIZED_PARTY` / `LECG_CLERK_SECRET_KEY`
    / `LECG_CLERK_VERIFIED_CLAIM` -- the shared Clerk spine. **Leave UNSET until
    Clerk Pro** (the write surfaces 503 while unset; reads + admin work).
  - `LECG_DEV_AUTH` -- MUST stay `false` in prod (the local-only bypass).
  - `LECG_CORS_ALLOW_ORIGINS` -- the read-surface allow-list (LE site / RC).
- **The ratification write-back adopts deliberately (RULED 2026-06-20: materialize +
  git).** A ratified amendment bumps the venue's GOVERNED version but NOT the genesis
  `constitution_version` the `lec` instrument pins. Adopting an edition is a separate,
  gated procedure:
  1. Preview:   `python -m governance.lecg_adopt --dry-run` (or admin `GET /api/admin/edition/preview`).
  2. Materialize: `python -m governance.lecg_adopt --apply` -- bakes the pending amendments
     into `le-baseline/*.json` and stamps them `adopted_at` (so the overlay stops
     re-applying them).
  3. Review the git diff, commit, tag `edition-<new_version>` (git is the edition ledger;
     genesis is the v1 tag).
  4. Redeploy `lec` (`deploy.sh`) so the instrument re-pins the new `constitution_version`.

  Until step 4, `lec` `/health` reports the pin out of sync -- the pending adoption,
  surfaced. The `le-baseline` files hold the CURRENT adopted edition; git history + the
  `edition-*` tags are the per-edition record.
- **Smoke after deploy:** `curl -fsS https://lecg.libraengine.com/health` ->
  `{"status":"ok","service":"lecg","constitution_version":"1373218dda6e",
  "clerk_enabled":false,...}`; `/api/amendments` returns the log;
  `/motion-desk/` renders.
