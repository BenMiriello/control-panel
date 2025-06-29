#!/usr/bin/env python3

import os
import click
import subprocess
import sys
import json
import webbrowser
from pathlib import Path
from tabulate import tabulate

# Import from package-relative paths
try:
    from control_panel.utils.config import load_config, save_config, CONFIG_DIR, CONFIG_FILE
    from control_panel.utils.service import register_service, unregister_service, get_service_status, control_service, detect_service_port
    from control_panel.utils.node_helper import kill_process_by_port, get_node_service_command
    PACKAGE_MODE = True
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import load_config, save_config, CONFIG_DIR, CONFIG_FILE
    from utils.service import register_service, unregister_service, get_service_status, control_service, detect_service_port
    from utils.node_helper import kill_process_by_port, get_node_service_command
    PACKAGE_MODE = False

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

# Service management commands moved to cli/management_commands.py

# Import service lifecycle commands
try:
    from control_panel.cli.service_commands import start, stop, restart, enable, disable, auto
    from control_panel.cli.management_commands import register, unregister, list, logs, edit
except ImportError:
    from cli.service_commands import start, stop, restart, enable, disable, auto
    from cli.management_commands import register, unregister, list, logs, edit

# Register service lifecycle commands
cli.add_command(start)
cli.add_command(stop)
cli.add_command(restart)
cli.add_command(enable)
cli.add_command(disable)
cli.add_command(auto)

# Register service management commands
cli.add_command(register)
cli.add_command(unregister)
cli.add_command(list)
cli.add_command(logs)
cli.add_command(edit)

# logs and unregister commands moved to cli/management_commands.py

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

@cli.command()
@click.argument('port', type=int)
def kill_port(port):
    """Kill processes using a specific port"""
    success, message = kill_process_by_port(port, force=True)
    if success:
        click.echo(f"Success: {message}")
    else:
        click.echo(f"No processes found using port {port}")

@cli.command()
@click.argument('backup_file')
def restore(backup_file):
    """Restore configuration from a backup file"""
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"Error reading backup file: {e}")
        return
    
    # Validate backup structure
    if not isinstance(backup_data, dict) or "services" not in backup_data:
        click.echo("Invalid backup file format")
        return
    
    # Create backup of current config
    config = load_config()
    timestamp = subprocess.check_output(["date", "+%Y%m%d-%H%M%S"]).decode().strip()
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"control-panel-backup-{timestamp}.json"
    
    with open(backup_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"Current configuration backed up to {backup_path}")
    
    # Restore from backup
    save_config(backup_data)
    click.echo(f"Configuration restored from {backup_file}")

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=9000, type=int, help='Port to listen on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.option('--register', is_flag=True, help='Register as a service instead of running directly')
def web(host, port, no_browser, register):
    """Start the web UI"""
    import threading
    
    # Check if the web UI is already registered as a service
    config = load_config()
    service_name = "control-panel-web"
    
    if register or service_name in config["services"]:
        # Register the web UI as a service if needed
        if service_name not in config["services"]:
            # Determine the correct command to run the web UI
            if PACKAGE_MODE:
                web_ui_command = f"panel-web --host {host} --port {port}"
            else:
                web_ui_command = f"python3 web_ui.py --host {host} --port {port}"
            
            # Register the service
            env_vars = [f"HOST={host}", f"PORT={port}"]
            success, result = register_service(service_name, web_ui_command, port, "", "default", env_vars)
            
            if not success:
                click.echo(f"Error registering web UI service: {result}")
                return
            
            click.echo(f"Web UI registered as service '{service_name}' on port {result}")
            
            # Enable auto-start
            config = load_config()
            config["services"][service_name]["enabled"] = True
            save_config(config)
            subprocess.run(["systemctl", "--user", "enable", f"control-panel@{service_name}.service"])
        
        # Start the service
        success, error = control_service(service_name, "start")
        if not success:
            click.echo(f"Error starting web UI service: {error}")
            click.echo(f"Check logs with: panel logs {service_name}")
            return
        
        click.echo(f"Web UI service '{service_name}' started on http://{host}:{port}")
        click.echo(f"View logs with: panel logs {service_name}")
        
        # Open browser if requested
        if not no_browser:
            webbrowser.open(f"http://localhost:{port}")
    else:
        # Run the web UI directly (legacy mode)
        click.echo("Starting Web UI directly (not as a service)")
        click.echo("To register as a service, use --register flag")
        
        # Import here to avoid circular imports
        try:
            from control_panel.web_ui import start_web_ui
        except ImportError:
            # Fallback to local import if package is not fully installed
            try:
                from web_ui import start_web_ui
            except ImportError:
                click.echo("Error: web_ui module not found!")
                return
        
        click.echo(f"Starting Control Panel web UI at http://{host}:{port}")
        start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)

# Export the CLI function as main for entry_point in setup.py
main = cli

if __name__ == '__main__':
    cli()
