// Shell-level behavior shared by every page: theme toggle, toasts, top-bar summary.

window.cpToggleTheme = function() {
  var root = document.documentElement;
  var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  localStorage.setItem('panel-theme', next);
};

window.cpToast = function(message, kind) {
  kind = kind === 'err' ? 'err' : 'ok';
  var container = document.getElementById('cp-toasts');
  if (!container) return;
  var toast = document.createElement('div');
  toast.className = 'cp-toast cp-toast-' + kind;
  var span = document.createElement('span');
  span.textContent = message;
  toast.appendChild(span);
  container.appendChild(toast);
  setTimeout(function() {
    toast.remove();
  }, 3500);
};

document.addEventListener('DOMContentLoaded', function() {
  var runningEl = document.getElementById('cp-summary-running');
  var totalEl = document.getElementById('cp-summary-total');
  if (!runningEl && !totalEl) return;
  fetch('/api/services')
    .then(function(res) { return res.json(); })
    .then(function(data) {
      var services = (data && data.services) || [];
      var running = services.filter(function(s) { return s.status === 'active'; }).length;
      if (runningEl) runningEl.textContent = running;
      if (totalEl) totalEl.textContent = services.length;
    })
    .catch(function() {});
});
