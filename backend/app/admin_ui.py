"""Self-contained HTML for the LEC admin console.

Structure replicates the Rising Compass admin (sidebar shell + grouped nav +
stat cards + data tables + fixed logout), recolored to Libra Engine corporate
branding: dark ground, warm bone ink, a single gold accent, NO rainbow. Type is
serif + mono -- Cormorant SC (tracked small-caps) for the brand/nav/headings,
Cardo for prose, a monospace stack for all data (numbers, tokens, tables).

No template engine and no static mount (LEC stays dependency-lean): pages are
composed here as strings and the data rides in as JSON from /admin/api/summary.
__LOGIN_ACTION__ in LOGIN_HTML is replaced with the obscured login POST path at
serve time (the token lives only in the URL, never hard-coded here).
"""

# --- Shared chrome ---------------------------------------------------------

_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cardo:ital,wght@0,400;0,700;1,400&family=Cormorant+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

_BASE_CSS = """
<style>
  :root {
    --bg: #0a0a12; --panel: #0e0e18; --panel-strong: #15151f;
    --border: #353049; --border-soft: #242235;
    --text: #e2ddd0; --text-bright: #f5f1e6; --text-dim: #b3aa96; --text-hint: #857f6e;
    --gold: #d2b06a; --gold-strong: #e6cd92; --gold-dim: #4a3f28;
    --red: #cf6a4e;
    --mono: ui-monospace, 'SF Mono', 'Cascadia Mono', Menlo, Consolas, monospace;
    --serif: 'Cardo', Georgia, 'Times New Roman', serif;
    --display: 'Cormorant SC', serif;
    --sidebar-w: 230px; --sidebar-rail: 46px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--serif); background: var(--bg); color: var(--text);
    -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
  a { color: inherit; }
  h1 { font-family: var(--display); font-weight: 600; color: var(--gold);
    font-size: 1.7rem; letter-spacing: .06em; margin-bottom: 1.2rem; }
  .sc { font-family: var(--display); }
  .mono { font-family: var(--mono); }

  /* ---- Sidebar shell ---- */
  .admin-shell { display: flex; min-height: 100vh; }
  .admin-sidebar { width: var(--sidebar-w); flex-shrink: 0; background: var(--panel);
    border-right: 1px solid var(--border); padding: 1rem 0; position: sticky; top: 0;
    height: 100vh; overflow-y: auto; transition: width .25s ease; }
  .admin-sidebar-brand { font-family: var(--display); padding: .35rem 1.1rem 1rem 3rem;
    font-size: 1.05rem; font-weight: 600; color: var(--text-bright); letter-spacing: .12em;
    border-bottom: 1px solid var(--border-soft); margin-bottom: .75rem; min-height: 34px; display: flex; align-items: center; }
  .admin-nav-group { margin: 1.1rem 0 .25rem; }
  .admin-nav-group:first-of-type { margin-top: 0; }
  .admin-nav-group-label { font-family: var(--display); padding: .35rem 1.1rem; font-size: .74rem;
    font-weight: 600; color: var(--text-hint); text-transform: uppercase; letter-spacing: .16em; }
  .admin-nav-item { display: block; padding: .5rem 1.1rem; font-family: var(--display); font-size: 1rem;
    letter-spacing: .04em; color: var(--text-dim); text-decoration: none; border-left: 2px solid transparent; }
  .admin-nav-item:hover { color: var(--text-bright); background: rgba(210,176,106,.05); }
  .admin-nav-item.active { color: var(--gold); background: var(--panel-strong); border-left-color: var(--gold); }
  .admin-main { flex: 1; min-width: 0; padding: 1.6rem 2rem 3rem; max-width: 1200px; }

  .sidebar-toggle { position: fixed; top: .6rem; left: .6rem; z-index: 1100; width: 32px; height: 32px;
    padding: 0; background: var(--panel); border: 1px solid var(--border); color: var(--text-dim);
    border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .sidebar-toggle:hover { color: var(--gold); border-color: var(--gold-dim); }
  body.sidebar-collapsed .admin-sidebar { width: var(--sidebar-rail); overflow: hidden; }
  body.sidebar-collapsed .admin-sidebar-brand, body.sidebar-collapsed .admin-nav-group { opacity: 0; pointer-events: none; transition: opacity .12s ease; }
  @media (max-width: 800px) {
    .admin-sidebar { position: fixed; z-index: 1000; box-shadow: 4px 0 16px rgba(0,0,0,.5); }
    .admin-main { padding: 2.6rem 1rem 2rem calc(var(--sidebar-rail) + .8rem); }
    body:not(.sidebar-open) .admin-sidebar { width: var(--sidebar-rail); overflow: hidden; }
    body:not(.sidebar-open) .admin-sidebar-brand, body:not(.sidebar-open) .admin-nav-group { opacity: 0; pointer-events: none; }
    body.sidebar-open .admin-sidebar { width: var(--sidebar-w); }
  }

  .logout-btn { position: fixed; top: 1rem; right: 1rem; z-index: 100; padding: .35rem .9rem;
    font-family: var(--display); font-size: .82rem; letter-spacing: .08em; background: var(--panel);
    border: 1px solid var(--border); color: var(--text-dim); border-radius: 4px; cursor: pointer; }
  .logout-btn:hover { border-color: var(--gold); color: var(--gold); }

  /* ---- Content primitives (mirrors RC admin, recolored) ---- */
  .topmeta { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; margin: -.4rem 0 1.4rem; }
  .chip { font-family: var(--mono); font-size: .74rem; padding: .25rem .6rem; border-radius: 3px;
    background: var(--panel); border: 1px solid var(--border); color: var(--text-dim); text-decoration: none; }
  .chip.gold { color: var(--gold); border-color: var(--gold-dim); }
  .chip .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--gold);
    box-shadow: 0 0 7px var(--gold); margin-right: 6px; vertical-align: middle; }

  .section-title { font-family: var(--display); color: var(--text-dim); font-size: .95rem; letter-spacing: .14em;
    text-transform: uppercase; margin: 1.6rem 0 .7rem; }
  .section-title:first-child { margin-top: 0; }
  .card { background: var(--panel); border: 1px solid var(--border-soft); border-radius: 6px; padding: 1.1rem 1.25rem; }

  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: .9rem; margin-bottom: 1.4rem; }
  .stat-card { background: var(--panel); border: 1px solid var(--border-soft); border-radius: 6px; padding: 1rem 1.1rem; }
  .stat-card .val { font-family: var(--mono); font-size: 1.55rem; font-weight: 700; color: var(--gold); letter-spacing: -.01em; }
  .stat-card .label { font-family: var(--display); font-size: .76rem; letter-spacing: .12em; text-transform: uppercase; color: var(--text-dim); margin-top: .35rem; }

  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-bottom: 1.4rem; }
  @media (max-width: 760px) { .grid2 { grid-template-columns: 1fr; } }

  /* data tables (mono) */
  table.data { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: .8rem; }
  table.data th { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--border);
    color: var(--text-hint); font-weight: 600; font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; }
  table.data td { padding: .5rem .6rem; border-bottom: 1px solid var(--border-soft); color: var(--text); vertical-align: top; }
  table.data tr:last-child td { border-bottom: 0; }
  table.data td.num { text-align: right; color: var(--gold); }
  table.data td.dim { color: var(--text-dim); }
  table.data .title { font-family: var(--serif); font-size: .95rem; color: var(--text-bright); }
  .empty { color: var(--text-dim); font-style: italic; padding: .7rem 0; }
  .bad { color: var(--red); }

  /* rubric ladder (monochrome -- no RC rainbow) */
  .ladder { display: flex; flex-wrap: wrap; align-items: baseline; }
  .ladder .t { font-family: var(--display); font-size: 1.15rem; letter-spacing: .08em; color: var(--text-bright); }
  .ladder .sep { color: var(--border); margin: 0 .7rem; }
  .rubric-meta { font-family: var(--mono); margin-top: .9rem; color: var(--text-dim); font-size: .82rem; }
  .rubric-meta b { color: var(--gold); font-weight: 700; }
  .rubric-types { font-family: var(--mono); margin-top: .4rem; color: var(--text-hint); font-size: .78rem; }

  /* spend sparkline (gold) */
  .spark { display: flex; align-items: flex-end; gap: 2px; height: 80px; margin-top: .3rem; }
  .spark .b { flex: 1; background: var(--border); border-radius: 1px; min-height: 2px; }
  .spark .b.hot { background: var(--gold); opacity: .85; }
  .spark-cap { font-family: var(--mono); font-size: .72rem; color: var(--text-hint); margin-top: .5rem; }

  /* pipeline */
  .lane-head { font-family: var(--display); font-size: .9rem; letter-spacing: .14em; text-transform: uppercase;
    color: var(--text-dim); margin: 1.4rem 0 .7rem; display: flex; gap: .7rem; align-items: baseline; }
  .lane-head .file { font-family: var(--mono); color: var(--text-hint); letter-spacing: 0; text-transform: none; font-size: .7rem; }
  .stage { position: relative; background: var(--panel); border: 1px solid var(--border-soft); border-radius: 6px; padding: .85rem 1.05rem; margin-bottom: .5rem; }
  .stage .t { font-family: var(--serif); color: var(--text-bright); font-size: 1.05rem; }
  .stage .t .n { font-family: var(--mono); color: var(--gold); font-weight: 700; margin-right: .5rem; }
  .stage .sub { font-family: var(--mono); font-size: .74rem; color: var(--text-hint); margin-left: .4rem; }
  .stage .d { color: var(--text-dim); font-size: .9rem; margin-top: .35rem; }
  .stage .io { font-family: var(--mono); font-size: .74rem; color: var(--text-dim); background: var(--bg);
    border: 1px solid var(--border); border-radius: 4px; padding: .55rem .7rem; margin-top: .6rem; overflow-x: auto; white-space: pre-wrap; }
  .tag { float: right; font-family: var(--display); font-size: .72rem; letter-spacing: .12em; padding: .15rem .55rem; border-radius: 3px; }
  .tag.opus { color: var(--gold); border: 1px solid var(--gold-dim); }
  .tag.auth, .tag.meter { color: var(--text-dim); border: 1px solid var(--border); }
  .tag.meter { margin-left: .4rem; }
  .branch { margin: 0 0 .5rem 1.4rem; font-family: var(--mono); font-size: .78rem; color: var(--gold);
    border-left: 1px solid var(--gold-dim); padding: .2rem 0 .2rem .8rem; }
  .branch b { color: var(--gold-strong); }
  .arrow { text-align: center; color: var(--border); font-size: 1rem; margin: -.1rem 0 .4rem; }
  .stage.opusrow { border-color: var(--gold-dim); }
  .stage.boundary::after { content: 'Compass boundary'; position: absolute; right: 12px; bottom: -9px;
    font-family: var(--display); font-size: .72rem; letter-spacing: .1em; color: var(--gold); background: var(--bg); padding: 0 7px; }
  .lane.downstream .stage { background: var(--panel-strong); border-style: dashed; }
  .lane.downstream .lane-head { color: var(--text-hint); }
  .legend { margin-top: 1.6rem; color: var(--text-dim); font-size: .82rem; display: flex; gap: 1.4rem; flex-wrap: wrap; font-style: italic; }
  .legend b { color: var(--gold); font-weight: 700; font-style: normal; }
</style>
"""

