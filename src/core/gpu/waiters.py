#!/usr/bin/env python3

"""Optional waiter-registry reader for the GPU broker's ``gpu:waiters`` zset.

Split out of ``broker.py`` to keep that file within the project's file-size
guideline. See gpu-broker's README ("Waiter registry (observability, optional)")
for the protocol this mirrors: a zset of JSON members written by acquirers
while they are blocked in the acquire loop, never by the holder.
"""

import json


def get_waiters(
    redis_fn,
    parse_lease_id,
    now,
    waiters_key,
    holder,
    holder_priority,
    user_pending,
    bg_pending,
):
    """Prune and read the waiter registry, reconciled against the pending
    counters. Returns ``(waiters, waiters_unaccounted)``.

    ``redis_fn`` is the caller's ``_redis(*args)`` shell-out, ``parse_lease_id``
    is the caller's lease-id parser, and ``now`` is the current unix time.
    Harmlessly returns ``([], 0)`` when the key is absent (legacy namespace,
    unreachable broker, or an older broker that never writes it).
    """
    redis_fn("zremrangebyscore", waiters_key, "-inf", str(now))
    raw = redis_fn("zrange", waiters_key, "0", "-1")
    members = raw.split("\n") if raw else []

    waiters = []
    for member in members:
        if not member:
            continue
        try:
            data = json.loads(member)
        except (TypeError, ValueError):
            continue
        lease_id = data.get("lease_id")
        if not lease_id or lease_id == holder:
            continue
        parsed = parse_lease_id(lease_id)
        enqueued_at = _float_or_none(data.get("enqueued_at")) or now
        waiters.append(
            {
                "lease_id": lease_id,
                "kind": parsed.get("kind"),
                "priority": parsed.get("priority"),
                "holder": parsed.get("holder"),
                "consumer": data.get("consumer"),
                "host": parsed.get("host"),
                "pid": parsed.get("pid"),
                "enqueued_at": enqueued_at,
                "waiting_s": max(0, int(now - enqueued_at)),
            }
        )
    waiters.sort(key=lambda w: w["enqueued_at"])

    holder_share = 1 if holder_priority in ("user", "background") else 0
    known_ub = sum(1 for w in waiters if w["priority"] in ("user", "background"))
    counted = user_pending + bg_pending
    unaccounted = max(0, counted - holder_share - known_ub)
    return waiters, unaccounted


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
