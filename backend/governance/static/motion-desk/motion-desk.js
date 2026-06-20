/* === Motion Desk -- public motion ledger (read-only) ===

   Motions deliberate the framework: tenets, rules, modifiers, methodology.
   This venue renders the public ledger anonymously. Filing a motion is a
   write action, deferred until shared Libra Engine sign-in is wired -- the
   "File a motion" door routes to a calm participation notice instead. */

(() => {
  'use strict';

  const STATUS_COLORS = {
    filed: 'var(--md-status-filed)',
    in_deliberation: 'var(--md-status-in-deliberation)',
    ratified: 'var(--md-status-ratified)',
    covered: 'var(--md-status-covered)',
    rejected: 'var(--md-status-rejected)',
  };
  const TYPE_LABEL = {
    amend_tenet: 'Amend tenet',
    new_tenet: 'New tenet',
    remove_tenet: 'Remove tenet',
    amend_rule: 'Amend rule',
    new_rule: 'New rule',
    remove_rule: 'Remove rule',
    process: 'Process',
  };
  const STATUS_LABEL = {
    filed: 'Filed',
    in_deliberation: 'In deliberation',
    ratified: 'Ratified',
    covered: 'Covered',
    rejected: 'Rejected',
  };

  // ---------- helpers ----------

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  // ---------- participation notice (deferred write) ----------

  function bindParticipation() {
    const door = $('fileMotionDoor');
    const notice = $('participationNotice');
    const body = $('participationNoticeBody');
    if (!door || !notice || !body) return;
    body.textContent = window.LECGAuth.participationNotice();
    door.addEventListener('click', () => {
      notice.hidden = false;
      notice.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  // ---------- public ledger ----------

  let currentStatus = 'open';
  let currentType = 'all';

  function bindRecordFilters() {
    document.querySelectorAll('.md-filter[data-status]').forEach((b) => {
      b.addEventListener('click', () => {
        currentStatus = b.dataset.status;
        document.querySelectorAll('.md-filter[data-status]').forEach((x) => x.classList.toggle('active', x === b));
        loadRecord();
      });
    });
    document.querySelectorAll('.md-filter[data-type]').forEach((b) => {
      b.addEventListener('click', () => {
        currentType = b.dataset.type;
        document.querySelectorAll('.md-filter[data-type]').forEach((x) => x.classList.toggle('active', x === b));
        loadRecord();
      });
    });
  }

  async function loadRecord() {
    const list = $('recordList');
    list.innerHTML = '<p class="md-empty">Loading...</p>';
    const params = new URLSearchParams();
    if (currentStatus !== 'all' && currentStatus !== 'open') params.set('status', currentStatus);
    if (currentType !== 'all') params.set('motion_type', currentType);
    try {
      let items = await window.LECGAuth.fetchJSON(`/api/motions?${params.toString()}`);
      if (currentStatus === 'open') {
        items = items.filter((m) => m.status === 'filed' || m.status === 'in_deliberation');
      }
      renderRecord(items);
    } catch (err) {
      list.innerHTML = `<p class="md-empty">${esc(err.message)}</p>`;
    }
  }

  function renderRecord(items) {
    const list = $('recordList');
    if (!items.length) {
      list.innerHTML = '<p class="md-empty">No motions on the ledger for this filter yet.</p>';
      return;
    }
    list.innerHTML = items.map(renderMotion).join('');
    list.querySelectorAll('.md-motion-expand').forEach((btn) => {
      btn.addEventListener('click', () => {
        const body = btn.previousElementSibling;
        const isOpen = body.classList.toggle('expanded');
        body.classList.toggle('collapsed', !isOpen);
        btn.textContent = isOpen ? 'Collapse' : 'Read full reasoning';
      });
    });
  }

  function renderMotion(m) {
    const color = STATUS_COLORS[m.status] || 'var(--md-rule)';

    let targetBlock = '';
    if (m.target_kind && m.target_ref) {
      targetBlock = `<p class="md-motion-target">Targets <b>${esc(m.target_kind)}</b> <code>${esc(m.target_ref)}</code></p>`;
    } else if (m.motion_type === 'new_tenet') {
      targetBlock = '<p class="md-motion-target"><em>Proposes a new tenet</em></p>';
    } else if (m.motion_type === 'new_rule') {
      targetBlock = '<p class="md-motion-target"><em>Proposes a new rule</em></p>';
    } else if (m.motion_type === 'process') {
      targetBlock = '<p class="md-motion-target"><em>Methodology / morality / process</em></p>';
    }

    const verifiedBadge = m.filed_by_verified
      ? `<span class="md-motion-verified">verified</span>` : '';
    const filerName = m.filed_by_handle
      ? `@${esc(m.filed_by_handle)}`
      : esc(m.filed_by_anon_id || 'unknown');
    const filedDate = m.filed_at
      ? new Date(m.filed_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
      : '';

    const reasoning = (m.reasoning || '').trim();
    const showExpand = reasoning.length > 200 || reasoning.split('\n').length > 3;
    const reasoningCls = showExpand ? 'md-motion-reasoning collapsed' : 'md-motion-reasoning expanded';

    const citationsBlock = (m.citations && m.citations.length)
      ? `<div class="md-motion-citations">
           <span class="label">Citations</span>
           ${m.citations.map((u) => `<div><a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a></div>`).join('')}
         </div>`
      : '';

    const resolutionBlock = m.resolution_summary
      ? `<div class="md-motion-resolution" style="--md-status-color: ${color};">
           <span class="label">Resolution &middot; ${m.resolved_at ? new Date(m.resolved_at).toLocaleDateString() : ''}</span>
           <p>${esc(m.resolution_summary)}</p>
         </div>`
      : '';

    // Filed motions don't get a chamber link -- the chamber isn't open until
    // a motion moves into deliberation. The link stays after resolution so
    // the deliberation record remains public.
    const showChamberLink = m.status !== 'filed';
    const chamberLinkLabel = m.status === 'in_deliberation'
      ? 'Open the Deliberation Chamber'
      : 'See the deliberation record';
    const chamberLink = showChamberLink
      ? `<a class="md-motion-chamber-link" href="/motion-desk/deliberation-chamber/${m.id}/">${chamberLinkLabel} &rarr;</a>`
      : '';

    return `
      <article class="md-motion" style="--md-status-color: ${color};">
        <div class="md-motion-head">
          <span class="md-motion-type">${esc(TYPE_LABEL[m.motion_type] || m.motion_type)}</span>
          <span class="md-motion-status">${esc(STATUS_LABEL[m.status] || m.status)}</span>
          <span class="md-motion-filer">filed by ${filerName}</span>
          ${verifiedBadge}
          <span class="md-motion-date">${esc(filedDate)} &middot; #${m.id}</span>
        </div>
        ${targetBlock}
        <h3 class="md-motion-claim">${esc(m.claim)}</h3>
        <div class="${reasoningCls}">${esc(reasoning)}</div>
        ${showExpand ? '<button class="md-motion-expand" type="button">Read full reasoning</button>' : ''}
        ${citationsBlock}
        ${resolutionBlock}
        ${chamberLink}
      </article>
    `;
  }

  // ---------- boot ----------

  function boot() {
    bindParticipation();
    if ($('recordList')) {
      bindRecordFilters();
      loadRecord();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
