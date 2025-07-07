#!/usr/bin/env python3

import json
import subprocess

from ..config import load_config, save_config
from .lifecycle import get_service_status

# Container Detection Functions


def detect_container_service(service_name, command):
    """Detect if service is containerized and get port info"""
    if not command:
        return None

    command_lower = command.lower()

    # Check for container runtimes in command
    if "docker" in command_lower:
        return detect_docker_ports(service_name)
    elif "podman" in command_lower:
        return detect_podman_ports(service_name)

    # Check if command is a script file that might contain container commands
    if command.endswith(".sh") or "/scripts/" in command:
        try:
            # Try to read the script and check for container commands
            script_path = command.split()[0]  # Get just the script path, not args
            with open(script_path) as f:
                script_content = f.read().lower()

            if "docker" in script_content:
                return detect_docker_ports(service_name)
            elif "podman" in script_content:
                return detect_podman_ports(service_name)

        except (OSError, FileNotFoundError, PermissionError):
            # Script not readable, fallback to direct container detection
            pass

    return None


def detect_docker_ports(service_name):
    """Get Docker container ports for service"""
    try:
        # Check if docker command is available
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            return None

        # Get running containers
        result = subprocess.run(
            ["docker", "ps", "--format", "json"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return None

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Find container by name pattern or label
        target_container = None
        for container in containers:
            names = container.get("Names", "")
            labels = container.get("Labels", "")

            # Check if service name matches container name or is in labels
            if (
                service_name in names
                or service_name in labels
                or names.replace("-", "_") == service_name.replace("-", "_")
            ):
                target_container = container
                break

        if not target_container:
            return None

        container_id = target_container["ID"]
        container_name = target_container["Names"]

        # Get port mappings using docker port
        port_result = subprocess.run(
            ["docker", "port", container_id], capture_output=True, text=True
        )

        port_mappings = {}
        internal_ports = []
        external_ports = []

        # Check network mode first to determine port detection strategy
        inspect_result = subprocess.run(
            ["docker", "inspect", container_id], capture_output=True, text=True
        )
        network_mode = "bridge"  # default
        exposed_ports = []

        if inspect_result.returncode == 0:
            try:
                inspect_data = json.loads(inspect_result.stdout)[0]
                network_mode = inspect_data.get("HostConfig", {}).get(
                    "NetworkMode", "bridge"
                )

                # Get exposed ports from container config
                config_exposed = inspect_data.get("Config", {}).get("ExposedPorts", {})
                for port_spec in config_exposed.keys():
                    port_num = port_spec.split("/")[0]
                    exposed_ports.append(port_num)

            except (json.JSONDecodeError, IndexError, KeyError):
                pass

        if network_mode == "host":
            # For host network containers, exposed ports are directly accessible
            # Use exposed ports from container configuration
            external_ports = exposed_ports
            internal_ports = exposed_ports
            for port in exposed_ports:
                port_mappings[f"{port}/tcp"] = port
        else:
            # For bridge/other networks, parse docker port output
            if port_result.returncode == 0:
                # Parse docker port output: "8080/tcp -> 0.0.0.0:3001"
                for line in port_result.stdout.strip().split("\n"):
                    if line.strip() and "->" in line:
                        internal_part, external_part = line.split(" -> ", 1)
                        internal_port = internal_part.split("/")[0]

                        # Extract external port from "0.0.0.0:3001" or ":::3001"
                        if ":" in external_part:
                            external_port = external_part.split(":")[-1]
                        else:
                            external_port = external_part

                        port_mappings[internal_part] = external_port
                        internal_ports.append(internal_port)
                        external_ports.append(external_port)

        return {
            "runtime": "docker",
            "container_id": container_id,
            "container_name": container_name,
            "network_mode": network_mode,
            "port_mappings": port_mappings,
            "internal_ports": internal_ports,
            "external_ports": external_ports,
        }

    except Exception:
        # Container detection failed, not necessarily an error
        return None


def detect_podman_ports(service_name):
    """Get Podman container ports for service"""
    try:
        # Check if podman command is available
        result = subprocess.run(["podman", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            return None

        # Get running containers (podman uses same format as docker)
        result = subprocess.run(
            ["podman", "ps", "--format", "json"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return None

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Find container by name pattern
        target_container = None
        for container in containers:
            names = container.get("Names", "")
            if service_name in names or names.replace("-", "_") == service_name.replace(
                "-", "_"
            ):
                target_container = container
                break

        if not target_container:
            return None

        container_id = target_container["Id"]
        container_name = target_container["Names"]

        # Get port mappings using podman port
        port_result = subprocess.run(
            ["podman", "port", container_id], capture_output=True, text=True
        )

        port_mappings = {}
        internal_ports = []
        external_ports = []

        if port_result.returncode == 0:
            # Parse podman port output (same format as docker)
            for line in port_result.stdout.strip().split("\n"):
                if line.strip() and "->" in line:
                    internal_part, external_part = line.split(" -> ", 1)
                    internal_port = internal_part.split("/")[0]

                    if ":" in external_part:
                        external_port = external_part.split(":")[-1]
                    else:
                        external_port = external_part

                    port_mappings[internal_part] = external_port
                    internal_ports.append(internal_port)
                    external_ports.append(external_port)

        # Check network mode
        inspect_result = subprocess.run(
            ["podman", "inspect", container_id], capture_output=True, text=True
        )
        network_mode = "bridge"  # default
        if inspect_result.returncode == 0:
            try:
                inspect_data = json.loads(inspect_result.stdout)[0]
                network_mode = inspect_data.get("HostConfig", {}).get(
                    "NetworkMode", "bridge"
                )
            except (json.JSONDecodeError, IndexError, KeyError):
                pass

        return {
            "runtime": "podman",
            "container_id": container_id,
            "container_name": container_name,
            "network_mode": network_mode,
            "port_mappings": port_mappings,
            "internal_ports": internal_ports,
            "external_ports": external_ports,
        }

    except Exception:
        return None


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
        # First, check if this is a containerized service
        config = load_config()
        service_config = config.get("services", {}).get(name, {})
        service_command = service_config.get("command", "")

        # Try container detection first
        container_info = detect_container_service(name, service_command)
        if container_info:
            # For containerized services, convert container ports to detected_ports format
            detected_ports = {}
            if container_info["external_ports"]:
                # Use container ID as PID for consistency with existing format
                container_id = container_info["container_id"][:12]  # Short ID
                for port in container_info["external_ports"]:
                    try:
                        detected_ports[container_id] = int(port)
                        break  # Use first external port as primary
                    except ValueError:
                        continue

            return {
                "detected_ports": detected_ports,
                "main_pid": None,
                "container_info": container_info,
            }

        # Fallback to traditional process detection for non-containerized services
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


def select_primary_port(detected_ports, main_pid=None, container_info=None):
    """Select primary port using smart priority logic with container support"""
    if not detected_ports:
        return None

    all_ports = list(detected_ports.values())

    # For containerized services, use container-specific logic
    if container_info:
        external_ports = container_info.get("external_ports", [])
        if external_ports:
            # Apply web heuristics to container external ports
            return apply_web_port_heuristics(
                [int(p) for p in external_ports if p.isdigit()]
            )

    # Priority 1: SystemD MainPID port (if available)
    if main_pid and main_pid in detected_ports:
        return detected_ports[main_pid]

    # Priority 2: Web port heuristic (common web ports)
    return apply_web_port_heuristics(all_ports)


def apply_web_port_heuristics(ports):
    """Apply web port selection heuristics to a list of ports"""
    if not ports:
        return None

    web_port_ranges = [
        (80, 80),
        (443, 443),  # Standard HTTP/HTTPS
        (3000, 3010),  # Development servers (React, Express, etc.)
        (5000, 5010),  # Flask, etc.
        (8000, 8090),  # Django, web servers, etc.
        (11430, 11440),  # Ollama range
    ]

    web_ports = []
    for port in ports:
        for start, end in web_port_ranges:
            if start <= port <= end:
                web_ports.append(port)
                break

    if web_ports:
        return min(web_ports)  # Lowest web port

    # Fallback: Lowest overall port
    return min(ports)


def detect_service_port(name):
    """Try to detect the actual port being used by a service (legacy function)"""
    port_data = detect_service_ports(name)
    detected_ports = port_data["detected_ports"]
    main_pid = port_data["main_pid"]
    container_info = port_data.get("container_info")

    return select_primary_port(detected_ports, main_pid, container_info)


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
        # For stopped services, validation depends on port management mode
        if port_management == "auto_detect":
            validation = "service_stopped"  # Auto-detect services don't need indicators when stopped
        else:
            validation = "unknown"  # Managed services get ? when stopped

        return {
            "status": "service_stopped",
            "configured_port": managed_port,
            "actual_port": None,
            "validation": validation,
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
