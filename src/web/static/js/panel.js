// Dashboard state, polling, filtering/sorting, and toolbar wiring.
// Cards/list views are rendered by panel-cards.js / panel-list.js from the
// filtered+sorted dataset computed here.

window.PanelUtil = {
  escapeHtml(value) {
    if (value === undefined || value === null) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  },
  portDisplay(service) {
    const ps = service.port_status || {};
    return ps.actual_port || service.port || null;
  },
};

(function() {
  const state = {
    view: localStorage.getItem('panel-view') === 'list' ? 'list' : 'cards',
    query: '',
    filter: 'all',
    sortKey: 'name',
    sortDir: 1,
    expanded: new Set(),
    rangesOpen: true,
    services: [],
    lastHash: '',
  };

  const cardsEl = document.getElementById('cp-cards');
  const listEl = document.getElementById('cp-list');
  const emptyEl = document.getElementById('cp-empty');
  const searchEl = document.getElementById('cp-search');

  // Hash only the fields the UI actually renders, so volatile port-detection
  // internals (detected_ports, main_pid, last_started) don't trigger a rebuild
  // and re-animate the whole grid every poll.
  function displayHash(services) {
    return services.map((s) => {
      const ps = s.port_status || {};
      return [s.name, s.status, s.enabled, s.port, ps.actual_port, ps.validation,
        ps.managed_port, s.command, s.working_dir, JSON.stringify(s.env || {})].join('|');
    }).join('~');
  }

  function matchesFilter(s) {
    if (state.filter === 'running') return s.status === 'active';
    if (state.filter === 'stopped') return s.status !== 'active';
    if (state.filter === 'auto') return !!s.enabled;
    return true;
  }

  function matchesQuery(s) {
    if (!state.query) return true;
    const q = state.query.toLowerCase();
    return (s.name || '').toLowerCase().includes(q) || (s.command || '').toLowerCase().includes(q);
  }

  function sortValue(s) {
    if (state.sortKey === 'status') return s.status === 'active' ? '0' : '1';
    if (state.sortKey === 'port') return Number(window.PanelUtil.portDisplay(s) || 0);
    return (s.name || '').toLowerCase();
  }

  function getVisible() {
    const filtered = state.services.filter((s) => matchesFilter(s) && matchesQuery(s));
    filtered.sort((a, b) => {
      const av = sortValue(a);
      const bv = sortValue(b);
      if (av < bv) return -1 * state.sortDir;
      if (av > bv) return 1 * state.sortDir;
      return 0;
    });
    return filtered;
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function updateCounts() {
    const total = state.services.length;
    const running = state.services.filter((s) => s.status === 'active').length;
    const auto = state.services.filter((s) => s.enabled).length;
    setText('cp-count-all', total);
    setText('cp-count-running', running);
    setText('cp-count-stopped', total - running);
    setText('cp-count-auto', auto);
    setText('cp-summary-running', running);
    setText('cp-summary-total', total);
  }

  function render() {
    updateCounts();
    const visible = getVisible();
    emptyEl.style.display = visible.length === 0 ? 'block' : 'none';
    cardsEl.style.display = state.view === 'cards' && visible.length ? 'block' : 'none';
    listEl.style.display = state.view === 'list' && visible.length ? 'block' : 'none';
    if (!visible.length) return;
    if (state.view === 'cards') {
      window.PanelCards.render(cardsEl, visible, state, onAction);
    } else {
      window.PanelList.render(listEl, visible, state, onAction);
    }
  }

  function onAction(name, action) {
    const handlers = {
      start: window.PanelActions.start,
      stop: window.PanelActions.stop,
      restart: window.PanelActions.restart,
      enable: window.PanelActions.enable,
      disable: window.PanelActions.disable,
      delete: window.PanelActions.delete,
    };
    const handler = handlers[action];
    if (!handler) return;
    handler(name).then((data) => {
      if (data && data.success) poll(true);
    });
  }

  function toggleExpanded(name) {
    if (state.expanded.has(name)) state.expanded.delete(name);
    else state.expanded.add(name);
    if (state.view === 'cards' && window.PanelCards.toggleCard) {
      window.PanelCards.toggleCard(cardsEl, name, state);
    } else {
      render();
    }
  }

  function setSort(key) {
    if (state.sortKey === key) {
      state.sortDir *= -1;
    } else {
      state.sortKey = key;
      state.sortDir = 1;
    }
    updateSortUI();
    render();
  }

  async function poll(force) {
    try {
      const res = await fetch('/api/services');
      const data = await res.json();
      const services = data.services || [];
      const hash = displayHash(services);
      if (!force && hash === state.lastHash) return;
      state.lastHash = hash;
      state.services = services;
      render();
    } catch (err) {
      console.error('Error fetching services:', err);
    }
  }

  function updateSortUI() {
    document.querySelectorAll('#cp-sortbar .cp-sort-btn').forEach((btn) => {
      const active = btn.getAttribute('data-sort') === state.sortKey;
      btn.classList.toggle('active', active);
      const arrow = btn.querySelector('.cp-sort-arrow');
      if (arrow) arrow.textContent = active ? (state.sortDir === 1 ? '↑' : '↓') : '';
    });
  }

  function wireToolbar() {
    searchEl.addEventListener('input', () => {
      state.query = searchEl.value;
      render();
    });

    document.getElementById('cp-chips').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-filter]');
      if (!btn) return;
      state.filter = btn.getAttribute('data-filter');
      document.querySelectorAll('#cp-chips .cp-chip').forEach((el) => el.classList.toggle('active', el === btn));
      render();
    });

    document.getElementById('cp-sortbar').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-sort]');
      if (!btn) return;
      setSort(btn.getAttribute('data-sort'));
    });

    document.getElementById('cp-viewswitch').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-view]');
      if (!btn) return;
      state.view = btn.getAttribute('data-view');
      localStorage.setItem('panel-view', state.view);
      document.querySelectorAll('#cp-viewswitch .cp-view-btn').forEach((el) => el.classList.toggle('active', el === btn));
      render();
    });

    const rangesToggle = document.getElementById('cp-ranges-toggle');
    if (rangesToggle) {
      rangesToggle.addEventListener('click', () => {
        state.rangesOpen = !state.rangesOpen;
        document.getElementById('cp-ranges-body-wrap').classList.toggle('closed', !state.rangesOpen);
        document.getElementById('cp-ranges-chevron').classList.toggle('open', state.rangesOpen);
      });
    }
  }

  function initView() {
    document.querySelectorAll('#cp-viewswitch .cp-view-btn').forEach((el) => {
      el.classList.toggle('active', el.getAttribute('data-view') === state.view);
    });
  }

  window.PanelDashboard = { toggleExpanded, setSort };

  document.addEventListener('DOMContentLoaded', () => {
    if (!cardsEl) return;
    wireToolbar();
    updateSortUI();
    initView();
    poll(true);
    setInterval(() => poll(false), 1000);
  });
})();
