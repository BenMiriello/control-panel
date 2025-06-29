#!/usr/bin/env python3

import subprocess

import click
from tabulate import tabulate

from control_panel.cli import SERVICE_NAME, cli
from control_panel.utils.config import load_config
from control_panel.utils.service import control_service, get_service_status


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
        try:
            status, enabled = get_service_status(name)
            enabled_mark = "✓" if enabled else ""

            # Add path to display
            rows.append(
                [
                    name,
                    service["port"],
                    status,
                    enabled_mark,
                    service.get("working_dir", ""),
                    service["command"],
                ]
            )
        except Exception:
            # Handle errors gracefully
            rows.append(
                [
                    name,
                    service["port"],
                    "error",
                    "",
                    service.get("working_dir", ""),
                    service["command"],
                ]
            )

    # Sort by name
    rows.sort(key=lambda x: x[0])

    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Path", "Command"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))


@cli.command()
@click.argument("name", type=SERVICE_NAME)
@click.option("--log", is_flag=True, help="Show service logs after starting")
def start(name, log):
    """Start a service"""
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error: {error}")
        click.echo(f"To check logs: panel logs {name}")
        return

    click.echo(f"Service '{name}' started")

    if log:
        click.echo("Showing logs (press Ctrl+C to exit):")
        try:
            subprocess.run(
                [
                    "journalctl",
                    "--user",
                    "-f",
                    "-n",
                    "50",
                    "-u",
                    f"control-panel@{name}.service",
                ]
            )
        except KeyboardInterrupt:
            pass


@cli.command()
@click.argument("name", type=SERVICE_NAME)
def stop(name):
    """Stop a service"""
    success, error = control_service(name, "stop")
    if not success:
        click.echo(f"Error: {error}")
        click.echo(f"To check logs: panel logs {name}")
        return

    click.echo(f"Service '{name}' stopped")


@cli.command()
@click.argument("name", type=SERVICE_NAME)
@click.option("--log", is_flag=True, help="Show service logs after restarting")
def restart(name, log):
    """Restart a service"""
    success, error = control_service(name, "restart")
    if not success:
        click.echo(f"Error: {error}")
        click.echo(f"To check logs: panel logs {name}")
        return

    click.echo(f"Service '{name}' restarted")

    if log:
        click.echo("Showing logs (press Ctrl+C to exit):")
        try:
            subprocess.run(
                [
                    "journalctl",
                    "--user",
                    "-f",
                    "-n",
                    "50",
                    "-u",
                    f"control-panel@{name}.service",
                ]
            )
        except KeyboardInterrupt:
            pass
