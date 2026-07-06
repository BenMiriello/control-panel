// List view: table rows with FLIP reorder animation.

window.PanelList = (function() {
  const icons = {
    square: '<svg class="cp-ico" width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>',
    play: '<svg class="cp-ico" width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="6 3 20 12 6 21 6 3"/></svg>',
    logs: '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v5h5M10 9H8M16 13H8M16 17H8"/></svg>',
    edit: '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.4 2.6a1.9 1.9 0 0 1 2.7 2.7L11 15.4l-3.6.9.9-3.6z"/></svg>',
  };

  function render(container, services, state, onAction) {
    const prevRects = captureRects(container);
    container.innerHTML = headerHtml(state) + services.map((s) => rowHtml(s)).join('');
    wireRows(container, onAction);
    flip(container, prevRects);
  }

  function headerHtml(state) {
    return `
      <div class="cp-list-grid cp-list-header">
        <span></span>
        <button class="cp-list-sort-btn" data-sortcol="name">Service${arrow(state, 'name')}</button>
        <button class="cp-list-sort-btn" data-sortcol="port">Port${arrow(state, 'port')}</button>
        <span class="cp-list-col-cmd cp-eyebrow">Command</span>
        <span class="cp-list-col-auto cp-eyebrow">Auto</span>
        <span class="cp-eyebrow" style="text-align:right">Actions</span>
      </div>`;
  }

  function arrow(state, key) {
    if (state.sortKey !== key) return '';
    return ` <span class="mono">${state.sortDir === 1 ? '↑' : '↓'}</span>`;
  }

  function rowHtml(s) {
    const esc = window.PanelUtil.escapeHtml;
    const running = s.status === 'active';
    const ps = s.port_status || {};
    const port = ps.actual_port || s.port || '—';
    const dot = running
      ? '<span class="cp-dot cp-dot-running" title="Running"></span>'
      : '<span class="cp-dot cp-dot-stopped" title="Stopped"></span>';
    const autoCell = s.enabled
      ? '<span class="cp-auto-chip">on</span>'
      : '<span style="font-size:10.5px;color:var(--text-3)">—</span>';
    const statusBtn = running
      ? `<button class="cp-icon-btn" data-action="stop" data-name="${esc(s.name)}" title="Stop">${icons.square}</button>`
      : `<button class="cp-icon-btn cp-icon-btn-start" data-action="start" data-name="${esc(s.name)}" title="Start">${icons.play}</button>`;

    return `
      <div class="cp-list-grid cp-list-row" data-flip="${esc(s.name)}">
        ${dot}
        <span style="font-weight:600;font-size:13px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(s.name)}</span>
        <span class="mono" style="font-size:12px;color:var(--text-2)">:${esc(port)}</span>
        <span class="cp-list-col-cmd mono" style="font-size:11.5px;color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(s.command)}</span>
        <span class="cp-list-col-auto">${autoCell}</span>
        <div style="display:flex;align-items:center;justify-content:flex-end;gap:5px">
          ${statusBtn}
          <a class="cp-icon-btn" href="/logs/${encodeURIComponent(s.name)}" title="Logs">${icons.logs}</a>
          <a class="cp-icon-btn" href="/services/edit/${encodeURIComponent(s.name)}" title="Edit">${icons.edit}</a>
        </div>
      </div>`;
  }

  function wireRows(container, onAction) {
    container.querySelectorAll('[data-sortcol]').forEach((btn) => {
      btn.addEventListener('click', () => {
        window.PanelDashboard.setSort(btn.getAttribute('data-sortcol'));
      });
    });
    container.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        onAction(btn.getAttribute('data-name'), btn.getAttribute('data-action'));
      });
    });
  }

  function captureRects(container) {
    const rects = new Map();
    container.querySelectorAll('[data-flip]').forEach((el) => {
      rects.set(el.getAttribute('data-flip'), el.getBoundingClientRect());
    });
    return rects;
  }

  function flip(container, prevRects) {
    container.querySelectorAll('[data-flip]').forEach((el) => {
      const prev = prevRects.get(el.getAttribute('data-flip'));
      if (!prev) return;
      const next = el.getBoundingClientRect();
      const dx = prev.left - next.left;
      const dy = prev.top - next.top;
      if (!dx && !dy) return;
      el.style.transition = 'none';
      el.style.transform = `translate(${dx}px, ${dy}px)`;
      requestAnimationFrame(() => {
        el.style.transition = 'transform .4s cubic-bezier(.4,0,.2,1)';
        el.style.transform = '';
      });
    });
  }

  return { render };
})();