_SHELL_JS = """
<script>
function doLogout() {
  fetch('/admin/logout', { method: 'POST' }).finally(() => { window.location = '/'; });
}
(function () {
  const KEY = 'lec_admin_sidebar_collapsed';
  const btn = document.getElementById('sidebarToggle');
  if (!btn) return;
  const mq = window.matchMedia('(max-width: 800px)');
  function apply() {
    if (mq.matches) {
      document.body.classList.toggle('sidebar-open', sessionStorage.getItem('lec_sb_mobile') === '1');
      document.body.classList.remove('sidebar-collapsed');
    } else {
      document.body.classList.toggle('sidebar-collapsed', localStorage.getItem(KEY) === '1');
      document.body.classList.remove('sidebar-open');
    }
  }
  btn.addEventListener('click', () => {
    if (mq.matches) sessionStorage.setItem('lec_sb_mobile', sessionStorage.getItem('lec_sb_mobile') === '1' ? '0' : '1');
    else localStorage.setItem(KEY, localStorage.getItem(KEY) === '1' ? '0' : '1');
    apply();
  });
  mq.addEventListener('change', apply); apply();
})();
const $ = (id) => document.getElementById(id);
const money = (n) => '$' + (n || 0).toFixed(n >= 100 ? 0 : 2);
const tok = (n) => !n ? '0' : n >= 1000 ? (n/1000).toFixed(1).replace(/\\.0$/,'') + 'k' : '' + n;
const ago = (iso) => { if (!iso) return ''; const s=(Date.now()-new Date(iso+'Z').getTime())/1000;
  if (s<60) return Math.floor(s)+'s ago'; if (s<3600) return Math.floor(s/60)+'m ago';
  if (s<86400) return Math.floor(s/3600)+'h ago'; return Math.floor(s/86400)+'d ago'; };
function esc(s){ return (s==null?'':''+s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
</script>
"""


