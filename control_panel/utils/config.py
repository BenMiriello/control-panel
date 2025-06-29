#!/usr/bin/env python3

import json
from pathlib import Path

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "control-panel"
CONFIG_FILE = CONFIG_DIR / "services.json"
ENV_DIR = CONFIG_DIR / "env"

# Ensure directories exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ENV_DIR.mkdir(parents=True, exist_ok=True)


def initialize_config():
    """Initialize the configuration file if it doesn't exist"""
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            json.dump(
                {
                    "services": {},
                    "port_ranges": {"default": {"start": 8000, "end": 9000}},
                },
                f,
                indent=2,
            )
        return True
    return False


def load_config():
    """Load the services configuration"""
    initialize_config()
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config):
    """Save the services configuration"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def find_available_port(port_range):
    """Find the next available port in the given range"""
    config = load_config()
    start, end = port_range["start"], port_range["end"]

    # Get all ports already in use
    used_ports = [service.get("port", 0) for service in config["services"].values()]

    # Find the first available port
    for port in range(start, end + 1):
        if port not in used_ports:
            return port

    raise ValueError(f"No available ports in range {start}-{end}")


def create_env_file(name, service_config, effective_command=None):
    """Create an environment file for a service"""
    env_file = ENV_DIR / f"{name}.env"
    command = effective_command or service_config["command"]
    working_dir = service_config.get("working_dir", str(Path.home()))
    with open(env_file, "w") as f:
        f.write(f"COMMAND={command}\n")
        f.write(f"WORKING_DIR={working_dir}\n")
        f.write(f"PORT={service_config['port']}\n")
        for key, value in service_config.get("env", {}).items():
            f.write(f"{key}={value}\n")
