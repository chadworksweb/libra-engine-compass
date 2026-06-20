/* === Amendments -- fetch + render the public record ===

   Reads GET /api/amendments and renders the standard's change history,
   grouped by status. Read-only and anonymous: the Compass keeps the record;
   proposals are argued on the Motion Desk. */

(() => {
  'use strict';

  async function fetchLog() {
    let lastErr;
    for (let i = 0; i < 3; i++) {
      try {
        return await window.LECGAuth.fetchJSON('/api/amendments', {
          signal: AbortSignal.timeout(8000),
        });
      } catch (err) {
        lastErr = err;
        // A 4xx is a real, non-transient failure -- don't retry it.
        if (err.status && err.status >= 400 && err.status < 500) throw err;
      }
      if (i < 2) await new Promise((r) => setTimeout(r, 400 * (i + 1)));
    }
    throw lastErr;
  }

  // Status -> CSS var name (also used in card side-stripe).
  const STATUS_COLOR_VAR = {
    proposed: '--am-proposed',
    deliberating: '--am-deliberating',
    ratified: '--am-ratified',
    covered: '--am-covered',
    rejected: '--am-rejected',
  };

  // Fallback status descriptions when the log doesn't ship its own. The venue
  // may provide statuses[] with label + description; this only fills gaps.
  const STATUS_DESCRIPTION = {
    proposed: 'Raised and awaiting deliberation.',
    deliberating: 'Under argument on the Motion Desk right now.',
    ratified: 'Argued, carried, and folded into the tenets.',
    covered: 'Already answered by an existing tenet or a prior amendment.',
    rejected: 'Argued and not carried.',
  };
  const STATUS_ORDER = ['proposed', 'deliberating', 'ratified', 'covered', 'rejected'];

  // ---------- helpers ----------

  const html = (tag, attrs = {}, children = []) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null) continue;
      if (k === 'class') node.className = v;
      else if (k === 'style') node.setAttribute('style', v);
      else if (k.startsWith('data-') || k === 'id' || k === 'role' || k === 'aria-label' || k === 'target' || k === 'rel') {
        node.setAttribute(k, v);
      } else {
        node[k] = v;
      }
    }
    for (const c of [].concat(children)) {
      if (c != null) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return node;
  };

  const statusColor = (key) => `var(${STATUS_COLOR_VAR[key] || '--am-rule'})`;

  // ---------- venue CTA ----------

  function renderVenueCta(root, venue) {
    root.replaceChildren();
    if (!venue || !venue.url) return;
    const label = venue.label || 'Open the Motion Desk';
    root.appendChild(html('a', {
      class: 'am-cta',
      href: venue.url,
    }, label));
    if (venue.note) {
      root.parentElement.appendChild(html('p', { class: 'am-cta-note' }, venue.note));
    }
  }

  // ---------- thresholds ----------

  function renderThresholds(root, t) {
    root.replaceChildren();
    if (!t || typeof t !== 'object') return;
    // Render whatever threshold pairs the venue ships. Known keys get a
    // friendly label + unit; anything else renders generically so a new
    // threshold appears without a frontend change.
    const KNOWN = {
      co_sponsors_required: { label: 'Co-sponsors required', fmt: (v) => String(v) },
      deliberation_window_days: { label: 'Deliberation window', fmt: (v) => `${v} days` },
      ratification_supermajority_pct: { label: 'Supermajority to ratify', fmt: (v) => `${v}%` },
    };
    const entries = Object.entries(t).filter(([, v]) => v != null);
    if (!entries.length) return;
    entries.forEach(([key, value]) => {
      const known = KNOWN[key];
      const display = known ? known.fmt(value) : String(value);
      const label = known ? known.label : key.replace(/_/g, ' ');
      const box = html('div', { class: 'am-thresh' });
      box.appendChild(html('p', { class: 'am-thresh-value' }, display));
      box.appendChild(html('p', { class: 'am-thresh-label' }, label));
      root.appendChild(box);
    });
  }

  // ---------- amendment card ----------

  function renderCard(am) {
    const color = statusColor(am.status);
    const card = html('article', {
      class: 'am-card',
      id: `amend-${am.id}`,
      style: `--status-color: ${color};`,
    });

    card.appendChild(html('p', { class: 'am-card-id' }, `${am.id} - ${String(am.status || '').toUpperCase()}`));
    card.appendChild(html('h3', { class: 'am-card-title' }, am.title || '(untitled)'));

    // Meta row
    const meta = html('div', { class: 'am-card-meta' });
    if (am.proposed_at) meta.appendChild(html('span', {}, [html('b', {}, 'Proposed '), am.proposed_at]));
    if (am.target_kind && am.target_ref) {
      // Tenet targets link into the tenets page by id; other kinds show plain.
      if (am.target_kind === 'tenet') {
        const a = html('a', { href: `/tenets/#tenet-${am.target_ref}` }, am.target_ref);
        meta.appendChild(html('span', {}, [html('b', {}, 'Targets '), a]));
      } else {
        meta.appendChild(html('span', {}, [html('b', {}, `Targets ${am.target_kind} `), am.target_ref]));
      }
    }
    if (am.proposer) meta.appendChild(html('span', {}, [html('b', {}, 'Proposer '), am.proposer]));
    if (am.ratified_at) meta.appendChild(html('span', {}, [html('b', {}, 'Ratified '), am.ratified_at]));
    if (am.rejected_at && am.status === 'rejected') meta.appendChild(html('span', {}, [html('b', {}, 'Rejected '), am.rejected_at]));
    card.appendChild(meta);

    // Proposed change
    if (am.proposed_change) {
      const sec = html('div', { class: 'am-card-section' });
      sec.appendChild(html('h4', {}, 'Proposed change'));
      sec.appendChild(html('p', {}, am.proposed_change));
      card.appendChild(sec);
    }

    // Covered-by explanation
    if (am.status === 'covered' && (am.covered_by || am.rejection_reason)) {
      const sec = html('div', { class: 'am-card-section' });
      sec.appendChild(html('h4', {}, am.covered_by ? `Already covered by ${am.covered_by}` : 'Already covered'));
      if (am.rejection_reason) sec.appendChild(html('p', {}, am.rejection_reason));
      card.appendChild(sec);
    }

    // Rejection reason
    if (am.status === 'rejected' && am.rejection_reason) {
      const sec = html('div', { class: 'am-card-section' });
      sec.appendChild(html('h4', {}, 'Rejection reason'));
      sec.appendChild(html('p', {}, am.rejection_reason));
      card.appendChild(sec);
    }

    // Discussion link -- points at the Deliberation Chamber for any motion
    // already moved past the filed queue. Same-origin: the Chamber is part of
    // this venue, not an offsite room.
    if (am.discussion_url) {
      const label = am.status === 'deliberating'
        ? 'Open the Deliberation Chamber ->'
        : 'See the deliberation record ->';
      card.appendChild(html('a', { class: 'am-card-cta', href: am.discussion_url }, label));
    }

    return card;
  }

  // ---------- groups (one per status) ----------

  function renderGroups(root, data) {
    root.replaceChildren();
    const byStatus = {};
    (data.amendments || []).forEach((am) => {
      (byStatus[am.status] = byStatus[am.status] || []).push(am);
    });

    // Prefer the venue's own status list (label + description + order); fall
    // back to the known ordering when it isn't shipped.
    let statuses = data.statuses;
    if (!Array.isArray(statuses) || !statuses.length) {
      statuses = STATUS_ORDER.map((key) => ({ key }));
    }

    statuses.forEach((status) => {
      const key = status.key;
      const color = statusColor(key);
      const group = html('section', {
        class: 'am-group',
        id: `group-${key}`,
        style: `--status-color: ${color};`,
      });

      const header = html('div', { class: 'am-group-header' });
      const label = status.label || key.replace(/_/g, ' ');
      header.appendChild(html('h2', { class: 'am-group-label' }, String(label).toUpperCase()));
      const entries = byStatus[key] || [];
      header.appendChild(html('p', { class: 'am-group-count' }, `${entries.length} - ${key}`));
      group.appendChild(header);

      const description = status.description || STATUS_DESCRIPTION[key];
      if (description) group.appendChild(html('p', { class: 'am-group-description' }, description));

      if (entries.length === 0) {
        group.appendChild(html('p', { class: 'am-empty' }, 'None on the record yet.'));
      } else {
        // Newest first by proposed_at (string-sortable YYYY-MM-DD).
        entries.sort((a, b) => (b.proposed_at || '').localeCompare(a.proposed_at || ''));
        entries.forEach((am) => group.appendChild(renderCard(am)));
      }

      root.appendChild(group);
    });
  }

  // ---------- meta ----------

  function renderFooterMeta(data) {
    const v = document.getElementById('schema-version');
    const u = document.getElementById('updated-at');
    if (v && data.schema_version != null) v.textContent = `v${data.schema_version}`;
    if (u) u.textContent = data.updated_at || '--';
  }

  // ---------- boot ----------

  async function boot() {
    const cta = document.getElementById('venue-cta');
    const thresholds = document.getElementById('thresholds');
    const sections = document.getElementById('sections');

    try {
      const data = await fetchLog();
      renderVenueCta(cta, data.venue);
      renderThresholds(thresholds, data.thresholds);
      renderFooterMeta(data);
      renderGroups(sections, data);
    } catch (err) {
      console.error('Failed to load amendment log:', err);
      sections.appendChild(
        html('p', { class: 'am-empty' }, 'The amendment record is momentarily out of reach. Please reload.'),
      );
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
