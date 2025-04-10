#!/usr/bin/env python3

import click
import subprocess

from control_panel.utils.config import load_config, save_config
from control_panel.utils.service import control_service

from control_panel.cli import cli, SERVICE_NAME

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def auto(name):
    """Enable a service to auto-start at system boot and start it now"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    # Enable the service at boot
    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)
    
    click.echo(f"Service '{name}' set to auto-start at system boot")
    
    # Also start it now
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error starting service: {error}")
        click.echo(f"To check logs: panel logs {name}")
    else:
        click.echo(f"Service '{name}' has been started")

# Keep "enable" for backwards compatibility, but mark as deprecated
@cli.command(hidden=True)
@click.argument('name', type=SERVICE_NAME)
def enable(name):
    """[DEPRECATED] Use 'auto' instead to enable auto-start"""
    click.echo("Note: 'panel enable' is deprecated, please use 'panel auto' instead.")
    auto.callback(name)

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def disable(name):
    """Disable a service from auto-starting at system boot"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = False
    save_config(config)
    
    click.echo(f"Service '{name}' disabled from auto-starting at system boot")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
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
