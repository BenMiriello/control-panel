#!/usr/bin/env python3

"""Read-only view (and force-clear) of the GPU broker's lease state.

The broker itself lives in another project (intergen) as a Redis-backed
coordinator for the single GPU. Its coordination state is entirely in Redis,
so any process that speaks to the same keys can observe it — that is what lets
Control Panel show "who holds the card" and clear a wedged lease even when the
owning app is down.

We talk to Redis through the ``redis-cli`` binary rather than a Python client,
matching how the rest of Control Panel shells out to systemctl / nvidia-smi and
keeping the dependency set unchanged.

Key names are centralized here on purpose: if the broker's namespace is ever
neutralized (e.g. ``intergen:gpu:*`` -> ``gpu:*`` so non-intergen apps can
coordinate through it), this is the single place to update.
"""

import os
import subprocess

from . import waiters as _waiters

# Control Panel is a compliant consumer of the standalone gpu-broker (see
# ~/Documents/gpu-broker). The broker's authority lives in Redis keys, so we
# observe/clear by reading those keys directly via redis-cli — matching how the
# rest of Control Panel shells out to systemctl / nvidia-smi, and keeping the
# dependency set unchanged.
#
# Two things are discovered at runtime: WHICH Redis instance (intergen's broker
# runs on a second Redis while other apps use 6379) and WHICH namespace. During
# the migration both the neutral shared namespace and intergen's legacy one may
# exist; we prefer the neutral one and fall back to legacy, so Control Panel
# keeps working before, during, and after each app's cutover with no edit here.
#
# Override the instance with CONTROL_PANEL_GPU_REDIS_PORT.
_CANDIDATE_PORTS = ["6380", "6379"]

# Per-namespace key maps. Counter key names differ between the shared library
# and intergen's legacy broker, so this is a full map, not a prefix swap.
_NAMESPACES = {
    "gpu": {
        "holder": "gpu:holder",
        "lease_meta": "gpu:lease_meta",
        "user_pending": "gpu:user_pending",
        "bg_pending": "gpu:bg_pending",
        "activity_hint": "gpu:activity_hint",
        "disabled": "gpu:disabled",
        "waiters": "gpu:waiters",
    },
    "intergen:gpu": {
        "holder": "intergen:gpu:holder",
        "lease_meta": "intergen:gpu:lease_meta",
        "user_pending": "intergen:gpu:user_lease_count",
        "bg_pending": "intergen:gpu:bg_lease_count",
        "activity_hint": "intergen:user_activity_hint",
        "disabled": "intergen:gpu:disabled",
        "waiters": "intergen:gpu:waiters",
    },
}
# Preference order: neutral shared namespace wins over legacy intergen.
_NAMESPACE_ORDER = ["gpu", "intergen:gpu"]

_resolved = None  # cached (port, namespace_name) tuple