def _sidebar(active: str) -> str:
    def cls(key):
        return "admin-nav-item active" if active == key else "admin-nav-item"
    return (
        '<aside class="admin-sidebar" id="adminSidebar">'
        '<div class="admin-sidebar-brand">Libra Engine Compass</div>'
        '<div class="admin-nav-group">'
        '<div class="admin-nav-group-label">Overview</div>'
        f'<a class="{cls("console")}" href="/admin">Console</a>'
        '</div>'
        '<div class="admin-nav-group">'
        '<div class="admin-nav-group-label">Calibrator</div>'
        f'<a class="{cls("pipeline")}" href="/admin/pipeline">Pipeline</a>'
        '</div>'
        '</aside>'
    )


_TOGGLE = (
    '<button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar" type="button">'
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
    '<line x1="3" y1="4" x2="13" y2="4"/><line x1="3" y1="8" x2="13" y2="8"/><line x1="3" y1="12" x2="13" y2="12"/>'
    '</svg></button>'
)


def _page(title: str, active: str, body: str, page_script: str) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<meta name=\"robots\" content=\"noindex, nofollow\">"
        f"<title>{title} - Libra Engine Compass</title>"
        + _FONTS + _BASE_CSS +
        "</head><body>"
        + _TOGGLE +
        '<button class="logout-btn" onclick="doLogout()">Sign out</button>'
        '<div class="admin-shell">'
        + _sidebar(active) +
        '<main class="admin-main">'
        + body +
        "</main></div>"
        + _SHELL_JS + page_script +
        "</body></html>"
    )


