#!/usr/bin/env python3

from ..config import load_config
from .lifecycle import get_service_status
from .ports import get_service_port_status


def build_service_list(config=None):
    """Build the detailed service list used by the dashboard and API"""
    if config is None:
        config = load_config()

    services = []
    for name, service in config["services"].items():
        status, enabled = get_service_status(name)
        port_status = get_service_port_status(name)

        services.append(
            {
                "name": name,
                "port": service["port"],
                "command": service["command"],
                "status": status,
                "enabled": enabled,
                "port_status": port_status,
                "working_dir": service.get("working_dir", ""),
                "env": service.get("env", {}),
                "last_started": service.get("last_started"),
            }
        )

    return sort_services(services)


def sort_services(services):
    """Sort services: running first (alphabetical), then stopped by
    last_started descending (never-started services last, alphabetical
    among ties)"""
    running = sorted(
        (s for s in services if s["status"] == "active"),
        key=lambda s: s["name"],
    )

    # Stable sort: alphabetical first, then descending by last_started so
    # ties (identical timestamps) remain alphabetical
    stopped_with_timestamp = sorted(
        (s for s in services if s["status"] != "active" and s["last_started"]),
        key=lambda s: s["name"],
    )
    stopped_with_timestamp.sort(key=lambda s: s["last_started"], reverse=True)
    stopped_without_timestamp = sorted(
        (s for s in services if s["status"] != "active" and not s["last_started"]),
        key=lambda s: s["name"],
    )

    return running + stopped_with_timestamp + stopped_without_timestamp
