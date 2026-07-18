// GPU broker panel: pure markup builders consumed by gpu.js's GpuPanel.
// Exposed as window.GpuRender so gpu.js can stay focused on data/state.

function mib(v) {
    if (v == null) return '?';
    return v >= 1024 ? `${(v / 1024).toFixed(1)} GB` : `${v} MB`;
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
}

function barColor(pct) {
    if (pct >= 90) return 'var(--red)';
    if (pct >= 75) return 'var(--amber)';
    return 'var(--green)';
}

const ICONS = {
    chevron: (open) => `<svg class="cp-ico" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-3);transition:transform .28s cubic-bezier(.4,0,.2,1);transform:rotate(${open ? 90 : 0}deg)"><path d="m9 18 6-6-6-6"/></svg>`,
    gpuChip: () => '<svg class="cp-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-2)"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/></svg>',
    warning: () => '<svg class="cp-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-top:1px"><path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4M12 17h.01"/></svg>',
    trash: () => '<svg class="cp-ico" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>',
};

function leasePill(broker) {
    let dot, label;
    if (!broker.reachable) {
        dot = 'var(--text-3)'; label = 'Broker offline';
    } else if (broker.held) {
        dot = 'var(--accent)'; label = esc(broker.consumer || broker.kind || '?');
    } else {
        dot = 'var(--green)'; label = 'Idle';
    }
    return `<span style="display:inline-flex;align-items:center;gap:7px;height:26px;padding:0 11px;border-radius:99px;border:1px solid var(--border);background:var(--surface-inset);flex:none">
      <span style="width:7px;height:7px;border-radius:50%;flex:none;background:${dot}"></span>
      <span style="font-size:12px;font-weight:500;color:var(--text);white-space:nowrap">${label}</span>
    </span>`;
}

function header(data, broker, open) {
    const device = data.device;
    const vram = device
        ? `<span class="mono" style="font-size:12px;color:var(--text-2)" data-hide-mobile>${mib(device.mem_used_mib)} / ${mib(device.mem_total_mib)}</span>`
        : '';
    return `
    <button id="gpu-toggle" style="display:flex;align-items:center;gap:11px;width:100%;padding:13px 16px;background:transparent;border:none;cursor:pointer;text-align:left">
      ${ICONS.chevron(open)}${ICONS.gpuChip()}
      <span style="font-weight:600;font-size:14px;color:var(--text)">GPU</span>
      <span class="mono" style="font-size:12px;color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(device ? device.name : '')}</span>
      <div style="flex:1"></div>
      ${vram}
      ${leasePill(broker)}
    </button>`;
}

function vramStrip(device) {
    if (!device) return '';
    const pct = device.mem_total_mib ? Math.round(device.mem_used_mib / device.mem_total_mib * 100) : 0;
    const color = barColor(pct);
    return `
    <div style="display:flex;align-items:flex-end;gap:16px;margin-bottom:16px">
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:7px">
          <span class="cp-eyebrow">VRAM</span>
          <span class="mono" style="font-size:12.5px;color:var(--text)">${mib(device.mem_used_mib)} / ${mib(device.mem_total_mib)} <span style="color:var(--text-3)">· ${pct}%</span></span>
        </div>
        <div style="height:7px;border-radius:99px;background:var(--surface-inset);overflow:hidden">
          <div style="height:100%;border-radius:99px;transition:width .7s cubic-bezier(.4,0,.2,1);width:${pct}%;background:${color}"></div>
        </div>
      </div>
      <span class="mono" style="font-size:11.5px;color:var(--text-2);background:var(--surface-inset);border:1px solid var(--border);padding:3px 9px;border-radius:6px;flex:none">${device.util_pct ?? '?'}% util</span>
      <span class="mono" style="font-size:11.5px;color:var(--text-2);background:var(--surface-inset);border:1px solid var(--border);padding:3px 9px;border-radius:6px;flex:none">${device.temp_c ?? '?'}°C</span>
    </div>`;
}

