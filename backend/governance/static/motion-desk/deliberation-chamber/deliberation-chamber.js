/* === Deliberation Chamber -- read view of one motion's argument thread ===

   Sub-room of the Motion Desk. The page renders a single motion's thread
   chronologically with rebuttals visually nested under their parent. The
   whole venue is read-only here: anyone can read; posting opens with shared
   Libra Engine sign-in (a calm participation notice stands in for the form).
   The motion id is resolved from the path
   /motion-desk/deliberation-chamber/{id}/. */

(() => {
  'use strict';

  const STATUS_COLORS = {
    filed: 'var(--md-status-filed)',
    in_deliberation: 'var(--md-status-in-deliberation)',
    ratified: 'var(--md-status-ratified)',
    covered: 'var(--md-status-covered)',
    rejected: 'var(--md-status-rejected)',
  };
  const STATUS_LABEL = {
    filed: 'Filed',
    in_deliberation: 'In deliberation',
    ratified: 'Ratified',
    covered: 'Covered',
    rejected: 'Rejected',
  };
  const TYPE_LABEL_MOTION = {
    amend_tenet: 'Amend tenet',
    new_tenet: 'New tenet',
    remove_tenet: 'Remove tenet',
    amend_rule: 'Amend rule',
    new_rule: 'New rule',
    remove_rule: 'Remove rule',
    process: 'Process',
  };
  const TYPE_LABEL_POST = {
    argument_for: 'For',
    argument_against: 'Against',
    rebuttal: 'Rebuttal',
    citation: 'Citation',
    clarification: 'Clarification',
  };
  const RESOLVED_STATUSES = new Set(['ratified', 'rejected', 'covered']);

  // ---------- helpers ----------

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function fmtDate(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch (_) { return ''; }
  }

  function getMotionIdFromPath() {
    const m = window.location.pathname.match(/\/motion-desk\/deliberation-chamber\/(\d+)\/?$/);
    return m ? parseInt(m[1], 10) : null;
  }

  // ---------- state ----------

  const state = {
    motionId: getMotionIdFromPath(),
    motion: null,
    args: [],
    argsError: null,
  };

  // ---------- motion header ----------

  async function loadMotion() {
    try {
      return await window.LECGAuth.fetchJSON(`/api/motions/${state.motionId}`);
    } catch (err) {
      if (err.status === 404) throw new Error('Motion not found');
      throw new Error(`Failed to load motion (${err.status || 'error'})`);
    }
  }

  function renderMotionHeader(m) {
    const header = $('motionHeader');
    const color = STATUS_COLORS[m.status] || 'var(--md-rule)';

    let targetBlock = '';
    if (m.target_kind && m.target_ref) {
      targetBlock = `<p class="dc-motion-target">Targets <b>${esc(m.target_kind)}</b> <code>${esc(m.target_ref)}</code></p>`;
    } else if (m.motion_type === 'new_tenet') {
      targetBlock = '<p class="dc-motion-target"><em>Proposes a new tenet</em></p>';
    } else if (m.motion_type === 'new_rule') {
      targetBlock = '<p class="dc-motion-target"><em>Proposes a new rule</em></p>';
    } else if (m.motion_type === 'process') {
      targetBlock = '<p class="dc-motion-target"><em>Methodology / morality / process</em></p>';
    }

    const reasoning = (m.reasoning || '').trim();
    const showExpand = reasoning.length > 240 || reasoning.split('\n').length > 3;
    const reasoningCls = showExpand ? 'dc-motion-reasoning collapsed' : 'dc-motion-reasoning';

    const filerHandle = m.filed_by_handle
      ? `@${esc(m.filed_by_handle)}`
      : esc(m.filed_by_anon_id || 'unknown');
    const verified = m.filed_by_verified
      ? '<span class="dc-motion-verified">verified</span>' : '';

    header.style.setProperty('--dc-status-color', color);
    header.innerHTML = `
      <p class="dc-motion-meta">
        <span class="dc-motion-type">${esc(TYPE_LABEL_MOTION[m.motion_type] || m.motion_type)}</span>
        <span class="dc-motion-status">${esc(STATUS_LABEL[m.status] || m.status)}</span>
        <span>#${m.id}</span>
        <span>filed ${esc(fmtDate(m.filed_at))}</span>
      </p>
      ${targetBlock}
      <h1 class="dc-motion-claim">${esc(m.claim)}</h1>
      <div class="${reasoningCls}" id="motionReasoning">${esc(reasoning)}</div>
      ${showExpand ? '<button class="dc-motion-expand" type="button" id="motionReasoningExpand">Read full reasoning</button>' : ''}
      <p class="dc-motion-filer">Filed by ${filerHandle} ${verified}</p>
    `;
    if (showExpand) {
      $('motionReasoningExpand').addEventListener('click', () => {
        const r = $('motionReasoning');
        const isOpen = r.classList.toggle('collapsed');
        $('motionReasoningExpand').textContent = isOpen ? 'Read full reasoning' : 'Collapse';
      });
    }
  }

  function renderResolutionBanner(m) {
    const banner = $('resolutionBanner');
    if (!RESOLVED_STATUSES.has(m.status) || !m.resolution_summary) {
      banner.hidden = true;
      return;
    }
    const color = STATUS_COLORS[m.status] || 'var(--md-rule)';
    banner.style.setProperty('--dc-status-color', color);
    banner.hidden = false;
    banner.innerHTML = `
      <p class="dc-resolution-label">
        ${esc(STATUS_LABEL[m.status] || m.status)}
        ${m.resolved_at ? ' &middot; ' + esc(fmtDate(m.resolved_at)) : ''}
      </p>
      <p class="dc-resolution-summary">${esc(m.resolution_summary)}</p>
    `;
  }

  // ---------- thread ----------

  async function loadArguments() {
    return window.LECGAuth.fetchJSON(`/api/motions/${state.motionId}/arguments`);
  }

  function orderThread(args) {
    // Chronological order, but each rebuttal is placed immediately after its
    // parent post (and any earlier rebuttals on the same parent).
    const byId = new Map(args.map((a) => [a.id, a]));
    const topLevel = args.filter((a) => !a.parent_id);
    topLevel.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    const rebuttalsByParent = new Map();
    for (const a of args) {
      if (a.parent_id && byId.has(a.parent_id)) {
        if (!rebuttalsByParent.has(a.parent_id)) rebuttalsByParent.set(a.parent_id, []);
        rebuttalsByParent.get(a.parent_id).push(a);
      }
    }
    for (const list of rebuttalsByParent.values()) {
      list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    const out = [];
    for (const parent of topLevel) {
      out.push(parent);
      const kids = rebuttalsByParent.get(parent.id) || [];
      out.push(...kids);
    }
    return out;
  }

  function renderPost(a) {
    const isRebut = a.post_type === 'rebuttal';
    const verified = a.author_verified
      ? '<span class="dc-post-verified">verified</span>' : '';
    const author = a.author_handle
      ? `@${esc(a.author_handle)}`
      : esc(a.author_anon_id || 'unknown');
    const citations = (a.citations && a.citations.length)
      ? `<div class="dc-post-citations">
           <span class="label">Citations</span>
           ${a.citations.map((u) => `<div><a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a></div>`).join('')}
         </div>`
      : '';

    return `
      <article class="dc-post ${isRebut ? 'rebuttal' : ''}" data-type="${esc(a.post_type)}" data-id="${a.id}">
        <div class="dc-post-head">
          <span class="dc-post-type">${esc(TYPE_LABEL_POST[a.post_type] || a.post_type)}</span>
          <span class="dc-post-author">${author}</span>
          ${verified}
          <span class="dc-post-date">${esc(fmtDate(a.created_at))}</span>
        </div>
        <h3 class="dc-post-summary">${esc(a.summary)}</h3>
        <p class="dc-post-body">${esc(a.body)}</p>
        ${citations}
      </article>
    `;
  }

  function renderThread() {
    const thread = $('thread');
    if (state.argsError) {
      thread.innerHTML = `<p class="dc-empty">${esc(state.argsError)}</p>`;
      return;
    }
    if (!state.args.length) {
      thread.innerHTML = '<p class="dc-empty">No arguments on the record yet.</p>';
      return;
    }
    thread.innerHTML = orderThread(state.args).map(renderPost).join('');
  }

  // ---------- participation notice (deferred posting) ----------

  function renderParticipationNotice(m) {
    const notice = $('participationNotice');
    const title = notice.querySelector('.lecg-notice-title');
    const body = $('participationNoticeBody');
    if (!notice || !body) return;

    if (RESOLVED_STATUSES.has(m.status)) {
      // Closed deliberation -- the thread above is the preserved record.
      title.textContent = 'This deliberation has closed';
      body.textContent =
        'The thread above is preserved as the public record of how this ' +
        'motion was deliberated. The Chamber is read-only.';
      notice.hidden = false;
      return;
    }
    if (m.status !== 'in_deliberation') {
      title.textContent = 'Not yet open for deliberation';
      body.textContent =
        'This motion is still in the filed queue. It opens for argument once ' +
        'it is moved into deliberation. Until then, posting is closed.';
      notice.hidden = false;
      return;
    }
    // In deliberation -- posting is the deferred write action.
    title.textContent = 'Posting opens soon';
    body.textContent = window.LECGAuth.participationNotice();
    notice.hidden = false;
  }

  // ---------- boot ----------

  async function boot() {
    if (!state.motionId) {
      $('motionHeader').innerHTML = '<p class="dc-empty">No motion id in the URL.</p>';
      $('thread').innerHTML = '';
      return;
    }
    // The motion fetch is authoritative: a bad id 404s here and that is the
    // error worth showing. Load the motion first; only then the thread, and
    // let a thread-only failure degrade gracefully.
    let m;
    try {
      m = await loadMotion();
    } catch (err) {
      $('motionHeader').innerHTML = `<p class="dc-empty">${esc(err.message)}</p>`;
      $('thread').innerHTML = '';
      return;
    }
    state.motion = m;
    renderMotionHeader(m);
    renderResolutionBanner(m);

    try {
      state.args = await loadArguments();
      state.argsError = null;
    } catch (err) {
      state.args = [];
      state.argsError = err.message || 'Failed to load the thread.';
    }
    renderThread();
    renderParticipationNotice(m);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