# --- Login (standalone, no shell) ------------------------------------------

LOGIN_HTML = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    "<meta name=\"robots\" content=\"noindex, nofollow\">"
    "<title>Libra Engine Compass</title>"
    + _FONTS + _BASE_CSS +
    "<style>"
    "  body { display: grid; place-items: center; min-height: 100vh; }"
    "  .login-box { width: 360px; max-width: 90vw; background: var(--panel); border: 1px solid var(--border);"
    "    border-radius: 8px; padding: 2.4rem 2rem; }"
    "  .login-box h2 { font-family: var(--display); font-size: 1.4rem; line-height: 1.15; color: var(--text-bright); letter-spacing: .1em; }"
    "  .login-box .rule { height: 1px; background: linear-gradient(90deg, var(--gold), transparent); margin: .9rem 0 1rem; }"
    "  .login-box p { font-family: var(--serif); font-style: italic; color: var(--text-dim); margin-bottom: 1.6rem; }"
    "  label { display: block; font-family: var(--display); font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; color: var(--text-dim); margin-bottom: .4rem; }"
    "  input { width: 100%; padding: .65rem .75rem; margin-bottom: 1rem; background: var(--panel-strong); color: var(--text-bright);"
    "    border: 1px solid var(--border); border-radius: 4px; font-family: var(--serif); font-size: 1rem; }"
    "  input:focus { outline: none; border-color: var(--gold); box-shadow: 0 0 0 3px rgba(210,176,106,.12); }"
    "  button { width: 100%; margin-top: .3rem; padding: .7rem; font-family: var(--display); font-size: 1rem; letter-spacing: .14em;"
    "    text-transform: uppercase; background: transparent; color: var(--gold); border: 1px solid var(--gold); border-radius: 4px; cursor: pointer; }"
    "  button:hover { background: var(--gold); color: var(--bg); }"
    "  .err { color: var(--red); font-size: .85rem; margin-top: .9rem; min-height: 18px; }"
    "</style></head><body>"
    "<form class=\"login-box\" id=\"f\">"
    "<h2 class=\"sc\">Libra Engine<br>Compass</h2><div class=\"rule\"></div>"
    "<p>Admin console</p>"
    "<label for=\"user\">Username</label>"
    "<input id=\"user\" type=\"text\" autocomplete=\"username\" autofocus>"
    "<label for=\"pw\">Password</label>"
    "<input id=\"pw\" type=\"password\" autocomplete=\"current-password\">"
    "<button type=\"submit\">Enter</button>"
    "<div class=\"err\" id=\"err\"></div>"
    "</form><script>"
    "const f=document.getElementById('f'),err=document.getElementById('err');"
    "f.addEventListener('submit',async(e)=>{e.preventDefault();err.textContent='';"
    "const r=await fetch('__LOGIN_ACTION__',{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({username:document.getElementById('user').value,password:document.getElementById('pw').value})});"
    "if(r.ok){const d=await r.json();window.location=d.redirect||'/admin';}"
    "else{err.textContent=r.status===401?'Wrong username or password.':'Login unavailable.';}});"
    "</script></body></html>"
)


