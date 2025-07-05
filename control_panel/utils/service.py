#!/usr/bin/env python3

from pathlib import Path
import subprocess

from .config import (
    ENV_DIR,
    create_env_file,
    find_available_port,
    load_config,
    save_config,
)
from .script_manager import create_run_script, get_effective_command


def register_service(
    name, command, port, working_dir, range_name, env_vars, project_dir=None
):
    """Register a new service"""
    config = load_config()

    # Validate the service doesn't already exist
    if name in config["services"]:
        return False, f"Service '{name}' already exists"

    # Auto-assign port if not specified
    if not port:
        if range_name not in config["port_ranges"]:
            return False, f"Port range '{range_name}' not defined"

        try:
            port = find_available_port(config["port_ranges"][range_name])
        except ValueError as e:
            return False, str(e)

    # Create the service configuration
    service_config = {
        "command": command,
        "port": port,
        "working_dir": working_dir or str(Path.home()),
        "enabled": False,
        "env": {},
        "project_dir": project_dir,  # Add optional project directory
    }

    # Process environment variables
    for env_var in env_vars:
        if "=" in env_var:
            key, value = env_var.split("=", 1)
            service_config["env"][key] = value

    # Always add the PORT to environment
    service_config["env"]["PORT"] = str(port)

    # Add to config
    config["services"][name] = service_config
    save_config(config)

    # Create environment file
    create_env_file(name, service_config)

    # Create run_panel.sh if project_dir is specified
    if project_dir:
        success, result = create_run_script(name, service_config, project_dir)
        if not success:
            # Log warning but don't fail registration
            print(f"Warning: Could not create run_panel.sh: {result}")

    return True, port


def unregister_service(name):
    """Unregister a service"""
    config = load_config()

    if name not in config["services"]:
        return False, f"Service '{name}' not found"

    # Stop and disable the service first
    subprocess.run(
        ["systemctl", "--user", "stop", f"control-panel@{name}.service"],
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["systemctl", "--user", "disable", f"control-panel@{name}.service"],
        stderr=subprocess.DEVNULL,
    )

    # Remove the service from configuration
    del config["services"][name]
    save_config(config)

    # Remove environment file
    env_file = ENV_DIR / f"{name}.env"
    if env_file.exists():
        env_file.unlink()

    return True, None


def get_service_status(name):
    """Get the status of a service"""
    # Check if the service is active
    result = subprocess.run(
        ["systemctl", "--user", "is-active", f"control-panel@{name}.service"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    status = result.stdout.strip() if result.returncode == 0 else "inactive"

    # Check if enabled at boot
    result = subprocess.run(
        ["systemctl", "--user", "is-enabled", f"control-panel@{name}.service"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    enabled = result.returncode == 0

    return status, enabled


def control_service(name, action):
    """Control a service (start, stop, restart)"""
    config = load_config()

    if name not in config["services"]:
        return False, f"Service '{name}' not found"

    # Update environment file with effective command before starting
    if action in ["start", "restart"]:
        service_config = config["services"][name]
        effective_command = get_effective_command(name, service_config)
        create_env_file(name, service_config, effective_command)

    result = subprocess.run(
        ["systemctl", "--user", action, f"control-panel@{name}.service"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        return False, f"Failed to {action} service: {result.stderr}"

    # If we're starting a service and it has a port, update if actual port differs
    if action == "start":
        # Wait a moment for the service to start
        import time

        time.sleep(1)

        # Try to detect the actual port
        port = detect_service_port(name)
        if port is not None and port != config["services"][name]["port"]:
            # Update the port in configuration
            config["services"][name]["port"] = port
            config["services"][name]["env"]["PORT"] = str(port)
            save_config(config)

            # Update environment file
            create_env_file(name, config["services"][name])

    return True, None


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


def rename_service(old_name, new_name):
    """Rename a service and update all related configurations"""
    import re
    import subprocess

    from .config import load_config, save_config

    # Validate new name
    if not re.match(r"^[a-zA-Z0-9_-]+$", new_name):
        return (
            False,
            "Service name can only contain letters, numbers, hyphens, and underscores",
        )

    if len(new_name) > 50:
        return False, "Service name must be 50 characters or less"

    if new_name == old_name:
        return True, "No change needed"

    # Load config
    config = load_config()

    if old_name not in config["services"]:
        return False, f"Service '{old_name}' not found"

    if new_name in config["services"]:
        return False, f"Service '{new_name}' already exists"

    try:
        # Get current service status
        status, enabled = get_service_status(old_name)

        # Stop the old service if running
        if status == "active":
            success, error = control_service(old_name, "stop")
            if not success:
                return False, f"Failed to stop service: {error}"

        # Disable the old service
        if enabled:
            subprocess.run(
                ["systemctl", "--user", "disable", f"control-panel@{old_name}.service"],
                check=False,
            )

        # Copy service configuration to new name
        config["services"][new_name] = config["services"][old_name].copy()

        # Remove old service from config
        del config["services"][old_name]

        # Save updated config
        save_config(config)

        # If the service was enabled, enable the new one
        if enabled:
            subprocess.run(
                ["systemctl", "--user", "enable", f"control-panel@{new_name}.service"],
                check=False,
            )

        # If the service was running, start the new one
        if status == "active":
            success, error = control_service(new_name, "start")
            if not success:
                # Rollback on failure
                config["services"][old_name] = config["services"][new_name].copy()
                del config["services"][new_name]
                save_config(config)
                return False, f"Failed to start renamed service: {error}"

        return True, f"Service renamed from '{old_name}' to '{new_name}'"

    except Exception as e:
        # Rollback on any error
        if new_name in config["services"]:
            del config["services"][new_name]
        save_config(config)
        return False, f"Error renaming service: {str(e)}"
