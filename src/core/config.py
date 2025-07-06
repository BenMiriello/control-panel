#!/usr/bin/env python3

from datetime import datetime
import json
from pathlib import Path
import shutil

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "control-panel"
CONFIG_FILE = CONFIG_DIR / "services.json"
ENV_DIR = CONFIG_DIR / "env"
BACKUP_DIR = CONFIG_DIR / "backups"

# Ensure directories exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ENV_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


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


def backup_config():
    """Create a backup of the current configuration"""
    if CONFIG_FILE.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_file = BACKUP_DIR / f"auto-backup-{timestamp}.json"
        shutil.copy2(CONFIG_FILE, backup_file)
        return backup_file
    return None


def save_config(config):
    """Save the services configuration with automatic backup"""
    # Create backup before saving if config file exists and has services
    if CONFIG_FILE.exists():
        try:
            current_config = load_config()
            if current_config.get("services"):
                backup_config()
        except (json.JSONDecodeError, FileNotFoundError):
            # If current config is corrupted, still proceed with save
            pass

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


def create_env_file(name, service_config):
    """Create an environment file for a service"""
    env_file = ENV_DIR / f"{name}.env"
    with open(env_file, "w") as f:
        f.write(f"COMMAND={service_config['command']}\n")
        if service_config.get("working_dir"):
            f.write(f"WORKING_DIR={service_config['working_dir']}\n")
        f.write(f"PORT={service_config['port']}\n")
        for key, value in service_config.get("env", {}).items():
            f.write(f"{key}={value}\n")


def recover_from_env_files():
    """Recover services configuration from environment files"""
    import subprocess

    recovered_services = {}

    # Get list of env files
    for env_file in ENV_DIR.glob("*.env"):
        service_name = env_file.stem

        # Skip if service isn't actually running in systemd
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "is-active",
                f"control-panel@{service_name}.service",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if result.returncode != 0:
            continue  # Service not running, skip

        # Parse environment file
        env_vars = {}
        command = None
        port = None
        working_dir = "/home/simonsays"  # default

        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key == "COMMAND":
                        command = value
                    elif key == "PORT":
                        port = int(value)
                    elif key == "WORKING_DIR":
                        working_dir = value
                    else:
                        env_vars[key] = value

        if command and port:
            # Check if service is enabled for auto-start
            enabled_result = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "is-enabled",
                    f"control-panel@{service_name}.service",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            enabled = enabled_result.returncode == 0

            recovered_services[service_name] = {
                "command": command,
                "port": port,
                "working_dir": working_dir,
                "enabled": enabled,
                "env": env_vars,
            }

    return recovered_services


def recover_config():
    """Recover the full configuration from environment files and backups"""
    recovered_services = recover_from_env_files()

    # Create new config
    new_config = {
        "services": recovered_services,
        "port_ranges": {"default": {"start": 8000, "end": 9000}},
    }

    # Backup current config if it exists
    if CONFIG_FILE.exists():
        backup_config()

    # Save recovered config
    save_config(new_config)

    return len(recovered_services)