# --- Console (dashboard) ---------------------------------------------------

_CONSOLE_BODY = (
    "<h1>Console</h1>"
    '<div class="topmeta">'
    '<span class="chip" id="health"><span class="dot"></span>operational</span>'
    '<span class="chip" id="rubver">rubric ...</span>'
    '<span class="chip" id="model">...</span>'
    '<span class="chip" id="updated">...</span>'
    '</div>'
    '<h2 class="section-title">The rubric</h2>'
    '<div class="card" style="margin-bottom:1.4rem">'
    '<div class="ladder" id="ladder"></div>'
    '<div class="rubric-meta" id="rubricmeta"></div>'
    '<div class="rubric-types" id="types"></div>'
    '</div>'
    '<div class="stats-grid" id="stats"></div>'
    '<div class="grid2">'
    '<div class="card"><h2 class="section-title" style="margin-top:0">Calibration spend</h2>'
    '<div class="spark" id="spark"></div><div class="spark-cap" id="sparkcap"></div></div>'
    '<div class="card"><h2 class="section-title" style="margin-top:0">Recent reads</h2><div id="recent"></div></div>'
    '</div>'
    '<h2 class="section-title">Clients &amp; keys</h2>'
    '<div class="card" id="clients"></div>'
)

_CONSOLE_JS = """
<script>
function render(d) {
  $('rubver').textContent = 'rubric ' + d.rubric.version;
  $('model').textContent = d.service.model + ' . ' + d.service.db_dialect;
  $('updated').textContent = 'refreshed ' + ago(d.service.generated_at);

  $('ladder').innerHTML = d.rubric.tiers.map(t => `<span class="t">${esc(t.label)}</span>`).join('<span class="sep">/</span>');
  $('rubricmeta').innerHTML = `version <b>${d.rubric.version}</b> &middot; <b>${d.rubric.tiers.length}</b> tiers `
    + `&middot; <b>${d.rubric.tenet_count ?? '?'}</b> tenets &middot; <b>${d.rubric.artifact_types.length}</b> artifact types`;
  $('types').textContent = 'reads: ' + d.rubric.artifact_types.map(t => t.key).join('  ');

  const s = d.spend;
  const cards = [
    ['Spend, all-time', money(s.total_cost_usd)],
    ['Calibrations', s.total_calls + (s.failed_calls ? ` (${s.failed_calls} failed)` : '')],
    ['Avg per read', money(s.avg_cost_usd)],
    ['Tokens in / out', tok(s.input_tokens) + ' / ' + tok(s.output_tokens)],
  ];
  $('stats').innerHTML = cards.map(([l,n]) => `<div class="stat-card"><div class="val">${n}</div><div class="label">${l}</div></div>`).join('');

  const max = Math.max(...s.series.map(p => p.cost), 0.0001);
  $('spark').innerHTML = s.series.map(p => `<div class="${p.cost>0?'b hot':'b'}" style="height:${Math.max(Math.round(p.cost/max*100),2)}%" title="${p.date}: ${money(p.cost)}"></div>`).join('');
  $('sparkcap').textContent = `${s.window_days} days . ${money(s.window_cost_usd)} over ${s.window_calls} reads`;

  $('recent').innerHTML = d.recent.length
    ? '<table class="data"><thead><tr><th>Artifact</th><th>Cost</th><th>When</th></tr></thead><tbody>'
      + d.recent.map(r => {
          const by = r.artist ? `<div class="dim" style="font-size:.72rem">${esc(r.artist)}${r.duration_ms?' . '+(r.duration_ms/1000).toFixed(0)+'s':''}</div>` : '';
          const dot = r.ok ? '' : '<span class="bad">! </span>';
          return `<tr><td><span class="title">${dot}${esc(r.title||'(untitled)')}</span>${by}</td>`
            + `<td class="num">${money(r.cost_usd)}</td><td class="dim">${ago(r.ts)}</td></tr>`;
        }).join('') + '</tbody></table>'
    : '<div class="empty">No reads logged yet.</div>';

  if (!d.clients.length) {
    $('clients').innerHTML = '<div class="empty">No clients yet. Keys for Rising Compass and Lyric Transformer are issued here at deploy.</div>';
  } else {
    const rows = [];
    d.clients.forEach(c => {
      const ks = c.keys.length ? c.keys : [null];
      ks.forEach(k => rows.push(
        `<tr><td><span class="title">${esc(c.name)}</span><div class="dim" style="font-size:.72rem">${esc(c.slug)}</div></td>`
        + `<td>${k && k.revoked ? '<span class="bad">revoked</span>' : esc(c.status)}</td>`
        + `<td class="dim">${k ? esc(k.prefix||'')+'...' : '-'}</td>`
        + `<td class="dim">${k && k.last_used_at ? ago(k.last_used_at) : (k?'never':'-')}</td></tr>`));
    });
    $('clients').innerHTML = '<table class="data"><thead><tr><th>Client</th><th>Status</th><th>Key</th><th>Last used</th></tr></thead><tbody>' + rows.join('') + '</tbody></table>';
  }
}
async function load() {
  try {
    const r = await fetch('/admin/api/summary', { headers: { 'Accept': 'application/json' } });
    if (r.status === 404) { window.location = '/'; return; }
    if (!r.ok) return; render(await r.json());
  } catch (e) {}
}
load(); setInterval(load, 20000);
</script>
"""

