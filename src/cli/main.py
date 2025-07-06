#!/usr/bin/env python3

import os
from pathlib import Path
import subprocess

import click

# Import from core business logic
from core.config import load_config, save_config
from core.node_helper import kill_process_by_port
from core.service import (
    control_service,
    unregister_service,
)

# Import completion types from CLI module
from .completion import SERVICE_NAME
from .discovery import GroupedMultiCommand

# Helper functions for multi-shell completion support


def _get_config_file(shell):
    """Get the config file path for a given shell"""
    if shell == "bash":
        return os.path.expanduser("~/.bashrc")
    elif shell == "zsh":
        return os.path.expanduser("~/.zshrc")
    elif shell == "fish":
        return os.path.expanduser("~/.config/fish/config.fish")
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def _get_completion_file(shell):
    """Get completion file path for shells that use separate files"""
    if shell == "zsh":
        return os.path.expanduser("~/.panel_completion.zsh")
    return None


# Use the new grouped multi-command for automatic discovery
cli = GroupedMultiCommand(
    commands_dir=Path(__file__).parent / "commands",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Control Panel - Manage your services and ports",
)


# Add commands from control.py


@cli.command()
@click.argument("name", type=SERVICE_NAME)
def enable(name):
    """Enable a service to start automatically"""
    config = load_config()

    if name not in config["services"]:
        click.secho(
            f"✗ Service '{name}' not found", fg="red", bold=True, err=True, color=True
        )
        return

    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])

    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)

    click.secho(
        f"✓ Service '{click.style(name, fg='cyan', bold=True)}' enabled to start automatically",
        fg="green",
        bold=True,
        color=True,
    )


@cli.command()
@click.argument("name", type=SERVICE_NAME)
def disable(name):
    """Disable a service from starting automatically"""
    config = load_config()

    if name not in config["services"]:
        click.secho(
            f"✗ Service '{name}' not found", fg="red", bold=True, err=True, color=True
        )
        return

    subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"])

    # Update config
    config["services"][name]["enabled"] = False
    save_config(config)

    click.secho(
        f"✓ Service '{click.style(name, fg='cyan', bold=True)}' disabled from starting automatically",
        fg="yellow",
        bold=True,
        color=True,
    )


# Combined command that enables auto-start and starts the service (commonly used together)
@cli.command()
@click.argument("name", type=SERVICE_NAME)
def auto(name):
    """Enable a service to auto-start at system boot and start it now"""
    # First enable auto-start
    config = load_config()

    if name not in config["services"]:
        click.secho(
            f"✗ Service '{name}' not found", fg="red", bold=True, err=True, color=True
        )
        return

    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])

    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)

    click.secho(
        f"✓ Service '{click.style(name, fg='cyan', bold=True)}' enabled to start automatically",
        fg="green",
        bold=True,
        color=True,
    )

    # Now start the service
    success, error = control_service(name, "start")
    if not success:
        click.secho(
            f"✗ Error starting service: {error}",
            fg="red",
            bold=True,
            err=True,
            color=True,
        )
        click.echo(f"Check logs with: panel logs {click.style(name, fg='cyan')}")
    else:
        click.secho(
            f"✓ Service '{click.style(name, fg='cyan', bold=True)}' started successfully",
            fg="green",
            bold=True,
            color=True,
        )


@cli.command()
@click.argument("name", type=SERVICE_NAME)
@click.option("--lines", "-n", default=25, help="Number of lines to show initially")
@click.option("--follow", "-f", is_flag=True, help="Follow log output in real-time")
@click.option("--no-pager", is_flag=True, help="Don't use pager, output directly")
def logs(name, lines, follow, no_pager):
    """View service logs with scrollable paging"""
    config = load_config()

    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return

    service_name = f"control-panel@{name}.service"

    if follow:
        # Streaming mode: show last N lines, then follow
        cmd = ["journalctl", "--user", "-f", "-n", str(lines), "-u", service_name]
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            pass
    else:
        # Paged mode: show last N lines with pager for scrolling
        if no_pager:
            # Direct output without pager
            cmd = [
                "journalctl",
                "--user",
                "-n",
                str(lines),
                "-u",
                service_name,
                "--no-pager",
            ]
            subprocess.run(cmd)
        else:
            # Use less directly for paged viewing
            try:
                # First get the output
                cmd = [
                    "journalctl",
                    "--user",
                    "-n",
                    str(lines),
                    "-u",
                    service_name,
                    "--no-pager",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.stdout:
                    # Use less with proper options for paging
                    # -R: handle color codes, -S: don't wrap long lines, -X: don't clear screen on exit
                    less_proc = subprocess.Popen(
                        ["less", "-R", "-S", "-X"], stdin=subprocess.PIPE, text=True
                    )
                    less_proc.communicate(input=result.stdout)
                    less_proc.wait()

                if result.stderr:
                    click.echo(result.stderr, err=True)

            except KeyboardInterrupt:
                pass
            except FileNotFoundError:
                # Fallback if less is not available - just print
                cmd = [
                    "journalctl",
                    "--user",
                    "-n",
                    str(lines),
                    "-u",
                    service_name,
                    "--no-pager",
                ]
                subprocess.run(cmd)


@cli.command()
@click.argument("name", type=SERVICE_NAME)
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


# Command aliases
@cli.command("ls")
def ls():
    """List all registered services (alias for 'list')"""
    # Call the list command from auto-registered commands
    from commands.service_commands import list as list_command

    ctx = click.get_current_context()
    ctx.invoke(list_command.callback)


# Commands are now automatically discovered from the commands/ directory
# No manual registration needed!

# Export the CLI function as main for entry_point in setup.py
main = cli

if __name__ == "__main__":
    cli()
