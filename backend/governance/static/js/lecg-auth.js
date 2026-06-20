/* === LECG auth shim ===

   A tiny, dependency-free helper for the Libra Engine Compass governance
   venue (lecg). It does two jobs:

     1. fetchJSON(path)        -- a thin wrapper over fetch for the public
                                  read calls (motions, arguments, amendments).
                                  Same-origin relative base: the venue serves
                                  /api/* itself.
     2. participationNotice()  -- the deferred-sign-in message shown on any
                                  write action (file a motion, post an
                                  argument). Writes open with shared Libra
                                  Engine sign-in, which is still being wired.

   It probes GET /health once on load and records clerk_enabled / dev_auth so
   this shim can later grow real auth without touching the read views. For now
   it stays read-only: anonymous reads work, writes route to the notice. */

(() => {
  'use strict';

  // Same-origin relative base. The venue serves /api/* on its own host, so a
  // bare path is a same-origin call (mirrors how the read pages fetch).
  const API_BASE = '';

  const NOTICE =
    'Participation (filing motions, posting arguments) opens with shared ' +
    'Libra Engine sign-in, which is being wired. Reading the record stays ' +
    'open to everyone, no account needed.';

  // Populated by the one-time /health probe. Until it resolves these stay
  // false, which is the safe default (writes deferred, reads unaffected).
  const health = {
    ready: false,
    clerkEnabled: false,
    devAuth: false,
  };

  // Probe /health once. Fail-soft: a missing or erroring endpoint just leaves
  // the venue in read-only mode. Nothing here gates the read views.
  let healthPromise = null;
  function probeHealth() {
    if (healthPromise) return healthPromise;
    healthPromise = fetch(`${API_BASE}/health`, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((body) => {
        if (body && typeof body === 'object') {
          health.clerkEnabled = body.clerk_enabled === true;
          health.devAuth = body.dev_auth === true;
        }
        health.ready = true;
        return health;
      })
      .catch(() => {
        health.ready = true;
        return health;
      });
    return healthPromise;
  }

  // Thin JSON fetch for the read calls. Throws on a non-2xx so callers can
  // render a calm error state. No auth header: these are public reads.
  async function fetchJSON(path, options) {
    const resp = await fetch(`${API_BASE}${path}`, options || {});
    if (!resp.ok) {
      const err = new Error(`Request failed (${resp.status})`);
      err.status = resp.status;
      throw err;
    }
    return resp.json();
  }

  function participationNotice() {
    return NOTICE;
  }

  // Kick the probe off immediately so health is known by the time a write
  // action is attempted. Does not block any read.
  probeHealth();

  window.LECGAuth = {
    apiBase: API_BASE,
    fetchJSON,
    participationNotice,
    probeHealth,
    health,
  };
})();
