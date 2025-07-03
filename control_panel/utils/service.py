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


def detect_service_port(name):
    """Try to detect the actual port being used by a service"""
    try:
        # Get process ID
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
        pid = result.stdout.strip()

        if pid and pid != "0":
            # Get listening ports for this PID
            result = subprocess.run(
                ["lsof", "-i", "-P", "-n", "-a", "-p", pid],
                capture_output=True,
                text=True,
            )

            for line in result.stdout.splitlines():
                if "LISTEN" in line:
                    parts = line.split()
                    if len(parts) >= 9:
                        addr_port = parts[8].split(":")
                        if len(addr_port) >= 2:
                            try:
                                detected_port = int(addr_port[-1])
                                return detected_port
                            except ValueError:
                                pass
        return None
    except Exception:
        return None


def get_service_port_status(name):
    """Get comprehensive port status for a service"""
    config = load_config()

    if name not in config["services"]:
        return {
            "status": "service_not_found",
            "configured_port": None,
            "actual_port": None,
            "validation": "error",
            "port_type": "unknown",
        }

    service = config["services"][name]
    configured_port = service.get("port")

    # Check if service is running
    status, _ = get_service_status(name)

    if status != "active":
        return {
            "status": "service_stopped",
            "configured_port": configured_port,
            "actual_port": None,
            "validation": "unknown",
            "port_type": "configured" if configured_port else "none",
        }

    # Detect actual port
    actual_port = detect_service_port(name)

    # Determine port validation status and type
    if actual_port is None:
        validation = "no_port_detected"
        port_type = "none"
    elif configured_port is None:
        validation = "dynamic_port"
        port_type = "dynamic"
    elif actual_port == configured_port:
        validation = "port_matches"
        port_type = "configured_static"
    else:
        validation = "port_mismatch"
        port_type = "configured_mismatch"

    return {
        "status": "service_running",
        "configured_port": configured_port,
        "actual_port": actual_port,
        "validation": validation,
        "port_type": port_type,
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


def set_port_mode(name, mode, port=None):
    """Set port mode for a service (static or dynamic)"""
    config = load_config()

    if name not in config["services"]:
        return False, f"Service '{name}' not found"

    service = config["services"][name]

    if mode == "static":
        if port is None:
            return False, "Port must be specified for static mode"
        service["port"] = port
        service["env"]["PORT"] = str(port)
        # Add metadata to track port mode
        service["port_mode"] = "static"
    elif mode == "dynamic":
        # Keep current port if detected, but mark as dynamic
        service["port_mode"] = "dynamic"
        # Don't set PORT env var for dynamic services
        if "PORT" in service["env"]:
            del service["env"]["PORT"]
    else:
        return False, f"Unknown port mode: {mode}"

    save_config(config)
    return True, f"Port mode set to {mode}"


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
