#!/usr/bin/env python3

import subprocess

from ..config import load_config, save_config
from .lifecycle import get_service_status


def check_service_running(name, port):
    """Check if a service is actually running on the given port"""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def detect_service_ports(name):
    """Detect all ports used by a service and its process group with PID relationships"""
    try:
        # Get main process ID from systemd
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                f"control-panel@{name}.service",
                "-p",
                "MainPID",
                "--value",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        main_pid = result.stdout.strip()

        if not main_pid or main_pid == "0":
            return {"detected_ports": {}, "main_pid": None}

        # Get process group ID
        try:
            result = subprocess.run(
                ["ps", "-o", "pgid=", "-p", main_pid],
                capture_output=True,
                text=True,
            )
            pgid = result.stdout.strip()
        except Exception:
            pgid = main_pid

        # Get all processes in the process group
        result = subprocess.run(
            ["pgrep", "-g", pgid],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Fallback to just main PID if pgrep fails
            all_pids = [main_pid]
        else:
            all_pids = [
                pid.strip() for pid in result.stdout.splitlines() if pid.strip()
            ]

        detected_ports = {}

        if all_pids:
            # Scan all PIDs for listening ports using lsof
            pid_list = ",".join(all_pids)
            result = subprocess.run(
                ["lsof", "-i", "-P", "-n", "-a", "-p", pid_list],
                capture_output=True,
                text=True,
            )

            # Parse lsof output
            for line in result.stdout.splitlines():
                if "LISTEN" in line:
                    parts = line.split()
                    if len(parts) >= 9:
                        pid = parts[1]
                        addr_port = parts[8].split(":")
                        if len(addr_port) >= 2:
                            try:
                                port = int(addr_port[-1])
                                detected_ports[pid] = port
                            except ValueError:
                                pass

        return {
            "detected_ports": detected_ports,
            "main_pid": main_pid,
            "all_pids": all_pids,
        }
    except Exception:
        return {"detected_ports": {}, "main_pid": None}


def select_primary_port(detected_ports, main_pid=None):
    """Select primary port using smart priority logic"""
    if not detected_ports:
        return None

    all_ports = list(detected_ports.values())

    # Priority 1: SystemD MainPID port (if available)
    if main_pid and main_pid in detected_ports:
        return detected_ports[main_pid]

    # Priority 2: Web port heuristic (common web ports)
    web_port_ranges = [
        (80, 80),
        (443, 443),  # Standard HTTP/HTTPS
        (3000, 3010),  # Development servers (React, Express, etc.)
        (5000, 5010),  # Flask, etc.
        (8000, 8090),  # Django, web servers, etc.
    ]

    web_ports = []
    for port in all_ports:
        for start, end in web_port_ranges:
            if start <= port <= end:
                web_ports.append(port)
                break

    if web_ports:
        return min(web_ports)  # Lowest web port

    # Priority 3: Lowest overall port (fallback)
    return min(all_ports)


def detect_service_port(name):
    """Try to detect the actual port being used by a service (legacy function)"""
    port_data = detect_service_ports(name)
    detected_ports = port_data["detected_ports"]
    main_pid = port_data["main_pid"]

    return select_primary_port(detected_ports, main_pid)


def get_service_port_status(name):
    """Get comprehensive port status for a service with enhanced port management modes"""
    config = load_config()

    if name not in config["services"]:
        return {
            "status": "service_not_found",
            "configured_port": None,
            "actual_port": None,
            "validation": "error",
            "port_management": "unknown",
            "managed_port": None,
            "primary_port": None,
        }

    service = config["services"][name]

    # Get port management configuration
    port_management = service.get(
        "port_management", "managed"
    )  # Default to managed mode
    managed_port = service.get("managed_port") or service.get(
        "port"
    )  # Fallback to legacy port

    # Check if service is running
    status, _ = get_service_status(name)

    if status != "active":
        return {
            "status": "service_stopped",
            "configured_port": managed_port,
            "actual_port": None,
            "validation": "unknown",
            "port_management": port_management,
            "managed_port": managed_port,
            "primary_port": managed_port,
        }

    # Get enhanced port detection data
    port_data = detect_service_ports(name)
    detected_ports = port_data["detected_ports"]
    main_pid = port_data["main_pid"]

    # Select primary port using smart selection
    primary_port = select_primary_port(detected_ports, main_pid)

    # Determine validation based on port management mode
    if port_management == "managed":
        # In managed mode, compare detected port to user's managed_port
        if primary_port is None:
            validation = "no_port_detected"
        elif managed_port is None:
            validation = "no_managed_port_set"
        elif primary_port == managed_port:
            validation = "port_matches"
        else:
            validation = "port_mismatch"
    else:  # auto_detect mode
        # In auto_detect mode, we just report what we found
        if primary_port is None:
            validation = "no_port_detected"
        else:
            validation = "dynamic_port"

    return {
        "status": "service_running",
        "configured_port": managed_port,  # Legacy compatibility
        "actual_port": primary_port,
        "validation": validation,
        "port_management": port_management,
        "managed_port": managed_port,
        "primary_port": primary_port,
        "detected_ports": detected_ports,
        "main_pid": main_pid,
    }


def validate_service_port(name):
    """Validate that a service is using its configured port"""
    port_status = get_service_port_status(name)

    if port_status["validation"] == "port_matches":
        return True, "Service is using configured port"
    elif port_status["validation"] == "port_mismatch":
        return (
            False,
            f"Service using port {port_status['actual_port']} but configured for {port_status['configured_port']}",
        )
    elif port_status["validation"] == "no_port_detected":
        return False, "Service is running but no port detected"
    elif port_status["validation"] == "dynamic_port":
        return True, f"Service using dynamic port {port_status['actual_port']}"
    else:
        return False, f"Service validation failed: {port_status['status']}"


def set_port_management_mode(name, mode, managed_port=None):
    """Set port management mode for a service (managed or auto_detect)"""
    config = load_config()

    if name not in config["services"]:
        return False, f"Service '{name}' not found"

    service = config["services"][name]

    if mode == "managed":
        # Managed mode: user controls port, service should respect it
        if managed_port is not None:
            service["managed_port"] = managed_port
            service["port"] = managed_port  # Legacy compatibility
            service["env"]["PORT"] = str(managed_port)
        elif "managed_port" not in service and "port" in service:
            # Migrate legacy port to managed_port
            service["managed_port"] = service["port"]

        service["port_management"] = "managed"

    elif mode == "auto_detect":
        # Auto-detect mode: system finds port, user doesn't control it
        service["port_management"] = "auto_detect"
        # Preserve managed_port for when user switches back
        if "managed_port" not in service and "port" in service:
            service["managed_port"] = service["port"]
        # Remove PORT env var since service determines its own port
        if "PORT" in service.get("env", {}):
            del service["env"]["PORT"]
    else:
        return False, f"Unknown port management mode: {mode}"

    save_config(config)
    return True, f"Port management mode set to {mode}"


def set_port_mode(name, mode, port=None):
    """Legacy function - redirects to new port management system"""
    if mode == "static":
        return set_port_management_mode(name, "managed", port)
    elif mode == "dynamic":
        return set_port_management_mode(name, "auto_detect")
    else:
        return False, f"Unknown port mode: {mode}"
