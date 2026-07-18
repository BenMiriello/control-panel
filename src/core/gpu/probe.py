#!/usr/bin/env python3

"""Physical GPU truth via nvidia-smi: memory, utilization, and the processes
actually resident on the card.

This is the process-agnostic ground truth — it sees every app holding VRAM
regardless of whether the broker knows about it. That gap (broker-managed vs
unmanaged) is exactly what we surface, since an unmanaged process holding the
card is the classic cause of a broker headroom stall / OOM.
"""

import json
import os
import subprocess

try:
    import psutil
except ImportError:
    psutil = None


def _load_managed_markers():
    """Substrings that identify a process as a known broker-managed GPU
    consumer, keyed by lowercase command-line substring -> consumer name.
    Everything else holding VRAM is reported as unmanaged.

    Configured per-machine via CONTROL_PANEL_GPU_MARKERS (a JSON object),
    since which apps are broker-managed consumers is deployment-specific,
    not something this tool should assume.
    """
    raw = os.environ.get("CONTROL_PANEL_GPU_MARKERS")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {str(k).lower(): str(v) for k, v in data.items()}
    except (TypeError, ValueError):
        return {}


_MANAGED_MARKERS = _load_managed_markers()


def is_available():
    """True if nvidia-smi is present and responds."""
    return _smi("--query-gpu=name", "--format=csv,noheader") is not None


def _smi(*args, timeout=3.0):
    try:
        result = subprocess.run(
            ["nvidia-smi", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _int_or_none(value):
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return None


def get_device():
    """Device-level snapshot: name, memory (MiB), utilization %, temperature."""
    out = _smi(
        "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    )
    if not out:
        return None
    parts = [p.strip() for p in out.split("\n")[0].split(",")]
    if len(parts) < 5:
        return None
    return {
        "name": parts[0],
        "mem_used_mib": _int_or_none(parts[1]),
        "mem_total_mib": _int_or_none(parts[2]),
        "util_pct": _int_or_none(parts[3]),
        "temp_c": _int_or_none(parts[4]),
    }


def _classify(command):
    """Map a process command line to a managed consumer name, or None."""
    lowered = command.lower()
    for marker, consumer in _MANAGED_MARKERS.items():
        if marker in lowered:
            return consumer
    return None


def _resolve(pid):
    """Best-effort (name, command) for a pid via psutil."""
    if psutil is None:
        return None, None
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        try:
            command = " ".join(proc.cmdline()) or name
        except (psutil.AccessDenied, psutil.ZombieProcess):
            command = name
        return name, command
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return None, None


def get_processes():
    """Processes resident on the GPU, each with resolved command and whether a
    broker-managed consumer accounts for it."""
    out = _smi(
        "--query-compute-apps=pid,used_memory",
        "--format=csv,noheader,nounits",
    )
    if out is None:
        return []
    processes = []
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        pid = _int_or_none(parts[0]) if parts else None
        if pid is None:
            continue
        vram = _int_or_none(parts[1]) if len(parts) > 1 else None
        name, command = _resolve(pid)
        consumer = _classify(command or name or "")
        processes.append(
            {
                "pid": pid,
                "vram_mib": vram,
                "name": name or "(unknown)",
                "command": command or name or "(unknown)",
                "managed_by": consumer,
                "managed": consumer is not None,
            }
        )
    processes.sort(key=lambda p: p.get("vram_mib") or 0, reverse=True)
    return processes