function processRow(p) {
    const managed = !!p.managed_by;
    const badgeBg = managed ? 'var(--green-dim)' : 'var(--amber-dim)';
    const badgeFg = managed ? 'var(--green)' : 'var(--amber)';
    const badgeText = managed ? esc(p.managed_by) : 'unmanaged';
    return `
    <div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
        <span class="mono" style="font-size:11.5px;font-weight:600;color:var(--text);width:64px;flex:none">${mib(p.vram_mib)}</span>
        <span style="font-size:10.5px;font-weight:500;padding:2px 8px;border-radius:5px;flex:none;background:${badgeBg};color:${badgeFg}">${badgeText}</span>
        <span class="mono" style="font-size:10.5px;color:var(--text-3);flex:none">PID ${esc(p.pid)}</span>
        <span class="mono" style="font-size:11px;color:var(--text-2);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p.command)}</span>
      </div>
      <div class="gpu-share-track" style="height:4px;border-radius:99px;background:var(--surface-inset);overflow:hidden" data-vram="${p.vram_mib || 0}" data-color="${managed ? 'var(--green)' : 'var(--amber)'}"></div>
    </div>`;
}

function processesColumn(procs, warn) {
    const warning = warn ? `
    <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:11px;padding:9px 11px;border-radius:8px;background:var(--amber-dim);border:1px solid transparent">
      ${ICONS.warning()}
      <span style="font-size:12px;line-height:1.45;color:var(--text-2)">An <b style="color:var(--text)">unmanaged</b> process holds significant VRAM — the broker can't coordinate or evict it.</span>
    </div>` : '';
    const list = procs.length
        ? `<div style="display:flex;flex-direction:column;gap:9px">${procs.map(processRow).join('')}</div>`
        : '<span style="font-size:12.5px;color:var(--text-3)">Nothing resident</span>';
    return `
    <div style="min-width:0">
      <div class="cp-eyebrow" style="margin-bottom:9px">Resident on the card</div>
      ${warning}${list}
    </div>`;
}

function waitTime(s) {
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return rem ? `${m}m ${rem}s` : `${m}m`;
}

function priorityChip(priority) {
    const label = priority || '?';
    const accent = priority === 'user' || priority === 'high';
    const bg = accent ? 'var(--accent-soft)' : 'var(--surface-inset)';
    const fg = accent ? 'var(--accent)' : 'var(--text-3)';
    return `<span style="font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;color:${fg};background:${bg};padding:1px 6px;border-radius:5px;flex:none">${esc(label)}</span>`;
}

function waiterRow(w) {
    const name = w.holder || w.consumer || '?';
    return `
    <div style="display:flex;align-items:center;gap:8px;padding:3px 0">
      ${priorityChip(w.priority)}
      <span class="mono" style="font-size:11.5px;color:var(--text);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(name)}</span>
      <span class="mono" style="font-size:10.5px;color:var(--text-3);flex:none">waiting ${waitTime(w.waiting_s)}</span>
    </div>`;
}

function waiterQueue(broker) {
    const list = broker.waiters || [];
    if (!list.length) {
        if (!broker.user_pending && !broker.bg_pending) return '';
        const counts = [];
        if (broker.user_pending) counts.push(`${broker.user_pending} user`);
        if (broker.bg_pending) counts.push(`${broker.bg_pending} background`);
        return `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11.5px;color:var(--text-2)">Waiting: <span style="color:var(--text)">${counts.join(' · ')}</span></div>`;
    }
    const shown = list.slice(0, 6);
    const extra = list.length - shown.length;
    const extraHtml = extra > 0 ? `<div style="font-size:11px;color:var(--text-3);padding:3px 0">+${extra} more</div>` : '';
    const unaccountedHtml = broker.waiters_unaccounted > 0 ? `<div style="font-size:11px;color:var(--text-3);padding:3px 0">+${broker.waiters_unaccounted} waiting (client predates waiter registry)</div>` : '';
    return `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
      ${shown.map(waiterRow).join('')}
      ${extraHtml}${unaccountedHtml}
    </div>`;
}

