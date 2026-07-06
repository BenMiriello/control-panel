// Shared service action handlers: start/stop/restart/enable/disable/delete/open.
// Keeps the real backend routes exactly as-is; only presentation was redesigned.

window.PanelActions = (function() {
  function control(name, action) {
    return fetch(`/services/control/${encodeURIComponent(name)}/${encodeURIComponent(action)}`)
      .then((res) => res.json());
  }

  function remove(name) {
    return fetch(`/services/delete/${encodeURIComponent(name)}`)
      .then((res) => res.json());
  }

  function open(port) {
    window.open(`http://${window.location.hostname}:${port}`, '_blank');
  }

  function run(promise, successMsg) {
    return promise.then((data) => {
      if (data && data.success) {
        window.cpToast(successMsg, 'ok');
      } else {
        window.cpToast((data && data.error) || 'Action failed', 'err');
      }
      return data;
    }).catch((err) => {
      window.cpToast(err.message || 'Action failed', 'err');
      return { success: false, error: err.message };
    });
  }

  return {
    start: (name) => run(control(name, 'start'), `${name} started`),
    stop: (name) => run(control(name, 'stop'), `${name} stopped`),
    restart: (name) => run(control(name, 'restart'), `${name} restarted`),
    enable: (name) => run(control(name, 'enable'), `${name} auto-start enabled`),
    disable: (name) => run(control(name, 'disable'), `${name} auto-start disabled`),
    delete(name) {
      if (!confirm(`Delete service "${name}"? This cannot be undone.`)) {
        return Promise.resolve({ success: false });
      }
      return run(remove(name), `${name} deleted`);
    },
    open,
  };
})();
