// Cards view: masonry layout + collapsible service cards.

window.PanelCards = (function() {
  const GAP = 13;
  const icons = {
    external: '<svg class="cp-ico" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>',
    play: '<svg class="cp-ico" width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="6 3 20 12 6 21 6 3"/></svg>',
    restart: '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>',
    logs: '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v5h5M10 9H8M16 13H8M16 17H8"/></svg>',
    edit: '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.4 2.6a1.9 1.9 0 0 1 2.7 2.7L11 15.4l-3.6.9.9-3.6z"/></svg>',
    trash: '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>',
  };
  let resizeObserver = null;

  function render(container, services, state, onAction) {
    container.innerHTML = services.map((s) => cardHtml(s, state)).join('');
    wireCards(container, onAction);
    // Freshly-built cards have no prior transform; place them without the
    // transform transition so they appear in-slot instead of flying from 0,0.
    layout(container, state, false);
    if (!resizeObserver) {
      resizeObserver = new ResizeObserver(() => layout(container, state, false));
      resizeObserver.observe(container);
    }
  }

  function cardHtml(s, state) {
    const esc = window.PanelUtil.escapeHtml;
    const name = esc(s.name);
    const running = s.status === 'active';
    const expanded = state.expanded.has(s.name);
    const ps = s.port_status || {};
    const display = ps.actual_port || s.port || '—';

    let portToken = '';
    if (ps.validation === 'port_mismatch') {
      portToken = `<span class="cp-port-warn" title="Configured ${esc(s.port)}, actually listening on ${esc(ps.actual_port)}">⚠ :${esc(ps.actual_port)}</span>`;
    } else if (ps.validation === 'dynamic_port') {
      portToken = '<span class="cp-port-dyn" title="Dynamically detected port">~ dynamic</span>';
    }

    const autoChip = s.enabled
      ? '<span class="cp-auto-chip" title="Starts automatically on boot">auto</span>'
      : '';

    const rightActions = running
      ? `<button class="cp-btn cp-btn-secondary" data-action="open" data-name="${name}" data-port="${esc(display)}" style="height:28px;padding:0 10px;font-size:12px">Open ${icons.external}</button>
         <button class="cp-btn cp-btn-secondary" data-action="stop" data-name="${name}" style="height:28px;padding:0 11px;font-size:12px">Stop</button>`
      : `<button class="cp-btn cp-btn-start" data-action="start" data-name="${name}">${icons.play}Start</button>`;

    return `
      <div class="cp-card" data-card="${name}">
        <div class="cp-card-head">
          <button class="cp-card-toggle" data-toggle="${name}">
            <svg class="cp-ico cp-chevron${expanded ? ' open' : ''}" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
            <span class="cp-dot ${running ? 'cp-dot-running' : 'cp-dot-stopped'}"></span>
            <span class="cp-card-name">${name}</span>
            <span class="cp-port-chip">:${esc(display)}</span>
            ${portToken}
          </button>
          ${autoChip}
          <div style="display:flex;align-items:center;gap:6px;flex:none">${rightActions}</div>
        </div>
        <div class="cp-card-body-wrap${expanded ? ' open' : ''}">
          <div class="cp-card-body-inner">
            <div class="cp-card-body">${bodyHtml(s, ps)}</div>
          </div>
        </div>
      </div>`;
  }

  function bodyHtml(s, ps) {
    const esc = window.PanelUtil.escapeHtml;
    const name = esc(s.name);
    const display = ps.actual_port || s.port || '—';
    let portInfo;
    if (ps.validation === 'port_matches') {
      portInfo = `<span style="color:var(--green)">${esc(display)} ✓</span>`;
    } else if (ps.validation === 'port_mismatch') {
      portInfo = `<span style="color:var(--amber)">${esc(ps.actual_port)} ⚠ <span style="color:var(--text-3)">(cfg ${esc(ps.managed_port != null ? ps.managed_port : s.port)})</span></span>`;
    } else if (ps.validation === 'dynamic_port') {
      portInfo = `<span>${esc(display)} ~</span> <span style="color:var(--text-3)">dynamic</span>`;
    } else {
      portInfo = `<span>${esc(display)}</span>`;
    }

    const env = s.env || {};
    const envKeys = Object.keys(env);
    const envHtml = envKeys.length
      ? `<div style="margin-top:13px">
           <div class="cp-eyebrow" style="margin-bottom:5px">Environment</div>
           <div style="display:flex;flex-wrap:wrap;gap:6px">
             ${envKeys.map((k) => `<span class="cp-env-pill">${esc(k)}=${esc(env[k])}</span>`).join('')}
           </div>
         </div>`
      : '';

    const running = s.status === 'active';
    const autoOn = !!s.enabled;

    return `
      <div class="cp-eyebrow" style="margin-bottom:6px">Command</div>
      <div class="cp-code">${esc(s.command)}</div>
      <div class="cp-meta-grid">
        <div>
          <div class="cp-eyebrow" style="margin-bottom:4px">Directory</div>
          <div class="mono" style="font-size:12px;color:var(--text-2);word-break:break-all">${esc(s.working_dir || '—')}</div>
        </div>
        <div>
          <div style="display:flex;align-items:center;gap:5px;margin-bottom:4px">
            <span class="cp-eyebrow">Port</span>
            <span class="cp-info" title="✓ matches config · ⚠ mismatch · ~ dynamically detected">i</span>
          </div>
          <div class="mono" style="font-size:12px;color:var(--text-2)">${portInfo}</div>
        </div>
      </div>
      ${envHtml}
      <div class="cp-card-actions">
        <button class="cp-auto-toggle" data-action="${autoOn ? 'disable' : 'enable'}" data-name="${name}" title="Toggle start-on-boot">
          <span class="cp-switch" style="width:26px;height:15px;background:${autoOn ? 'var(--accent)' : 'var(--border-strong)'}">
            <span class="cp-switch-knob" style="width:11px;height:11px;transform:${autoOn ? 'translateX(11px)' : 'none'}"></span>
          </span>
          Auto-start
        </button>
        ${running ? `<button class="cp-btn cp-btn-ghost" data-action="restart" data-name="${name}">${icons.restart}Restart</button>` : ''}
        <a class="cp-btn cp-btn-ghost" href="/logs/${encodeURIComponent(s.name)}">${icons.logs}Logs</a>
        <a class="cp-btn cp-btn-ghost" href="/services/edit/${encodeURIComponent(s.name)}">${icons.edit}Edit</a>
        <div style="flex:1"></div>
        <button class="cp-btn cp-btn-danger" data-action="delete" data-name="${name}" title="Delete service">${icons.trash}Delete</button>
      </div>`;
  }

  function toggleCard(container, name, state) {
    const card = container.querySelector(`.cp-card[data-card="${name}"]`);
    if (!card) return;
    const open = state.expanded.has(name);
    card.querySelector('.cp-card-body-wrap').classList.toggle('open', open);
    card.querySelector('.cp-chevron').classList.toggle('open', open);
    card.style.zIndex = open ? '5' : '1';
    layout(container, state);
  }

  function wireCards(container, onAction) {
    container.querySelectorAll('[data-toggle]').forEach((btn) => {
      btn.addEventListener('click', () => {
        window.PanelDashboard.toggleExpanded(btn.getAttribute('data-toggle'));
      });
    });
    container.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const name = btn.getAttribute('data-name');
        const action = btn.getAttribute('data-action');
        if (action === 'open') {
          window.PanelActions.open(btn.getAttribute('data-port'));
        } else {
          onAction(name, action);
        }
      });
    });
  }

  function layout(container, state, animate = true) {
    const cards = Array.from(container.querySelectorAll('.cp-card'));
    if (!cards.length) {
      container.style.height = '0px';
      return;
    }
    if (!animate) cards.forEach((c) => { c.style.transition = 'none'; });
    const width = container.clientWidth;
    const columns = width <= 680 ? 1 : 2;
    const colWidth = (width - GAP * (columns - 1)) / columns;
    const colHeights = new Array(columns).fill(0);

    cards.forEach((card) => {
      card.style.width = `${colWidth}px`;
      const name = card.getAttribute('data-card');
      const expanded = state.expanded.has(name);
      const headerH = card.querySelector('.cp-card-head').offsetHeight;
      const bodyInner = card.querySelector('.cp-card-body-inner');
      const bodyH = expanded ? bodyInner.scrollHeight + 1 : 0;
      const cardH = headerH + bodyH;

      let col = 0;
      for (let i = 1; i < columns; i++) {
        if (colHeights[i] < colHeights[col]) col = i;
      }
      const x = col * (colWidth + GAP);
      const y = colHeights[col];
      card.style.transform = `translate(${x}px, ${y}px)`;
      card.style.zIndex = expanded ? '5' : '1';
      colHeights[col] = y + cardH + GAP;
    });

    container.style.height = `${Math.max(...colHeights) - GAP}px`;
    if (!animate) {
      // Restore the transition next frame so later moves (expand/collapse) animate.
      requestAnimationFrame(() => cards.forEach((c) => { c.style.transition = ''; }));
    }
  }

  return { render, toggleCard };
})();
