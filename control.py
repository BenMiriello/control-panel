#!/usr/bin/env python3

import os
import json
import click
import subprocess
import signal
import sys
from pathlib import Path
from tabulate import tabulate

CONFIG_DIR = Path.home() / ".config" / "control-panel"
CONFIG_FILE = CONFIG_DIR / "services.json"
ENV_DIR = CONFIG_DIR / "env"

# Ensure directories exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ENV_DIR.mkdir(parents=True, exist_ok=True)

# Initialize configuration if it doesn't exist
if not CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'w') as f:
        json.dump({
            "services": {},
            "port_ranges": {"default": {"start": 8000, "end": 9000}}
        }, f, indent=2)

def load_config():
    """Load the services configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save the services configuration"""
    with open(CONFIG_FILE, 'w') as f:
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

@click.group()
def cli():
    """Control Panel - Manage your services and ports"""
    pass

@cli.command()
@click.option('--name', required=True, help='Service name')
@click.option('--command', required=True, help='Command to start the service')
@click.option('--port', type=int, help='Port to run on (optional, will auto-assign if not specified)')
@click.option('--dir', default='', help='Working directory (defaults to home directory)')
@click.option('--range', 'range_name', default='default', help='Port range to use for auto-assignment')
@click.option('--env', multiple=True, help='Environment variables in KEY=VALUE format')
def register(name, command, port, dir, range_name, env):
    """Register a new service"""
    config = load_config()
    
    # Validate the service doesn't already exist
    if name in config["services"]:
        click.echo(f"Error: Service '{name}' already exists")
        return
    
    # Auto-assign port if not specified
    if not port:
        if range_name not in config["port_ranges"]:
            click.echo(f"Error: Port range '{range_name}' not defined")
            return
        
        port = find_available_port(config["port_ranges"][range_name])
    
    # Create the service configuration
    service_config = {
        "command": command,
        "port": port,
        "working_dir": dir or str(Path.home()),
        "enabled": True,
        "env": {}
    }
    
    # Process environment variables
    for env_var in env:
        if '=' in env_var:
            key, value = env_var.split('=', 1)
            service_config["env"][key] = value
    
    # Always add the PORT to environment
    service_config["env"]["PORT"] = str(port)
    
    # Add to config
    config["services"][name] = service_config
    save_config(config)
    
    # Create environment file
    env_file = ENV_DIR / f"{name}.env"
    with open(env_file, 'w') as f:
        f.write(f"COMMAND={command}\n")
        f.write(f"PORT={port}\n")
        for key, value in service_config["env"].items():
            f.write(f"{key}={value}\n")
    
    click.echo(f"Service '{name}' registered on port {port}")
    click.echo(f"To start: ./control.py start {name}")
    click.echo(f"To enable at startup: ./control.py enable {name}")

@cli.command()
def list():
    """List all registered services"""
    config = load_config()
    
    if not config["services"]:
        click.echo("No services registered")
        return
    
    # Get systemd status for each service
    rows = []
    for name, service in config["services"].items():
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
        enabled = "✓" if result.returncode == 0 else ""
        
        rows.append([name, service["port"], status, enabled, service["command"]])
    
    # Sort by name
    rows.sort(key=lambda x: x[0])
    
    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))

@cli.command()
@click.argument('name')
def start(name):
    """Start a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "start", f"control-panel@{name}.service"])
    click.echo(f"Service '{name}' started")

@cli.command()
@click.argument('name')
def stop(name):
    """Stop a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "stop", f"control-panel@{name}.service"])
    click.echo(f"Service '{name}' stopped")

@cli.command()
@click.argument('name')
def restart(name):
    """Restart a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "restart", f"control-panel@{name}.service"])
    click.echo(f"Service '{name}' restarted")

@cli.command()
@click.argument('name')
def enable(name):
    """Enable a service to start automatically"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
    click.echo(f"Service '{name}' enabled to start automatically")

@cli.command()
@click.argument('name')
def disable(name):
    """Disable a service from starting automatically"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"])
    click.echo(f"Service '{name}' disabled from starting automatically")

@cli.command()
@click.argument('name')
def logs(name):
    """View logs for a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    # This will follow logs until Ctrl+C is pressed
    try:
        subprocess.run(["journalctl", "--user", "-f", "-u", f"control-panel@{name}.service"])
    except KeyboardInterrupt:
        pass

@cli.command()
@click.argument('name')
def unregister(name):
    """Unregister a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
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
    
    click.echo(f"Service '{name}' unregistered")

@cli.command()
@click.argument('range_name')
@click.argument('start', type=int)
@click.argument('end', type=int)
def add_range(range_name, start, end):
    """Add a new port range"""
    if end <= start:
        click.echo("Error: End port must be greater than start port")
        return
    
    config = load_config()
    config["port_ranges"][range_name] = {"start": start, "end": end}
    save_config(config)
    
    click.echo(f"Port range '{range_name}' added: {start}-{end}")

if __name__ == '__main__':
    cli()
