// GPU broker panel: polls /api/gpu and renders the whole card into #gpu-panel.
// Markup builders live in gpu-render.js (window.GpuRender) to keep this file
// focused on polling, open/close state, and event wiring.

class GpuPanel {
    constructor(refreshInterval = 3000) {
        this.refreshInterval = refreshInterval;
        this.endpoint = '/api/gpu';
        this.intervalId = null;
        this.panel = document.getElementById('gpu-panel');
        this.open = localStorage.getItem('panel-gpu-open') !== '0';
    }

    init() {
        if (!this.panel) return;
        this.injectResponsiveStyle();
        this.update();
        this.intervalId = setInterval(() => this.update(), this.refreshInterval);
    }

    injectResponsiveStyle() {
        if (document.getElementById('gpu-panel-responsive-style')) return;
        const style = document.createElement('style');
        style.id = 'gpu-panel-responsive-style';
        style.textContent = `
            @media (max-width: 680px) {
                #gpu-panel [data-hide-mobile] { display: none; }
                #gpu-panel .gpu-cols { grid-template-columns: 1fr !important; }
            }`;
        document.head.appendChild(style);
    }

    async update() {
        try {
            const res = await fetch(this.endpoint);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this.data = await res.json();
            this.render();
        } catch (err) {
            console.error('Error fetching GPU state:', err);
        }
    }

    render() {
        const data = this.data;
        const broker = data.broker || {};
        if (!data.available && !broker.reachable) {
            this.panel.style.display = 'none';
            return;
        }
        this.panel.style.display = 'block';
        if (!this.panel.dataset.gpuStyled) {
            this.panel.style.cssText += ';background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow-sm);overflow:hidden';
            this.panel.dataset.gpuStyled = '1';
        }
        this.panel.innerHTML = GpuRender.header(data, broker, this.open) + GpuRender.body(data, broker, this.open);
        this.bind(data);
    }

    bind(data) {
        const toggle = document.getElementById('gpu-toggle');
        if (toggle) toggle.addEventListener('click', () => {
            this.open = !this.open;
            localStorage.setItem('panel-gpu-open', this.open ? '1' : '0');
            this.render();
        });
        const clearBtn = document.getElementById('gpu-clear-btn');
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearLease());
        this.panel.querySelectorAll('.gpu-access-toggle').forEach((btn) => {
            btn.addEventListener('click', () => this.toggleAccess(btn.dataset.consumer, btn.dataset.enabled === '0'));
        });
        this.panel.querySelectorAll('.gpu-share-track').forEach((track) => {
            const total = data.device ? data.device.mem_total_mib : 0;
            const vram = Number(track.dataset.vram);
            const pct = total ? Math.min(100, Math.round(vram / total * 100)) : 0;
            track.innerHTML = `<div style="height:100%;border-radius:99px;width:${pct}%;background:${track.dataset.color}"></div>`;
        });
    }

    async clearLease() {
        if (!window.confirm('Force-clear the current GPU broker lease?')) return;
        try {
            const res = await fetch('/api/gpu/clear', { method: 'POST' });
            const data = await res.json();
            if (!data.success) console.error('Clear failed:', data.error);
        } catch (err) {
            console.error('Error clearing lease:', err);
        } finally {
            this.update();
        }
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
}

document.addEventListener('DOMContentLoaded', () => {
    new GpuPanel(3000).init();
});
