#!/usr/bin/env python3

"""GPU overview: physical device/process truth (nvidia-smi) plus the broker
lease view (Redis), combined into one snapshot for the CLI and web UI.
"""

from . import broker, probe

# An unmanaged process below this much VRAM is noise (display server, an idle
# app parked on the card). At or above it, an app the broker can't coordinate
# is holding real memory — worth flagging, since that is what stalls the broker.
UNMANAGED_WARN_MIB = 1024


def get_gpu_overview():
    """Single snapshot consumed by both ``panel gpu`` and ``/api/gpu``.

    ``available`` is False when nvidia-smi is absent; callers show a friendly
    "no GPU detected" instead of an error. The broker section stands alone —
    it reports ``reachable: False`` when no Redis is up, so the process view
    still works when the coordinating app is down.
    """
    if not probe.is_available():
        return {"available": False, "broker": broker.get_lease_state()}

    processes = probe.get_processes()
    unmanaged = [
        p for p in processes if not p["managed"] and (p.get("vram_mib") or 0) > 0
    ]
    notable = [p for p in unmanaged if (p.get("vram_mib") or 0) >= UNMANAGED_WARN_MIB]
    return {
        "available": True,
        "device": probe.get_device(),
        "processes": processes,
        "unmanaged": unmanaged,
        "unmanaged_warning": bool(notable),
        "broker": broker.get_lease_state(),
    }
