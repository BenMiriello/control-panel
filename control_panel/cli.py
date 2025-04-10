#!/usr/bin/env python3

import click
import subprocess
import sys
import os
import shutil
import tempfile
import json
from pathlib import Path
from tabulate import tabulate

from control_panel.utils.config import load_config, save_config, CONFIG_DIR, CONFIG_FILE
from control_panel.utils.service import register_service, unregister_service, get_service_status, control_service, detect_service_port

def get_service_names():
    """Get a list of all registered service names"""
    config = load_config()
    return list(config["services"].keys())

class CompleteServices(click.ParamType):
    name = "service"
    
    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for services that match the incomplete string."""
        service_names = get_service_names()
        return [click.CompletionItem(name) for name in service_names if name.startswith(incomplete)]

class CompleteCommands(click.ParamType):
    name = "command"
    
    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for commands."""
        commands = [
            'register', 'list', 'start', 'stop', 'restart', 
            'auto', 'disable', 'logs', 'unregister', 'edit',
            'add_range', 'web', 'completion', 'backup',
            'restore', 'update', 'import_config', 'uninstall'
        ]
        return [click.CompletionItem(cmd) for cmd in commands if cmd.startswith(incomplete)]

SERVICE_NAME = CompleteServices()
COMMAND_NAME = CompleteCommands()

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass

@cli.command()
@click.option('--name', required=True, help='Service name')
@click.option('--command', required=True, help='Command to start the service')
@click.option('--port', type=int, help='Port to run on (optional, will auto-assign if not specified)')
@click.option('--path', '--dir', default='', help='Working directory/path for the service (defaults to home directory)')
@click.option('--range', 'range_name', default='default', help='Port range to use for auto-assignment')
@click.option('--env', multiple=True, help='Environment variables in KEY=VALUE format')
@click.option('--auto', is_flag=True, help='Enable service to auto-start at system boot')
@click.option('--start', is_flag=True, help='Start service immediately after registration')
def register(name, command, port, path, range_name, env, auto, start):
    """Register a new service"""
    # For backwards compatibility - path is preferred name
    working_dir = path
    
    success, result = register_service(name, command, port, working_dir, range_name, env)
    
    if not success:
        click.echo(f"Error: {result}")
        return
    
    click.echo(f"Service '{name}' registered on port {result}")
    
    # Auto-start configuration if requested
    if auto:
        click.echo("Enabling auto-start at system boot...")
        config = load_config()
        if name in config["services"]:
            config["services"][name]["enabled"] = True
            save_config(config)
            subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
            click.echo(f"Service '{name}' will auto-start at system boot")
    
    # Start immediately if requested
    if start or auto:  # Auto implies start
        click.echo(f"Starting service '{name}'...")
        success, error = control_service(name, "start")
        if not success:
            click.echo(f"Error starting service: {error}")
            click.echo(f"Check logs with: panel logs {name}")
        else:
            click.echo(f"Service '{name}' started successfully")
    else:
        click.echo(f"To start: panel start {name}")
        click.echo(f"To enable auto-start: panel auto {name}")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
@click.option('--command', help='New command to start the service')
@click.option('--port', type=int, help='New port number')
@click.option('--path', '--dir', help='New working directory/path')
@click.option('--env-add', multiple=True, help='Add/Update environment variables (KEY=VALUE)')
@click.option('--env-remove', multiple=True, help='Remove environment variables (KEY)')
@click.option('--detect-port', is_flag=True, help='Try to detect port from running service')
def edit(name, command, port, path, env_add, env_remove, detect_port):
    """Edit an existing service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    service = config["services"][name]
    
    # For backwards compatibility - path is preferred now
    working_dir = path
    
    # Update command if provided
    if command:
        service["command"] = command
        click.echo(f"Updated command to: {command}")
    
    # Update working directory if provided
    if working_dir:
        service["working_dir"] = working_dir
        click.echo(f"Updated path to: {working_dir}")
    
    # Try to detect port if requested
    if detect_port:
        detected_port = detect_service_port(name)
        if detected_port:
            click.echo(f"Detected port: {detected_port}")
            service["port"] = detected_port
            port = detected_port  # Update port variable for env update
        else:
            click.echo("Service is not running or no port detected")
    # Update port if provided
    elif port:
        service["port"] = port
        click.echo(f"Updated port to: {port}")
    
    # Initialize environment variables if not present
    if "env" not in service:
        service["env"] = {}
    
    # Add or update environment variables
    for env_var in env_add:
        if '=' in env_var:
            key, value = env_var.split('=', 1)
            service["env"][key] = value
            click.echo(f"Added/updated environment variable: {key}={value}")
    
    # Remove environment variables
    for key in env_remove:
        if key in service["env"]:
            del service["env"][key]
            click.echo(f"Removed environment variable: {key}")
    
    # Always update PORT in environment
    if port or detect_port:
        service["env"]["PORT"] = str(service["port"])
    
    # Save updated configuration
    save_config(config)
    
    # Update environment file
    env_dir = CONFIG_DIR / "env"
    env_file = env_dir / f"{name}.env"
    with open(env_file, 'w') as f:
        f.write(f"COMMAND={service['command']}\n")
        f.write(f"PORT={service['port']}\n")
        for key, value in service.get("env", {}).items():
            f.write(f"{key}={value}\n")
    
    click.echo(f"Service '{name}' updated successfully")
    click.echo("You will need to restart the service for changes to take effect:")
    click.echo(f"  panel restart {name}")
