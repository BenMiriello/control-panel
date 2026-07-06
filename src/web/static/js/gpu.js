// GPU panel: what is on the card + broker lease state, with a clear-lease action.

class GpuPanel {
    constructor(refreshInterval = 3000) {
        this.refreshInterval = refreshInterval;
        this.endpoint = '/api/gpu';
        this.intervalId = null;
        this.panel = document.getElementById('gpu-panel');
    }

    init() {
        if (!this.panel) return;
        const btn = document.getElementById('gpu-clear-btn');
        if (btn) btn.addEventListener('click', () => this.clearLease());
        this.update();
        this.intervalId = setInterval(() => this.update(), this.refreshInterval);
    }

    async update() {
        try {
            const res = await fetch(this.endpoint);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.render(await res.json());
        } catch (err) {
            console.error('Error fetching GPU state:', err);
        }
    }

    render(data) {
        const broker = data.broker || {};
        // Show the panel if a GPU exists OR the broker is reachable.
        if (!data.available && !broker.reachable) {
            this.panel.style.display = 'none';
            return;
        }
        this.panel.style.display = 'block';

        this.renderSummary(data.device);
        this.renderProcesses(data.processes || []);
        this.renderWarning(data.unmanaged_warning);
        this.renderBroker(broker);
        this.renderAccess(data.processes || [], broker);
    }

    renderAccess(procs, broker) {
        const el = document.getElementById('gpu-access');
        if (!el) return;
        if (!broker.reachable) {
            el.innerHTML = '<span class="text-muted small">broker unavailable</span>';
            return;
        }
        // Known broker consumers plus any managed app seen on the card.
        const known = new Set(['ollama', 'comfyui', 'forge']);
        procs.forEach((p) => { if (p.managed_by) known.add(p.managed_by); });
        (broker.disabled || []).forEach((d) => known.add(d));
        const disabled = new Set(broker.disabled || []);
        el.innerHTML = [...known].sort().map((name) => {
            const off = disabled.has(name);
            const cls = off ? 'btn-outline-secondary' : 'btn-outline-success';
            const label = off ? `${this.esc(name)}: disabled` : `${this.esc(name)}: enabled`;
            return `<button type="button" class="btn btn-sm ${cls} gpu-access-toggle"
                data-consumer="${this.esc(name)}" data-enabled="${off ? '0' : '1'}">${label}</button>`;
        }).join('');
        el.querySelectorAll('.gpu-access-toggle').forEach((btn) => {
            btn.addEventListener('click', () => this.toggleAccess(btn.dataset.consumer, btn.dataset.enabled === '0'));
        });
    }

    async toggleAccess(consumer, enabled) {
        try {
            await fetch('/api/gpu/set-enabled', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ consumer, enabled }),
            });
        } catch (err) {
            console.error('Error toggling GPU access:', err);
        } finally {
            this.update();
        }
    }

    renderSummary(device) {
        const el = document.getElementById('gpu-vram-summary');
        if (!device) { el.textContent = ''; return; }
        const used = device.mem_used_mib, total = device.mem_total_mib;
        const pct = (used && total) ? ` (${Math.round(used / total * 100)}%)` : '';
        el.textContent =
            `${device.name} — VRAM ${this.mib(used)} / ${this.mib(total)}${pct}` +
            ` · ${device.util_pct ?? '?'}% util · ${device.temp_c ?? '?'}°C`;
    }

    renderProcesses(procs) {
        const el = document.getElementById('gpu-processes');
        if (!procs.length) {
            el.innerHTML = '<span class="text-muted small">Nothing resident</span>';
            return;
        }
        el.innerHTML = procs.map(p => {
            const badge = p.managed
                ? `<span class="badge bg-success">${this.esc(p.managed_by)}</span>`
                : '<span class="badge bg-warning text-dark">unmanaged</span>';
            const cmd = this.esc(p.command).slice(0, 90);
            return `<div class="d-flex align-items-center py-1" style="gap: 8px;">
                <span class="badge bg-info" style="min-width: 72px;">${this.mib(p.vram_mib)}</span>
                ${badge}
                <span class="text-muted small">PID ${p.pid}</span>
                <code class="small text-truncate" style="min-width: 0;">${cmd}</code>
            </div>`;
        }).join('');
    }

    renderWarning(show) {
        const el = document.getElementById('gpu-unmanaged-warning');
        if (show) {
            el.textContent =
                'An unmanaged app is holding significant VRAM — the broker cannot ' +
                'coordinate or evict it.';
            el.classList.remove('d-none');
        } else {
            el.classList.add('d-none');
        }
    }

    renderBroker(broker) {
        const el = document.getElementById('gpu-broker');
        const btn = document.getElementById('gpu-clear-btn');
        if (!broker.reachable) {
            el.innerHTML = '<span class="text-muted small">Redis not reachable — broker state unavailable</span>';
            btn.style.display = 'none';
            return;
        }
        if (!broker.held) {
            el.innerHTML = '<span class="text-success">Idle</span> <span class="text-muted small">(no lease held)</span>';
            btn.style.display = 'none';
            this.renderWaiters(el, broker);
            return;
        }
        const consumer = this.esc(broker.consumer || broker.kind || '?');
        const parts = [
            `Held by <strong>${consumer}</strong>`,
            `<span class="text-muted small">priority: ${this.esc(broker.priority || '?')}` +
            ` · caller: ${this.esc(broker.holder_name || '?')}</span>`,
        ];
        if (broker.hold_remaining_s != null) {
            parts.push(`<span class="text-muted small">· fair window ${broker.hold_remaining_s}s</span>`);
        }
        el.innerHTML = parts.join(' ');
        this.renderWaiters(el, broker);
        btn.style.display = 'inline-block';
    }

    renderWaiters(el, broker) {
        const w = [];
        if (broker.user_pending) w.push(`${broker.user_pending} user`);
        if (broker.bg_pending) w.push(`${broker.bg_pending} background`);
        if (w.length) {
            el.innerHTML += `<div class="text-muted small">Waiting: ${w.join(', ')}</div>`;
        }
    }

    async clearLease() {
        if (!window.confirm('Force-clear the current GPU broker lease?')) return;
        const btn = document.getElementById('gpu-clear-btn');
        btn.disabled = true;
        try {
            const res = await fetch('/api/gpu/clear', { method: 'POST' });
            const data = await res.json();
            if (!data.success) console.error('Clear failed:', data.error);
        } catch (err) {
            console.error('Error clearing lease:', err);
        } finally {
            btn.disabled = false;
            this.update();
        }
    }

    mib(mib) {
        if (mib == null) return '?';
        return mib >= 1024 ? `${(mib / 1024).toFixed(1)} GB` : `${mib} MB`;
    }

    esc(s) {
        const d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new GpuPanel(3000).init();
});