function leaseBlock(broker) {
    if (!broker.reachable) {
        return `<div style="display:flex;align-items:center;gap:8px;padding:11px 13px;border-radius:9px;background:var(--surface-inset);border:1px solid var(--border)">
          <span style="width:8px;height:8px;border-radius:50%;background:var(--text-3);flex:none"></span>
          <span style="font-size:12.5px;color:var(--text-2)">Redis not reachable — broker state unavailable</span>
        </div>`;
    }
    if (!broker.held) {
        return `<div style="padding:11px 13px;border-radius:9px;background:var(--surface-inset);border:1px solid var(--border)">
          <div style="display:flex;align-items:center;gap:8px">
            <span style="width:8px;height:8px;border-radius:50%;background:var(--green);flex:none"></span>
            <span style="font-size:13px;color:var(--text)">Idle</span>
            <span style="font-size:12px;color:var(--text-3)">— the card is free</span>
          </div>
          ${waiterQueue(broker)}
        </div>`;
    }
    const meta = [];
    if (broker.holder_name != null) meta.push(`caller ${esc(broker.holder_name)}`);
    if (broker.hold_remaining_s != null) meta.push(`fair window ${broker.hold_remaining_s}s`);
    if (broker.ttl_s != null) meta.push(`TTL ${broker.ttl_s}s`);
    const highChip = broker.priority === 'high'
        ? '<span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;color:var(--accent);background:var(--accent-soft);padding:2px 7px;border-radius:5px">high</span>'
        : '';
    return `
    <div style="padding:11px 13px;border-radius:9px;background:var(--surface-inset);border:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:7px">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--accent);flex:none"></span>
        <span style="font-size:13px;color:var(--text)">Held by <b>${esc(broker.consumer || broker.kind || '?')}</b></span>
        ${highChip}
      </div>
      <div class="mono" style="display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11px;color:var(--text-3)">${meta.map((m) => `<span>${m}</span>`).join('')}</div>
      ${waiterQueue(broker)}
    </div>
    <button id="gpu-clear-btn" class="cp-btn cp-btn-danger" style="margin-top:10px">${ICONS.trash()}Clear stuck lease</button>`;
}

function accessSection(procs, broker) {
    if (!broker.reachable) return '';
    // Consumers are whatever the broker/probe have actually observed, not a
    // fixed app list: which apps talk to the broker is deployment-specific.
    const known = new Set();
    procs.forEach((p) => { if (p.managed_by) known.add(p.managed_by); });
    (broker.disabled || []).forEach((d) => known.add(d));
    if (!known.size) return '';
    const disabled = new Set(broker.disabled || []);
    const rows = [...known].sort().map((name) => {
        const off = disabled.has(name);
        const track = off ? 'var(--border-strong)' : 'var(--accent)';
        const knobX = off ? '0px' : '11px';
        return `
        <div style="display:flex;align-items:center;gap:10px;padding:7px 2px">
          <button class="gpu-access-toggle" data-consumer="${esc(name)}" data-enabled="${off ? '0' : '1'}" style="background:transparent;border:none;padding:0;cursor:pointer;flex:none">
            <span class="cp-switch" style="width:30px;height:17px;background:${track}">
              <span class="cp-switch-knob" style="width:13px;height:13px;transform:translateX(${knobX})"></span>
            </span>
          </button>
          <span class="mono" style="font-size:12.5px;color:var(--text);flex:1">${esc(name)}</span>
          <span style="font-size:11px;color:var(--text-3)">${off ? 'disabled' : 'enabled'}</span>
        </div>`;
    }).join('');
    return `
    <div style="display:flex;align-items:center;gap:6px;margin:16px 0 9px">
      <span class="cp-eyebrow">GPU access</span>
      <span class="cp-info" title="Disabling an app makes its GPU acquire fail fast in every broker-aware process, machine-wide.">i</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:2px">${rows}</div>`;
}

function brokerColumn(broker, procs) {
    return `
    <div style="min-width:0">
      <div class="cp-eyebrow" style="margin-bottom:9px">Broker lease</div>
      ${leaseBlock(broker)}
      ${accessSection(procs, broker)}
    </div>`;
}

function body(data, broker, open) {
    const rows = open ? '1fr' : '0fr';
    return `
    <div style="display:grid;grid-template-rows:${rows};transition:grid-template-rows .3s cubic-bezier(.4,0,.2,1)">
      <div style="overflow:hidden;min-height:0">
        <div style="border-top:1px solid var(--border);padding:16px">
          ${vramStrip(data.device)}
          <div class="gpu-cols" style="display:grid;gap:20px;grid-template-columns:1.15fr 1fr">
            ${processesColumn(data.processes || [], data.unmanaged_warning)}
            ${brokerColumn(broker, data.processes || [])}
          </div>
        </div>
      </div>
    </div>`;
}

window.GpuRender = { header, body, mib, esc };
