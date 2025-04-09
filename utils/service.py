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
        capture_output=True, text=True
    )
    status = result.stdout.strip() if result.returncode == 0 else "inactive"
    
    # Check if enabled at boot
    result = subprocess.run(
        ["systemctl", "--user", "is-enabled", f"control-panel@{name}.service"],
        capture_output=True, text=True, stderr=subprocess.DEVNULL
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
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        return False, f"Failed to {action} service: {result.stderr}"
    
    return True, None
