#!/usr/bin/env python3

import subprocess
from pathlib import Path
from .config import load_config, save_config, find_available_port, create_env_file, ENV_DIR

def register_service(name, command, port, working_dir, range_name, env_vars):
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
        "env": {}
    }
    
    # Process environment variables
    for env_var in env_vars:
        if '=' in env_var:
            key, value = env_var.split('=', 1)
            service_config["env"][key] = value
    
    # Always add the PORT to environment
    service_config["env"]["PORT"] = str(port)
    
    # Add to config
    config["services"][name] = service_config
    save_config(config)
    
    # Create environment file
    create_env_file(name, service_config)
    
    return True, port

def unregister_service(name):
    """Unregister a service"""
    config = load_config()
    
    if name not in config["services"]:
        return False, f"Service '{name}' not found"
    
    # Stop and disable the service first
    subprocess.run(["systemctl", "--user", "stop", f"control-panel@{name}.service"], 
                  stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"],
                  stderr=subprocess.DEVNULL)
    
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
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    status = result.stdout.strip() if result.returncode == 0 else "inactive"
    
    # Check if enabled at boot
    result = subprocess.run(
        ["systemctl", "--user", "is-enabled", f"control-panel@{name}.service"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    enabled = result.returncode == 0
    
    return status, enabled

def control_service(name, action):
    """Control a service (start, stop, restart)"""
    config = load_config()
    
    if name not in config["services"]:
        return False, f"Service '{name}' not found"
    
    result = subprocess.run(
        ["systemctl", "--user", action, f"control-panel@{name}.service"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
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
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def detect_service_port(name):
    """Try to detect the actual port being used by a service"""
    try:
        # Get process ID
        result = subprocess.run(
            ["systemctl", "--user", "show", f"control-panel@{name}.service", "-p", "MainPID", "--value"],
            capture_output=True, text=True, check=True
        )
        pid = result.stdout.strip()
        
        if pid and pid != "0":
            # Get listening ports for this PID
            result = subprocess.run(
                ["lsof", "-i", "-P", "-n", "-a", "-p", pid],
                capture_output=True, text=True
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
