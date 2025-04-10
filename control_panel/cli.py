#!/usr/bin/env python3

import os
import click
import subprocess
import sys
import shutil
import tempfile
import json
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

@cli.command()
@click.option('--name', required=True, help='Service name')
@click.option('--command', required=True, help='Command to start the service')
@click.option('--port', type=int, help='Port to run on (optional, will auto-assign if not specified)')
@click.option('--path', '--dir', default='', help='Working directory/path for the service (defaults to home directory)')
@click.option('--range', 'range_name', default='default', help='Port range to use for auto-assignment')
@click.option('--env', multiple=True, help='Environment variables in KEY=VALUE format')
@click.option('--auto', is_flag=True, help='Enable service to auto-start at system boot')
@click.option('--start', is_flag=True, help='Start service immediately after registration')
@click.option('--nodejs', is_flag=True, help='Optimize for Node.js service')
def register(name, command, port, path, range_name, env, auto, start, nodejs=False):
    """Register a new service"""
    # For backwards compatibility - path is preferred name
    working_dir = path
    
    # Optimize command for Node.js if specified
    if nodejs and command.strip().startswith("node "):
        script_path = command.replace("node ", "").strip()
        command = get_node_service_command(script_path, working_dir)
        click.echo(f"Optimized Node.js command: {command}")
    
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

# Add commands from control.py
@cli.command()
def list():
    """List all registered services"""
    config = load_config()
    
    if not config["services"]:
        click.echo("No services registered")
        return
    
    # Get status for each service
    rows = []
    for name, service in config["services"].items():
        status, enabled = get_service_status(name)
        enabled_mark = "✓" if enabled else ""
        
        rows.append([name, service["port"], status, enabled_mark, service["command"]])
    
    # Sort by name
    rows.sort(key=lambda x: x[0])
    
    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))

@cli.command()
@click.argument('name')
def start(name):
    """Start a service"""
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error: {error}")
        return
    
    click.echo(f"Service '{name}' started")

@cli.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Force kill the process')
def stop(name, force=False):
    """Stop a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
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

@cli.command()
@click.argument('name')
def restart(name):
    """Restart a service"""
    # First stop (with cleanup)
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
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

@cli.command()
@click.argument('name')
def enable(name):
    """Enable a service to start automatically"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)
    
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
    
    # Update config
    config["services"][name]["enabled"] = False
    save_config(config)
    
    click.echo(f"Service '{name}' disabled from starting automatically")

# Combined command that enables auto-start and starts the service (commonly used together)
@cli.command()
@click.argument('name')
def auto(name):
    """Enable a service to auto-start at system boot and start it now"""
    # First enable auto-start
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
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
    
    # Kill processes using the port
    port = config["services"][name]["port"]
    kill_process_by_port(port)
    
    # Unregister the service
    success, error = unregister_service(name)
    if not success:
        click.echo(f"Error: {error}")
        return
    
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
