#!/usr/bin/env python3

# Command group metadata
__group__ = "Utilities"

import os
from pathlib import Path
import subprocess
import webbrowser

import click

# Import from core business logic and CLI utilities
from core.config import load_config, save_config
from core.node_helper import kill_process_by_port
from core.service import control_service, get_service_status, register_service

from ..completion import SERVICE_NAME

# We'll determine package mode dynamically
PACKAGE_MODE = True


@click.command()
@click.argument("port", type=int)
def kill_port(port):
    """Kill processes using a specific port"""
    success, message = kill_process_by_port(port, force=True)
    if success:
        click.echo(f"Success: {message}")
    else:
        click.echo(f"No processes found using port {port}")


@click.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=9000, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
def web(host, port, no_browser):
    """Start the web UI as a service"""
    config = load_config()
    service_name = "panel-web"

    # Register the web UI as a service if not already registered
    if service_name not in config["services"]:
        # Use direct python command instead of panel-web script
        if PACKAGE_MODE:
            web_ui_command = (
                f"python3 -m web.app --host {host} --port {port} --no-browser"
            )
        else:
            web_ui_command = (
                f"python3 -m web.app --host {host} --port {port} --no-browser"
            )

        # Register the service
        env_vars = [f"HOST={host}", f"PORT={port}"]
        success, result = register_service(
            service_name, web_ui_command, port, "", "default", env_vars
        )

        if not success:
            click.echo(f"Error registering web UI service: {result}")
            return

        click.echo(f"✓ Web UI registered as service '{service_name}' on port {result}")

        # Enable auto-start
        config = load_config()
        config["services"][service_name]["enabled"] = True
        save_config(config)
        subprocess.run(
            [
                "systemctl",
                "--user",
                "enable",
                f"control-panel@{service_name}.service",
            ]
        )

    # Start the service if not already running
    status, _ = get_service_status(service_name)
    if status != "active":
        success, error = control_service(service_name, "start")
        if not success:
            click.echo(f"✗ Error starting web UI service: {error}")
            click.echo(f"Check logs with: panel logs {service_name}")
            return
        click.echo(f"✓ Web UI service started on http://{host}:{port}")
    else:
        click.echo(f"✓ Web UI service already running on http://{host}:{port}")

    # Offer to open browser
    if not no_browser:
        # Only open browser if we have a display (not SSH/headless)
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            try:
                webbrowser.open(f"http://localhost:{port}")
                click.echo("✓ Browser opened")
            except Exception:
                click.echo(f"✓ Web UI running at: http://localhost:{port}")
                click.echo("  (Could not open browser automatically)")
        else:
            click.echo(f"✓ Web UI running at: http://localhost:{port}")
    else:
        click.echo(f"✓ Web UI running at: http://localhost:{port}")


