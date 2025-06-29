#!/usr/bin/env python3

import subprocess

import click
from tabulate import tabulate

from utils.config import load_config, save_config
from utils.node_helper import get_node_service_command, kill_process_by_port
from utils.service import (
    control_service,
    get_service_status,
    register_service,
    unregister_service,
)


@click.group()
def cli():
    """Control Panel - Manage your services and ports"""
    pass


@cli.command()
@click.option("--name", required=True, help="Service name")
@click.option("--command", required=True, help="Command to start the service")
@click.option(
    "--port",
    type=int,
    help="Port to run on (optional, will auto-assign if not specified)",
)
@click.option(
    "--dir", default="", help="Working directory (defaults to home directory)"
)
@click.option(
    "--range",
    "range_name",
    default="default",
    help="Port range to use for auto-assignment",
)
@click.option("--env", multiple=True, help="Environment variables in KEY=VALUE format")
@click.option("--nodejs", is_flag=True, help="Optimize for Node.js service")
def register(name, command, port, dir, range_name, env, nodejs):
    """Register a new service"""
    # Optimize command for Node.js if specified
    if nodejs and command.strip().startswith("node "):
        script_path = command.replace("node ", "").strip()
        command = get_node_service_command(script_path, dir)
        click.echo(f"Optimized Node.js command: {command}")

    success, result = register_service(name, command, port, dir, range_name, env)

    if not success:
        click.echo(f"Error: {result}")
        return

    click.echo(f"Service '{name}' registered on port {result}")
    click.echo(f"To start: panel start {name}")
    click.echo(f"To enable at startup: panel enable {name}")


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
@click.argument("name")
def start(name):
    """Start a service"""
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error: {error}")
        return

    click.echo(f"Service '{name}' started")


@cli.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Force kill the process")
def stop(name):
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
    kill_result, kill_msg = kill_process_by_port(port)

    if kill_result:
        click.echo(f"Killed processes on port {port}: {kill_msg}")

    click.echo(f"Service '{name}' stopped")


@cli.command()
@click.argument("name")
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
@click.argument("name")
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
@click.argument("name")
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


@cli.command()
@click.argument("name")
def logs(name):
    """View logs for a service"""
    config = load_config()

    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return

    # This will follow logs until Ctrl+C is pressed
    try:
        subprocess.run(
            ["journalctl", "--user", "-f", "-u", f"control-panel@{name}.service"]
        )
    except KeyboardInterrupt:
        pass


@cli.command()
@click.argument("name")
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
@click.argument("range_name")
@click.argument("start", type=int)
@click.argument("end", type=int)
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
@click.argument("port", type=int)
def kill_port(port):
    """Kill processes using a specific port"""
    success, message = kill_process_by_port(port, force=True)
    if success:
        click.echo(f"Success: {message}")
    else:
        click.echo(f"No processes found using port {port}")


if __name__ == "__main__":
    cli()
