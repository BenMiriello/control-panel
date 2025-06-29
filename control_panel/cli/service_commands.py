#!/usr/bin/env python3

import click
import subprocess
from pathlib import Path

# Import from package-relative paths
try:
    from control_panel.utils.config import load_config, save_config
    from control_panel.utils.service import control_service
    from control_panel.utils.node_helper import kill_process_by_port
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import load_config, save_config
    from utils.service import control_service
    from utils.node_helper import kill_process_by_port

def validate_service_exists(name):
    """Validate that a service exists in configuration"""
    config = load_config()
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return False, None
    return True, config

@click.command()
@click.argument('name')
def start(name):
    """Start a service"""
    exists, _ = validate_service_exists(name)
    if not exists:
        return
    
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error: {error}")
        return
    
    click.echo(f"Service '{name}' started")

@click.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Force kill the process')
def stop(name, force=False):
    """Stop a service"""
    exists, config = validate_service_exists(name)
    if not exists:
        return
    
    # First try to stop through systemd
    success, error = control_service(name, "stop")
    if not success:
        click.echo(f"Warning: {error}")
    
    # Additionally kill any process that might be using the port
    port = config["services"][name]["port"]
    kill_result, kill_msg = kill_process_by_port(port, force)
    
    if kill_result:
        click.echo(f"Killed processes on port {port}: {kill_msg}")
    
    click.echo(f"Service '{name}' stopped")

@click.command()
@click.argument('name')
def restart(name):
    """Restart a service"""
    exists, config = validate_service_exists(name)
    if not exists:
        return
    
    # Stop service and kill processes
    success, error = control_service(name, "stop")
    port = config["services"][name]["port"]
    kill_process_by_port(port)
    
    # Start service again
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error restarting: {error}")
        return
    
    click.echo(f"Service '{name}' restarted")

@click.command()
@click.argument('name')
def enable(name):
    """Enable a service to start automatically"""
    exists, config = validate_service_exists(name)
    if not exists:
        return
    
    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)
    
    click.echo(f"Service '{name}' enabled to start automatically")

@click.command()
@click.argument('name')
def disable(name):
    """Disable a service from starting automatically"""
    exists, config = validate_service_exists(name)
    if not exists:
        return
    
    subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = False
    save_config(config)
    
    click.echo(f"Service '{name}' disabled from starting automatically")

@click.command()
@click.argument('name')
def auto(name):
    """Enable a service to auto-start at system boot and start it now"""
    exists, config = validate_service_exists(name)
    if not exists:
        return
    
    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)
    
    click.echo(f"Service '{name}' enabled to start automatically")
    
    # Now start the service
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error starting service: {error}")
        click.echo(f"Check logs with: panel logs {name}")
    else:
        click.echo(f"Service '{name}' started successfully")