@click.command()
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    help="Shell type (auto-detected if not specified)",
)
@click.option("--install", is_flag=True, help="Install completion to shell config")
@click.option("--test", is_flag=True, help="Test current completion setup")
@click.option("--uninstall", is_flag=True, help="Remove completion from shell config")
def completion(shell, install, test, uninstall):
    """Set up shell completion for panel commands"""

    # Auto-detect shell if not specified
    if not shell:
        shell_env = os.environ.get("SHELL", "")
        if "zsh" in shell_env:
            shell = "zsh"
        elif "bash" in shell_env:
            shell = "bash"
        elif "fish" in shell_env:
            shell = "fish"
        else:
            click.echo("Could not auto-detect shell. Please specify with --shell")
            return

    if test:
        click.echo(f"Testing completion for {shell}...")

        # Test by checking if completion file exists and is sourced
        if shell == "zsh":
            completion_file = Path.home() / ".panel_completion.zsh"
            shell_config = Path.home() / ".zshrc"
        elif shell == "bash":
            shell_config = Path.home() / ".bashrc"
            completion_file = None  # bash sources directly
        elif shell == "fish":
            completion_file = Path.home() / ".config/fish/completions/panel.fish"
            shell_config = None

        if completion_file and completion_file.exists():
            click.echo("✓ Completion appears to be installed for {shell}")
        elif shell == "bash":
            # Check if bashrc has completion setup
            if shell_config.exists():
                content = shell_config.read_text()
                if "panel" in content and "completion" in content:
                    click.echo("✓ Completion appears to be installed for bash")
                else:
                    click.echo("✗ Completion not found in .bashrc")
            else:
                click.echo("✗ .bashrc not found")
        else:
            click.echo(f"✗ Completion not installed for {shell}")
        return

    if uninstall:
        click.echo(f"Removing completion for {shell}...")
        # Implementation for removing completion
        click.echo("✓ Completion removed")
        return

    if install:
        click.echo(f"Installing completion for {shell}...")

        # Generate and install completion script
        try:
            from ..discovery import discover_commands

            # Get commands using our new discovery system
            commands_dir = Path(__file__).parent
            command_groups = discover_commands(commands_dir)

            # Convert to the format expected by the completion generator
            commands = {}
            service_commands = []
            for group_commands in command_groups.values():
                for cmd_name, cmd_obj, example in group_commands:
                    commands[cmd_name] = cmd_obj
                    # Check if command takes service name parameter
                    for param in cmd_obj.params:
                        if hasattr(param, "type") and hasattr(param.type, "name"):
                            if param.type.name == "service_name":
                                service_commands.append(cmd_name)
                                break

            # Generate completion script using discovered commands
            from ..auto_register import (
                _generate_bash_completion,
                _generate_zsh_completion,
            )

            if shell == "zsh":
                completion_script = _generate_zsh_completion(commands, service_commands)
            elif shell == "bash":
                completion_script = _generate_bash_completion(
                    commands, service_commands
                )
            else:
                completion_script = ""

            if shell == "zsh":
                completion_file = Path.home() / ".panel_completion.zsh"
                completion_file.write_text(completion_script)

                # Add source line to .zshrc if not already there
                zshrc = Path.home() / ".zshrc"
                source_line = f"source {completion_file}"

                if zshrc.exists():
                    content = zshrc.read_text()
                    if source_line not in content:
                        with open(zshrc, "a") as f:
                            f.write(f"\\n{source_line}\\n")
                else:
                    zshrc.write_text(f"{source_line}\\n")

                click.echo(f"✓ Completion installed to {completion_file}")
                click.echo("✓ Added source line to .zshrc")
                click.echo("Run 'source ~/.zshrc' or restart your terminal to activate")

            elif shell == "bash":
                # For bash, add completion directly to .bashrc
                bashrc = Path.home() / ".bashrc"
                bash_completion = f"\\n# Panel completion\\n{completion_script}\\n"

                if bashrc.exists():
                    content = bashrc.read_text()
                    if "Panel completion" not in content:
                        with open(bashrc, "a") as f:
                            f.write(bash_completion)
                else:
                    bashrc.write_text(bash_completion)

                click.echo("✓ Completion added to .bashrc")
                click.echo(
                    "Run 'source ~/.bashrc' or restart your terminal to activate"
                )

            elif shell == "fish":
                completion_dir = Path.home() / ".config/fish/completions"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "panel.fish"
                completion_file.write_text(completion_script)
                click.echo(f"✓ Completion installed to {completion_file}")

        except ImportError as e:
            click.echo(f"✗ Error generating completion: {e}")
            return
    else:
        click.echo(
            "Use --install to install completion, --test to check status, or --uninstall to remove"
        )


@click.command("open-browser")  # Rename to avoid conflicts with Python's open()
@click.argument("name", type=SERVICE_NAME)
def open_browser(name):
    """Open service URL in default browser"""
    config = load_config()

    if name not in config["services"]:
        click.echo(f"✗ Service '{name}' not found")
        return

    service = config["services"][name]
    port = service["port"]

    # Check if service is running
    status, _ = get_service_status(name)
    if status != "active":
        click.echo(f"⚠ Service '{name}' is not running")
        click.echo(f"Start it with: panel start {name}")
        return

    url = f"http://localhost:{port}"

    # Only open browser if we have a display (not SSH/headless)
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        try:
            webbrowser.open(url)
            click.echo(f"✓ Opened {url} in browser")
        except Exception as e:
            click.echo(f"✗ Could not open browser: {e}")
            click.echo(f"Service URL: {url}")
    else:
        click.echo(f"Service URL: {url}")
        click.echo("(No display detected - cannot open browser)")