def _redis_raw(port, *args, timeout=3.0):
    """Run redis-cli against a specific port, returning stdout or None."""
    try:
        result = subprocess.run(
            ["redis-cli", "-p", str(port), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _has_keys(port, ns):
    """True if this instance carries the ``ns`` broker namespace's holder key
    family (probed via the persistent lease_meta / holder / epoch keys)."""
    out = _redis_raw(port, "--scan", "--pattern", f"{ns}:*")
    return bool(out)


def _resolve():
    """Find (port, namespace) for the live broker. Env pins the port; the
    namespace is discovered, preferring the neutral shared one. Falls back to
    the first responding port + legacy namespace. Cached per process."""
    global _resolved
    if _resolved is not None:
        return _resolved

    override = os.environ.get("CONTROL_PANEL_GPU_REDIS_PORT")
    ports = [override] if override else list(_CANDIDATE_PORTS)

    responding = None
    for port in ports:
        if _redis_raw(port, "ping") != "PONG":
            continue
        if responding is None:
            responding = port
        for ns in _NAMESPACE_ORDER:
            if _has_keys(port, ns):
                _resolved = (port, ns)
                return _resolved
    _resolved = (responding, "intergen:gpu") if responding else None
    return _resolved


def _keys():
    """Resolved key map for the live namespace, or None if no Redis."""
    target = _resolve()
    if target is None:
        return None
    return _NAMESPACES[target[1]]


def _redis(*args, timeout=3.0):
    """Run redis-cli against the resolved broker instance."""
    target = _resolve()
    if target is None:
        return None
    return _redis_raw(target[0], *args, timeout=timeout)


def is_reachable():
    """True if the broker's Redis instance answers PING."""
    return _resolve() is not None


def _parse_lease_id(lease_id):
    """Break a lease id into its parts.

    Format: ``kind:priority:holder:host:pid:nonce`` (newer) or
    ``kind:priority:holder:nonce`` (legacy, no owner token).
    """
    if not lease_id:
        return {}
    parts = lease_id.split(":")
    info = {"kind": parts[0] if parts else None}
    if len(parts) >= 2:
        info["priority"] = parts[1]
    if len(parts) >= 3:
        info["holder"] = parts[2]
    if len(parts) >= 5:
        info["host"] = parts[-3]
        info["pid"] = parts[-2]
    return info


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_lease_state():
    """Snapshot of the broker lease, or ``{"reachable": False}`` if no Redis.

    Fields mirror what a waiter/operator needs: which consumer holds the card,
    the caller and priority, how much of its fair hold window remains, the
    liveness TTL, and how many user/background waiters are queued.
    """
    k = _keys()
    if k is None:
        return {"reachable": False, "waiters": [], "waiters_unaccounted": 0}

    holder = _redis("get", k["holder"]) or None
    ttl = _int_or_none(_redis("ttl", k["holder"]))
    user_pending = _int_or_none(_redis("get", k["user_pending"])) or 0
    bg_pending = _int_or_none(_redis("get", k["bg_pending"])) or 0

    disabled_raw = _redis("smembers", k["disabled"])
    disabled = sorted(disabled_raw.split("\n")) if disabled_raw else []

    state = {
        "reachable": True,
        "held": bool(holder),
        "holder": holder,
        "ttl_s": ttl if (ttl is not None and ttl >= 0) else None,
        "user_pending": user_pending,
        "bg_pending": bg_pending,
        "disabled": disabled,
        "consumer": None,
        "kind": None,
        "priority": None,
        "holder_name": None,
        "hold_remaining_s": None,
        "epoch": None,
    }
    if holder:
        parsed = _parse_lease_id(holder)
        state["kind"] = parsed.get("kind")
        state["priority"] = parsed.get("priority")
        state["holder_name"] = parsed.get("holder")

        meta = _redis("hgetall", k["lease_meta"])
        if meta:
            lines = meta.split("\n")
            fields = {
                lines[i].strip(): lines[i + 1].strip()
                for i in range(0, len(lines) - 1, 2)
            }
            # Only trust meta that describes the CURRENT holder.
            if fields.get("lease_id") == holder:
                state["consumer"] = fields.get("consumer")
                state["priority"] = fields.get("priority") or state["priority"]
                state["epoch"] = _int_or_none(fields.get("epoch"))
                hold_until = _float_or_none(fields.get("hold_until"))
                if hold_until is not None:
                    state["hold_remaining_s"] = int(hold_until - _now())

    waiter_list, unaccounted = _waiters.get_waiters(
        _redis,
        _parse_lease_id,
        _now(),
        k["waiters"],
        holder,
        state["priority"],
        user_pending,
        bg_pending,
    )
    state["waiters"] = waiter_list
    state["waiters_unaccounted"] = unaccounted
    return state


def clear_lease():
    """Force-clear the broker lease + pending counters. Returns True on success.

    Equivalent to the broker's own force clear: wipe the holder, its metadata,
    and the pending counters (the monotonic lease epoch is left intact). Use
    when a crashed worker left a ghost lease wedging the card.
    """
    k = _keys()
    if k is None:
        return False
    clearable = [
        k["holder"],
        k["lease_meta"],
        k["user_pending"],
        k["bg_pending"],
        k["activity_hint"],
        k["waiters"],
    ]
    return _redis("del", *clearable) is not None


def set_enabled(consumer, enabled):
    """Enable or disable a consumer's GPU access via the broker's disabled set.

    A disabled consumer's ``acquire`` fails fast in every app that speaks the
    broker protocol, so this turns an app's GPU access off machine-wide.
    """
    k = _keys()
    if k is None:
        return False
    op = "srem" if enabled else "sadd"
    return _redis(op, k["disabled"], consumer) is not None


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _now():
    import time

    return time.time()
