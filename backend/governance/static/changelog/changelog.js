/* === Calibrator Changelog -- render the calibrator's change-history timeline
       from window.CHANGELOG_DATA (served live at /changelog/changelog-data.js). === */

(() => {
  'use strict';

  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

  const KIND_LABEL = { law: 'Rule of construction', lens: 'Reading lens', foundation: 'Foundation' };

  function fmtDate(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
    if (!m) return s || '';
    return `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}`;
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function render(data) {
    const root = document.getElementById('timeline');
    root.replaceChildren();

    (data.entries || []).forEach((e) => {
      const item = el('article', `evo-item evo-${e.kind || 'law'}`);

      const rail = el('div', 'evo-rail');
      rail.appendChild(el('time', 'evo-date', fmtDate(e.date)));
      rail.appendChild(el('span', 'evo-kind', KIND_LABEL[e.kind] || e.kind || ''));

      const body = el('div', 'evo-body');
      if (e.headline) body.appendChild(el('h2', 'evo-headline', e.headline));
      if (e.body) body.appendChild(el('p', 'evo-text', e.body));
      if (e.source) body.appendChild(el('p', 'evo-source', e.source));

      item.appendChild(rail);
      item.appendChild(body);
      root.appendChild(item);
    });

    const v = document.getElementById('evo-version');
    if (v) v.textContent = data.constitution_version || '';
    const rc = document.getElementById('evo-rulecount');
    if (rc) rc.textContent = data.rule_count != null ? String(data.rule_count) : '';
  }

  function boot() {
    const root = document.getElementById('timeline');
    if (!window.CHANGELOG_DATA) {
      root.appendChild(el('p', 'evo-error', 'The history is momentarily out of reach. Please reload.'));
      return;
    }
    try {
      render(window.CHANGELOG_DATA);
    } catch (err) {
      console.error('Failed to render the changelog timeline:', err);
      root.appendChild(el('p', 'evo-error', 'The history is momentarily out of reach. Please reload.'));
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
