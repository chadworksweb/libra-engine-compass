"""Self-contained HTML for the LEC admin console. Two pages, no template engine
and no static mount (LEC stays dependency-lean): a login page and the dashboard
shell. The dashboard fetches /admin/api/summary and renders client-side, so the
markup is written once and the data rides in as JSON.

__LOGIN_ACTION__ in LOGIN_HTML is replaced with the obscured login POST path at
serve time (the token lives only in the URL, never hard-coded here).
"""

LOGIN_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Libra Engine Compass</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: grid; place-items: center;
    background: #0a0b10; color: #e7e9f0;
    font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  }
  .card {
    width: 340px; max-width: 90vw; padding: 32px 28px;
    background: #12141c; border: 1px solid #232636; border-radius: 14px;
    box-shadow: 0 20px 60px rgba(0,0,0,.5);
  }
  .spectrum { display: flex; height: 6px; border-radius: 4px; overflow: hidden; margin-bottom: 22px; }
  .spectrum span { flex: 1; }
  h1 { font-size: 16px; letter-spacing: .04em; margin: 0 0 4px; font-weight: 600; }
  p.sub { margin: 0 0 22px; color: #8b8fa3; font-size: 13px; }
  label { display: block; font-size: 12px; color: #8b8fa3; margin-bottom: 6px; letter-spacing: .03em; }
  input {
    width: 100%; padding: 11px 13px; background: #0c0d14; color: #e7e9f0;
    border: 1px solid #2a2e42; border-radius: 9px; font-size: 14px;
  }
  input:focus { outline: none; border-color: #5b6cff; }
  button {
    margin-top: 18px; width: 100%; padding: 11px; border: 0; border-radius: 9px;
    background: #5b6cff; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
  }
  button:hover { background: #6f7dff; }
  .err { margin-top: 14px; color: #ff7a7a; font-size: 13px; min-height: 18px; }
</style>
</head>
<body>
  <form class="card" id="f">
    <div class="spectrum">
      <span style="background:#9933ff"></span><span style="background:#3388ff"></span>
      <span style="background:#33cc55"></span><span style="background:#ffbb33"></span>
      <span style="background:#ff3333"></span>
    </div>
    <h1>LIBRA ENGINE COMPASS</h1>
    <p class="sub">Admin console</p>
    <label for="pw">Password</label>
    <input id="pw" type="password" autocomplete="current-password" autofocus>
    <button type="submit">Enter</button>
    <div class="err" id="err"></div>
  </form>
<script>
  const f = document.getElementById('f'), err = document.getElementById('err');
  f.addEventListener('submit', async (e) => {
    e.preventDefault(); err.textContent = '';
    const r = await fetch('__LOGIN_ACTION__', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ password: document.getElementById('pw').value })
    });
    if (r.ok) { const d = await r.json(); window.location = d.redirect || '/admin'; }
    else { err.textContent = r.status === 401 ? 'Wrong password.' : 'Login unavailable.'; }
  });
</script>
</body>
</html>"""


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>LEC Console</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: #0a0b10; color: #e7e9f0;
    font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  }
  a { color: inherit; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 22px 24px 64px; }
  header { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 22px; }
  header h1 { font-size: 16px; letter-spacing: .06em; margin: 0; font-weight: 700; }
  .chip {
    font-size: 12px; padding: 4px 9px; border-radius: 999px;
    background: #161924; border: 1px solid #262a3c; color: #aab0c6;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; }
  .dot.up { background: #33cc55; box-shadow: 0 0 8px #33cc55aa; }
  .spacer { flex: 1; }
  button.ghost {
    background: transparent; border: 1px solid #2a2e42; color: #aab0c6;
    padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 12px;
  }
  button.ghost:hover { border-color: #3a4060; color: #e7e9f0; }
  .card { background: #11131b; border: 1px solid #20233200; border: 1px solid #1d2030; border-radius: 14px; padding: 18px 20px; }
  .grid { display: grid; gap: 16px; }
  .g2 { grid-template-columns: 1fr 1fr; }
  .g4 { grid-template-columns: repeat(4, 1fr); }
  @media (max-width: 820px) { .g2, .g4 { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 520px) { .g2, .g4 { grid-template-columns: 1fr; } }
  h2.sec { font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: #6f7488; margin: 0 0 12px; }
  /* spectrum */
  .spectrum { display: flex; gap: 6px; }
  .tier { flex: 1; }
  .tier .bar { height: 46px; border-radius: 8px; }
  .tier .lab { margin-top: 8px; font-size: 12px; color: #cfd3e4; }
  .tier .key { font-size: 11px; color: #6f7488; }
  .rubric-meta { margin-top: 16px; color: #8b8fa3; font-size: 13px; }
  .rubric-meta b { color: #e7e9f0; font-weight: 600; }
  /* stat */
  .stat .n { font-size: 26px; font-weight: 700; letter-spacing: -.01em; }
  .stat .l { font-size: 12px; color: #6f7488; margin-top: 2px; }
  /* sparkline */
  .spark { display: flex; align-items: flex-end; gap: 2px; height: 70px; margin-top: 6px; }
  .spark .b { flex: 1; background: #2c3350; border-radius: 2px 2px 0 0; min-height: 2px; }
  .spark .b.hot { background: #5b6cff; }
  /* lists */
  .row { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid #181b27; }
  .row:last-child { border-bottom: 0; }
  .row .ttl { font-weight: 600; }
  .row .meta { color: #6f7488; font-size: 12px; }
  .row .right { margin-left: auto; text-align: right; color: #aab0c6; font-size: 12px; white-space: nowrap; }
  .empty { color: #6f7488; font-size: 13px; padding: 8px 0; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #181b27; font-size: 13px; }
  th { color: #6f7488; font-weight: 600; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .ok { color: #33cc55; } .bad { color: #ff7a7a; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>LIBRA ENGINE COMPASS</h1>
    <span class="chip" id="health"><span class="dot up"></span>up</span>
    <span class="chip" id="rubver">rubric ...</span>
    <span class="chip" id="model">...</span>
    <span class="spacer"></span>
    <span class="chip" id="updated">...</span>
    <a class="chip" href="/admin/pipeline" style="text-decoration:none">Pipeline &rarr;</a>
    <button class="ghost" id="logout">Log out</button>
  </header>

  <section class="card" style="margin-bottom:16px">
    <h2 class="sec">The spectrum</h2>
    <div class="spectrum" id="spectrum"></div>
    <div class="rubric-meta" id="rubricmeta"></div>
  </section>

  <div class="grid g4" id="stats" style="margin-bottom:16px"></div>

  <div class="grid g2" style="margin-bottom:16px">
    <section class="card">
      <h2 class="sec" id="spendhead">Calibration spend (30 days)</h2>
      <div class="spark" id="spark"></div>
    </section>
    <section class="card">
      <h2 class="sec">Recent reads</h2>
      <div id="recent"></div>
    </section>
  </div>

  <section class="card">
    <h2 class="sec">Clients & keys</h2>
    <div id="clients"></div>
  </section>
</div>

<script>
const $ = (id) => document.getElementById(id);
const money = (n) => '$' + (n || 0).toFixed(n >= 100 ? 0 : 2);
const tok = (n) => !n ? '0' : n >= 1000 ? (n/1000).toFixed(1).replace(/\\.0$/,'') + 'k' : '' + n;
const ago = (iso) => {
  if (!iso) return '';
  const s = (Date.now() - new Date(iso + 'Z').getTime()) / 1000;
  if (s < 60) return Math.floor(s) + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  if (s < 86400) return Math.floor(s/3600) + 'h ago';
  return Math.floor(s/86400) + 'd ago';
};

function render(d) {
  $('rubver').textContent = 'rubric ' + d.rubric.version;
  $('model').textContent = d.service.model + '  .  ' + d.service.db_dialect;
  $('updated').textContent = 'refreshed ' + ago(d.service.generated_at);

  // spectrum
  $('spectrum').innerHTML = d.rubric.tiers.map(t =>
    `<div class="tier"><div class="bar" style="background:${t.hex};box-shadow:0 0 22px ${t.hex}55"></div>`
    + `<div class="lab">${t.label}</div><div class="key">${t.key}</div></div>`).join('');
  const types = d.rubric.artifact_types.map(t => t.key).join('  ');
  $('rubricmeta').innerHTML =
    `<b>${d.rubric.tenet_count ?? '?'}</b> tenets across 5 tiers &nbsp;.&nbsp; `
    + `<b>${d.rubric.artifact_types.length}</b> artifact types: ${types} &nbsp;.&nbsp; version <b>${d.rubric.version}</b>`;

  // stats
  const s = d.spend;
  const cards = [
    ['Spend, all-time', money(s.total_cost_usd)],
    ['Calibrations', s.total_calls + (s.failed_calls ? `  (${s.failed_calls} failed)` : '')],
    ['Avg per read', money(s.avg_cost_usd)],
    ['Tokens in / out', tok(s.input_tokens) + ' / ' + tok(s.output_tokens)],
  ];
  $('stats').innerHTML = cards.map(([l, n]) =>
    `<div class="card stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');

  // sparkline
  $('spendhead').textContent = `Calibration spend (${s.window_days} days)  .  ${money(s.window_cost_usd)} . ${s.window_calls} reads`;
  const max = Math.max(...s.series.map(p => p.cost), 0.0001);
  $('spark').innerHTML = s.series.map(p => {
    const h = Math.round((p.cost / max) * 100);
    const cls = p.cost > 0 ? 'b hot' : 'b';
    return `<div class="${cls}" style="height:${Math.max(h,2)}%" title="${p.date}: ${money(p.cost)}"></div>`;
  }).join('');

  // recent
  $('recent').innerHTML = d.recent.length ? d.recent.map(r => {
    const name = r.title || '(untitled)';
    const by = r.artist ? ' . ' + r.artist : '';
    const dot = r.ok ? '' : '<span class="bad">! </span>';
    return `<div class="row"><div><div class="ttl">${dot}${esc(name)}</div>`
      + `<div class="meta">${esc(by.slice(3))} &nbsp;${r.duration_ms ? (r.duration_ms/1000).toFixed(0)+'s' : ''}</div></div>`
      + `<div class="right">${money(r.cost_usd)}<br>${ago(r.ts)}</div></div>`;
  }).join('') : '<div class="empty">No reads logged yet.</div>';

  // clients
  if (!d.clients.length) {
    $('clients').innerHTML = '<div class="empty">No clients yet. Keys for RC / Lyric Transformer get issued here at deploy.</div>';
  } else {
    const rows = [];
    d.clients.forEach(c => {
      if (!c.keys.length) {
        rows.push(`<tr><td>${esc(c.name)}<div class="meta">${esc(c.slug)}</div></td><td>${esc(c.status)}</td><td class="mono">-</td><td>-</td></tr>`);
      }
      c.keys.forEach(k => rows.push(
        `<tr><td>${esc(c.name)}<div class="meta">${esc(c.slug)}</div></td>`
        + `<td>${k.revoked ? '<span class="bad">revoked</span>' : '<span class="ok">'+esc(c.status)+'</span>'}</td>`
        + `<td class="mono">${esc(k.prefix || '')}...</td>`
        + `<td>${k.last_used_at ? ago(k.last_used_at) : 'never'}</td></tr>`));
    });
    $('clients').innerHTML = '<table><thead><tr><th>Client</th><th>Status</th><th>Key</th><th>Last used</th></tr></thead><tbody>'
      + rows.join('') + '</tbody></table>';
  }
}

function esc(s) { return (s == null ? '' : '' + s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

async function load() {
  try {
    const r = await fetch('/admin/api/summary', { headers: { 'Accept': 'application/json' } });
    if (r.status === 404) { window.location = '/'; return; }
    if (!r.ok) return;
    render(await r.json());
  } catch (e) { /* keep last paint */ }
}

$('logout').addEventListener('click', async () => {
  await fetch('/admin/logout', { method: 'POST' });
  window.location = '/';
});

load();
setInterval(load, 20000);
</script>
</body>
</html>"""


PIPELINE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>LEC Pipeline</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #0a0b10; color: #e7e9f0;
    font: 14px/1.55 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
  a { color: inherit; }
  .wrap { max-width: 880px; margin: 0 auto; padding: 22px 24px 80px; }
  header { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 8px; }
  header h1 { font-size: 16px; letter-spacing: .06em; margin: 0; font-weight: 700; }
  .chip { font-size: 12px; padding: 4px 9px; border-radius: 999px; background: #161924;
    border: 1px solid #262a3c; color: #aab0c6; text-decoration: none; }
  .spacer { flex: 1; }
  p.lead { color: #8b8fa3; margin: 4px 0 22px; font-size: 13px; }

  .lane { margin: 0 0 8px; }
  .lane-head { font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
    color: #6f7488; margin: 22px 0 10px; display: flex; gap: 10px; align-items: baseline; }
  .lane-head .file { font-family: ui-monospace, Menlo, monospace; color: #4d5266; letter-spacing: 0; text-transform: none; }

  .stage { position: relative; background: #11131b; border: 1px solid #1d2030;
    border-radius: 12px; padding: 13px 16px; margin: 0 0 8px; }
  .stage .t { font-weight: 650; }
  .stage .t .n { display: inline-block; min-width: 20px; color: #5b6cff; font-weight: 700; }
  .stage .sub { font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: #7f86a0; margin-left: 4px; }
  .stage .d { color: #aab0c6; font-size: 13px; margin-top: 5px; }
  .stage .io { font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: #8b91ad;
    background: #0c0d14; border: 1px solid #1b1e2c; border-radius: 7px; padding: 7px 10px; margin-top: 9px; overflow-x: auto; }
  .tag { float: right; font-size: 10px; letter-spacing: .08em; padding: 3px 8px; border-radius: 999px; font-weight: 700; }
  .tag.opus { background: #2a1f4d; color: #c9b6ff; border: 1px solid #4a3a7a; }
  .tag.auth { background: #18324a; color: #9fd0ff; border: 1px solid #2c5478; }
  .tag.meter { background: #133024; color: #84e6b3; border: 1px solid #245a40; font-size: 10px; margin-left: 6px; }
  .branch { margin: 0 0 8px 22px; font-size: 12px; color: #d8a657;
    border-left: 2px solid #5a4422; padding: 4px 0 4px 12px; }
  .branch b { color: #f0c069; font-weight: 600; }
  .arrow { text-align: center; color: #3a3f55; font-size: 16px; line-height: 1; margin: -2px 0 6px; }
  .stage.opusrow { border-color: #3a2f63; box-shadow: 0 0 0 1px #2a1f4d inset; }
  .stage.boundary::after { content: 'LEC boundary'; position: absolute; right: 14px; bottom: -9px;
    font-size: 10px; letter-spacing: .1em; color: #5b6cff; background: #0a0b10; padding: 0 8px; }
  .lane.downstream .stage { background: #0d0e15; border-style: dashed; border-color: #232737; }
  .lane.downstream .lane-head { color: #565b70; }
  .legend { margin-top: 26px; color: #6f7488; font-size: 12px; display: flex; gap: 18px; flex-wrap: wrap; }
  .legend span b { color: #aab0c6; font-weight: 600; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>CALIBRATOR PIPELINE</h1>
    <a class="chip" href="/admin">&larr; Console</a>
    <span class="spacer"></span>
    <span class="chip" id="rubver">rubric ...</span>
    <span class="chip" id="model">...</span>
  </header>
  <p class="lead">The path one artifact travels after a consumer POSTs it to <code>/api/score</code>. LEC runs the scoring half only; enrichment and persistence happen on the consumer side, shown dashed at the end.</p>
  <div id="flow"></div>
  <div class="legend">
    <span><b>OPUS</b> = a Claude call (metered to claude_api_usage)</span>
    <span><b>amber</b> = a branch that returns early</span>
    <span><b>dashed</b> = outside LEC (consumer side)</span>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);

const FLOW = [
  { lane: 'Consumer push', kind: 'consumer', stages: [
    { title: 'RC / Lyric Transformer / Creative Charger',
      d: 'A consumer pushes one artifact to be scored against the rubric.',
      io: 'POST /api/score  { type, text, title?, artist?, intent?, use_precedents? }   +  header X-Api-Key' },
  ]},
  { lane: 'LEC service edge', file: 'routers/score.py + deps.py', stages: [
    { n: 1, title: 'Service-key auth', sub: 'deps.require_api_key', tag: 'auth', dyn: 'auth',
      d: 'X-Api-Key matched against api_client_keys (non-revoked); stamps last_used_at.',
      branch: '<b>401</b> on missing / unknown key' },
    { n: 2, title: 'Type gate', sub: 'type in ARTIFACT_TYPES',
      d: 'Must be one of lyric / poem / prose_essay / script_dialogue / message / email / article.',
      branch: '<b>422</b> unknown type' },
    { n: 3, title: 'Text gate', sub: 'len(text) >= 20',
      d: 'Blocks empty or trivial input before any model spend.',
      branch: '<b>422</b> text too short' },
  ]},
  { lane: 'Calibrator core', file: 'services/agents/calibrator.py -> calibrate_song_async(db=None, skip_cache=True)', stages: [
    { n: 4, title: 'No-text short-circuit', sub: '_null_result',
      d: 'Empty text returns an explicit null calibration without burning a model call.',
      branch: 'no text &rarr; <b>null result</b> (returns)' },
    { n: 5, title: 'Build the prompt', sub: 'compass_agent_rubric.build_calibration_prompt',
      d: 'System prompt = the rubric assembled from tenets/core.json + precedents.json; the user prompt is framed by artifact_type. Few-shot examples disabled (the tenets + precedent table carry the anchoring).' },
    { n: 6, title: 'Read v3 - the calibration', sub: '_read_v3 -> tracked_create_async', tag: 'opus', opus: true,
      d: 'ONE Opus call (temperature 0, max 3500 tokens). Split reasoning from JSON, run soft guards (mandatory Contamination line + charge_summary framing), parse and validate_components. A usable read ships immediately; otherwise ONE corrective retry; if it still never validates, returns None.',
      branch: 'None &rarr; <b>_fallback_result</b> (needs human review, returns)' },
    { n: 7, title: 'Compose the charge', sub: 'charge_composition.compose',
      d: 'The model emits components only; the SERVER derives charge_value, tier (rubric_color), governing_axis, contaminated, and gut_divergence. The verdict is composed here, not by the model.' },
    { n: 8, title: 'Escalation gate', sub: 'evaluate_escalation', dyn: 'escalation',
      d: 'Triggers are ALWAYS recorded on the run. A second full re-pass fires only when re-pass is enabled AND the escalation model differs from the base model.' },
    { n: 9, title: 'Contamination cross-check',
      d: 'The derived contamination flag wins; a mismatch against the model\\'s own flag is recorded as a signal, not silently dropped.' },
    { n: 10, title: 'Assemble the package',
      d: 'Charge package + the v3 components (visceral_charge, route, harm, transcendence, center, vernier, precedent_refs, ...) + the agent reasoning, into one dict.' },
    { n: 11, title: 'Verbatim-quote guard', sub: 'lyric_quote_guard', boundary: true,
      d: 'Clears contamination_note / dogma_note if either reproduces a verbatim run of >=6 lyric words. The flags stay set. This is where LEC stops.' },
  ]},
  { lane: 'Response', file: 'routers/score.py', stages: [
    { n: 12, title: 'Map to the response',
      d: 'color None returns { status: unscorable, reason }. Otherwise the scored package.',
      io: '{ status:"scored", tier, color_key, charge_value, confidence, visceral_charge,\\n  charge_summary, contaminated, contamination_note, dogma_*, precedent_refs,\\n  rubric_version, components{ route, harm, transcendence, center, vernier, ... } }' },
  ]},
  { lane: 'Downstream - consumer side, outside LEC', kind: 'downstream', stages: [
    { title: 'RC: enrichment + persistence',
      d: '_ensure_generation (listener prose, ether tags, societal prose), then persist songs + calibration_runs. RC-side only; LEC returns these prose fields null.' },
    { title: 'Lyric Transformer: the Mirror',
      d: 'Consumes visceral_charge + listener prose. Listener-prose ownership is the open gate: LEC returns it null today, so the client either enriches or LEC starts generating it.' },
    { title: 'Creative Charger',
      d: 'Pushes the non-lyric artifact_types (poem / essay / script / message / email / article) through the same /api/score.' },
  ]},
];

function stageHTML(s) {
  let tag = '';
  if (s.tag === 'opus') tag = '<span class="tag opus">OPUS</span><span class="tag meter" id="meterflag">metered</span>';
  else if (s.tag === 'auth') tag = '<span class="tag auth" id="authflag">AUTH</span>';
  const num = s.n != null ? `<span class="n">${s.n}</span> ` : '';
  const sub = s.sub ? `<span class="sub">${s.sub}</span>` : '';
  const io = s.io ? `<div class="io">${s.io.replace(/</g,'&lt;').replace(/\\n/g,'<br>')}</div>` : '';
  const cls = 'stage' + (s.opus ? ' opusrow' : '') + (s.boundary ? ' boundary' : '');
  const dyn = s.dyn ? ` <span class="sub" id="dyn-${s.dyn}"></span>` : '';
  return `<div class="${cls}">${tag}<div class="t">${num}${s.title}${sub}${dyn}</div>`
       + `<div class="d">${s.d}</div>${io}</div>`
       + (s.branch ? `<div class="branch">${s.branch}</div>` : '');
}

function laneHTML(l, i) {
  const head = `<div class="lane-head">${l.lane}${l.file ? `<span class="file">${l.file}</span>` : ''}</div>`;
  const body = l.stages.map(stageHTML).join('<div class="arrow">&darr;</div>');
  const arrowBefore = i > 0 ? '<div class="arrow">&darr;</div>' : '';
  return `<div class="lane ${l.kind || ''}">${head}${arrowBefore ? '' : ''}${body}</div>` + (i < FLOW.length - 1 ? '<div class="arrow">&darr;</div>' : '');
}

$('flow').innerHTML = FLOW.map(laneHTML).join('');

async function overlay() {
  try {
    const r = await fetch('/admin/api/summary', { headers: { 'Accept': 'application/json' } });
    if (r.status === 404) { window.location = '/'; return; }
    if (!r.ok) return;
    const d = await r.json();
    $('rubver').textContent = 'rubric ' + d.rubric.version;
    $('model').textContent = d.service.model;
    const auth = $('dyn-auth');
    if (auth) auth.textContent = d.service.auth_required ? '(enforced)' : '(open locally: auth_required=false)';
    const esc = $('dyn-escalation');
    if (esc) esc.textContent = d.service.escalation_repass_enabled && d.service.escalation_model !== d.service.model
      ? `(re-pass ON -> ${d.service.escalation_model})` : '(re-pass OFF -> logs triggers only)';
  } catch (e) { /* static map still stands */ }
}
overlay();
</script>
</body>
</html>"""