DASHBOARD_HTML = _page("Console", "console", _CONSOLE_BODY, _CONSOLE_JS)


# --- Pipeline (data-flow map) ----------------------------------------------

_PIPELINE_BODY = (
    "<h1>Calibrator Pipeline</h1>"
    '<div class="topmeta">'
    '<span class="chip" id="rubver">rubric ...</span>'
    '<span class="chip" id="model">...</span>'
    '</div>'
    '<p style="color:var(--text-dim);font-style:italic;margin-bottom:1.4rem">The path one artifact travels after a consumer posts it to /api/score. The Compass runs the scoring half only; enrichment and persistence happen on the consumer side, shown dashed at the end.</p>'
    '<div id="flow"></div>'
    '<div class="legend">'
    '<span><b>OPUS</b> a Claude call, metered to claude_api_usage</span>'
    '<span><b>gold rule</b> a branch that returns early</span>'
    '<span><b>dashed</b> outside the Compass (consumer side)</span>'
    '</div>'
)

_PIPELINE_JS = """
<script>
const FLOW = [
  { lane: 'Consumer push', kind: 'consumer', stages: [
    { title: 'Rising Compass / Lyric Transformer / Creative Charger',
      d: 'A consumer pushes one artifact to be scored against the rubric.',
      io: 'POST /api/score  { type, text, title?, artist?, intent?, use_precedents? }   +  header X-Api-Key' },
  ]},
  { lane: 'Service edge', file: 'routers/score.py + deps.py', stages: [
    { n: 1, title: 'Service-key auth', sub: 'deps.require_api_key', tag: 'auth', dyn: 'auth',
      d: 'X-Api-Key matched against api_client_keys (non-revoked); stamps last_used_at.',
      branch: '<b>401</b> on missing or unknown key' },
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
      d: 'System prompt = the rubric assembled from tenets/core.json + precedents.json; the user prompt is framed by artifact_type. Few-shot examples disabled (the tenets and precedent table carry the anchoring).' },
    { n: 6, title: 'Read v3 - the calibration', sub: '_read_v3 -> tracked_create_async', tag: 'opus', opus: true,
      d: 'ONE Opus call (temperature 0, max 3500 tokens). Split reasoning from JSON, run the soft guards (mandatory Contamination line + charge_summary framing), parse and validate_components. A usable read ships immediately; otherwise ONE corrective retry; if it still never validates, returns None.',
      branch: 'None &rarr; <b>_fallback_result</b> (needs human review, returns)' },
    { n: 7, title: 'Compose the charge', sub: 'charge_composition.compose',
      d: 'The model emits components only; the SERVER derives charge_value, tier, governing_axis, contaminated, and gut_divergence. The verdict is composed here, not by the model.' },
    { n: 8, title: 'Escalation gate', sub: 'evaluate_escalation', dyn: 'escalation',
      d: 'Triggers are ALWAYS recorded on the run. A second full re-pass fires only when re-pass is enabled AND the escalation model differs from the base model.' },
    { n: 9, title: 'Contamination cross-check',
      d: 'The derived contamination flag wins; a mismatch against the model own flag is recorded as a signal, not silently dropped.' },
    { n: 10, title: 'Assemble the package',
      d: 'Charge package + the v3 components (visceral_charge, route, harm, transcendence, center, vernier, precedent_refs, ...) + the agent reasoning, into one dict.' },
    { n: 11, title: 'Verbatim-quote guard', sub: 'lyric_quote_guard', boundary: true,
      d: 'Clears contamination_note / dogma_note if either reproduces a verbatim run of six or more lyric words. The flags stay set. This is where the Compass stops.' },
  ]},
  { lane: 'Response', file: 'routers/score.py', stages: [
    { n: 12, title: 'Map to the response',
      d: 'color None returns { status: unscorable, reason }. Otherwise the scored package.',
      io: '{ status:"scored", tier, color_key, charge_value, confidence, visceral_charge,\\n  charge_summary, contaminated, contamination_note, dogma_*, precedent_refs,\\n  rubric_version, components{ route, harm, transcendence, center, vernier, ... } }' },
  ]},
  { lane: 'Downstream - consumer side, outside the Compass', kind: 'downstream', stages: [
    { title: 'Rising Compass: enrichment + persistence',
      d: '_ensure_generation (listener prose, ether tags, societal prose), then persist songs + calibration_runs. RC-side only; the Compass returns these prose fields null.' },
    { title: 'Lyric Transformer: the Mirror',
      d: 'Consumes visceral_charge + listener prose. Listener-prose ownership is the open gate: the Compass returns it null today, so the client either enriches or the Compass starts generating it.' },
    { title: 'Creative Charger',
      d: 'Pushes the non-lyric artifact types (poem / essay / script / message / email / article) through the same /api/score.' },
  ]},
];
function stageHTML(s) {
  let tag = '';
  if (s.tag === 'opus') tag = '<span class="tag opus">OPUS</span><span class="tag meter">metered</span>';
  else if (s.tag === 'auth') tag = '<span class="tag auth">AUTH</span>';
  const num = s.n != null ? `<span class="n">${s.n}</span>` : '';
  const sub = s.sub ? `<span class="sub">${s.sub}</span>` : '';
  const io = s.io ? `<div class="io">${s.io.replace(/</g,'&lt;').replace(/\\n/g,'<br>')}</div>` : '';
  const cls = 'stage' + (s.opus ? ' opusrow' : '') + (s.boundary ? ' boundary' : '');
  const dyn = s.dyn ? ` <span class="sub" id="dyn-${s.dyn}"></span>` : '';
  return `<div class="${cls}">${tag}<div class="t">${num}${s.title}${sub}${dyn}</div><div class="d">${s.d}</div>${io}</div>`
       + (s.branch ? `<div class="branch">${s.branch}</div>` : '');
}
function laneHTML(l, i) {
  const head = `<div class="lane-head">${l.lane}${l.file ? `<span class="file">${l.file}</span>` : ''}</div>`;
  const body = l.stages.map(stageHTML).join('<div class="arrow">&darr;</div>');
  return `<div class="lane ${l.kind || ''}">${head}${body}</div>` + (i < FLOW.length - 1 ? '<div class="arrow">&darr;</div>' : '');
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
    const a = $('dyn-auth'); if (a) a.textContent = d.service.auth_required ? '(enforced)' : '(open locally: auth_required=false)';
    const e = $('dyn-escalation'); if (e) e.textContent = d.service.escalation_repass_enabled && d.service.escalation_model !== d.service.model
      ? `(re-pass ON -> ${d.service.escalation_model})` : '(re-pass OFF -> logs triggers only)';
  } catch (e) {}
}
overlay();
</script>
"""

PIPELINE_HTML = _page("Pipeline", "pipeline", _PIPELINE_BODY, _PIPELINE_JS)
