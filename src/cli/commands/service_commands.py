#!/usr/bin/env python3

import subprocess

import click

# Command group metadata
__group__ = "Service Management"

# Import from core business logic and CLI utilities
from core.config import load_config, save_config
from core.service import control_service, register_service, unregister_service

from ..completion import PORT_RANGE, SERVICE_NAME, SMART_PORT


# Custom command classes to add shortcuts with proper formatting
class RegisterCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: reg")
                break
        return "\n".join(lines)


class EditCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: e")
                break
        return "\n".join(lines)


class StartCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: st")
                break
        return "\n".join(lines)


class RestartCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: rs")
                break
        return "\n".join(lines)


class StopCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: x")
                break
        return "\n".join(lines)


@click.command(cls=RegisterCommand)
@click.option("--name", required=True, help="Service name")
@click.option("--command", required=True, help="Command to start the service")
@click.option(
    "--port",
    type=SMART_PORT,
    help="Port to run on (optional, will auto-assign if not specified)",
)
@click.option(
    "--path",
    "--dir",
    default="",
    help="Working directory/path for the service (defaults to home directory)",
)
@click.option(
    "--script-dir", help="Project directory where run_panel.sh will be created"
)
@click.option(
    "--range",
    "range_name",
    type=PORT_RANGE,
    default="default",
    help="Port range to use for auto-assignment",
)
@click.option("--env", multiple=True, help="Environment variables in KEY=VALUE format")
@click.option(
    "--auto", is_flag=True, help="Enable service to auto-start at system boot"
)
@click.option(
    "--start", is_flag=True, help="Start service immediately after registration"
)
@click.option("--nodejs", is_flag=True, help="Optimize for Node.js service")
def register(
    name, command, port, path, script_dir, range_name, env, auto, start, nodejs=False
):
    """Register a new service"""
    # For backwards compatibility - path is preferred name
    working_dir = path

    # Optimize command for Node.js if specified
    if nodejs and command.strip().startswith("node "):
        from core.node_helper import get_node_service_command

        script_path = command.replace("node ", "").strip()
        command = get_node_service_command(script_path, working_dir)
        click.echo(f"Optimized Node.js command: {command}")

    success, result = register_service(
        name, command, port, working_dir, range_name, env, script_dir
    )

    if not success:
        click.echo(f"Error: {result}")
        return

    click.echo(f"Service '{name}' registered on port {result}")

    # Auto-start configuration if requested
    if auto:
        import subprocess

        click.echo("Enabling auto-start at system boot...")
        config = load_config()
        if name in config["services"]:
            config["services"][name]["enabled"] = True
            save_config(config)
            subprocess.run(
                ["systemctl", "--user", "enable", f"control-panel@{name}.service"]
            )
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


@click.command(cls=EditCommand)
@click.argument("name", type=SERVICE_NAME)
@click.option("--command", help="New command to start the service")
@click.option("--port", type=int, help="New port number")
@click.option("--path", "--dir", help="New working directory/path")
@click.option(
    "--env-add", multiple=True, help="Add/Update environment variables (KEY=VALUE)"
)
@click.option("--env-remove", multiple=True, help="Remove environment variables (KEY)")
@click.option(
    "--detect-port", is_flag=True, help="Try to detect port from running service"
)
def edit(name, command, port, path, env_add, env_remove, detect_port):
    """Edit an existing service"""
    config = load_config()

    if name not in config["services"]:
        click.secho(f"✗ Service '{name}' not found", fg="red", bold=True)
        return

    service = config["services"][name]
    changes_made = False

    # Update command
    if command:
        service["command"] = command
        changes_made = True
        click.echo(f"📝 Updated command: {command}")

    # Update port
    if port:
        service["port"] = port
        service["env"]["PORT"] = str(port)
        changes_made = True
        click.echo(f"🔌 Updated port: {port}")

    # Detect port from running service
    if detect_port:
        from core.services.ports import detect_service_port, set_port_management_mode

        detected_port = detect_service_port(name)
        if detected_port:
            # Switch to auto-detect mode and update port
            success, message = set_port_management_mode(name, "auto_detect")
            if success:
                changes_made = True
                click.echo(
                    f"🔍 Detected port {detected_port} and switched to auto-detect mode"
                )
            else:
                click.echo(f"❌ Error setting auto-detect mode: {message}")
        else:
            click.secho("⚠ Could not detect port from running service", fg="yellow")

    # Update working directory
    if path:
        import os

        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            service["working_dir"] = expanded_path
            changes_made = True
            click.echo(f"📁 Updated working directory: {expanded_path}")
        else:
            click.secho(f"✗ Directory does not exist: {expanded_path}", fg="red")
            return

    # Add/update environment variables
    for env_var in env_add:
        if "=" not in env_var:
            click.secho(f"✗ Invalid environment variable format: {env_var}", fg="red")
            continue
        key, value = env_var.split("=", 1)
        service["env"][key] = value
        changes_made = True
        click.echo(f"🔧 Set environment variable: {key}={value}")

    # Remove environment variables
    for key in env_remove:
        if key in service["env"]:
            del service["env"][key]
            changes_made = True
            click.echo(f"🗑️ Removed environment variable: {key}")
        else:
            click.secho(f"⚠ Environment variable not found: {key}", fg="yellow")

    if changes_made:
        save_config(config)
        click.secho(f"✓ Service '{name}' updated successfully", fg="green", bold=True)
        click.echo(f"To restart with new settings: panel restart {name}")
    else:
        click.echo("No changes made")


@click.command(cls=StartCommand)
@click.argument("name", type=SERVICE_NAME)
def start(name):
    """Start a service"""
    success, error = control_service(name, "start")
    if not success:
        click.secho(
            f"✗ Failed to start {name}: {error}",
            fg="red",
            bold=True,
            color=True,
        )
        return

    click.secho(
        f"✓ Service '{name}' started successfully",
        fg="green",
        bold=True,
        color=True,
    )


@click.command(cls=StopCommand)
@click.option(
    "--force", is_flag=True, help="Force kill processes using the service port"
)
@click.argument("name", type=SERVICE_NAME)
def stop(name, force):
    """Stop a service"""
    config = load_config()

    if name not in config["services"]:
        click.secho(
            f"✗ Service '{name}' not found", fg="red", bold=True, err=True, color=True
        )
        return

    # First try to stop through systemd
    success, error = control_service(name, "stop")
    if not success:
        click.secho(f"⚠ {error}", fg="yellow")

    # Additionally kill any process that might be using the port
    port = config["services"][name]["port"]

    if force:
        from core.node_helper import kill_process_by_port

        kill_result, kill_msg = kill_process_by_port(port, force)

        if kill_result:
            click.secho(
                f"🔪 Killed processes on port {port}: {kill_msg}",
                fg="yellow",
                bold=True,
                color=True,
            )

    click.secho(
        f"✓ Service '{name}' stopped",
        fg="green",
        bold=True,
        color=True,
    )


@click.command(cls=RestartCommand)
@click.argument("name", type=SERVICE_NAME)
def restart(name):
    """Restart a service"""
    # First stop
    success, error = control_service(name, "stop")
    if not success:
        click.secho(f"⚠ Stop failed: {error}", fg="yellow")

    # Then start
    success, error = control_service(name, "start")
    if not success:
        click.secho(
            f"✗ Failed to restart {name}: {error}",
            fg="red",
            bold=True,
            color=True,
        )
        return

    click.secho(
        f"✓ Service '{name}' restarted successfully",
        fg="green",
        bold=True,
        color=True,
    )


@click.command()
@click.option(
    "--enabled",
    is_flag=True,
    help="Only restart services that have auto-start enabled",
)
def restart_all(enabled_only):
    """Restart all services (or just enabled ones)"""
    config = load_config()

    if not config["services"]:
        click.echo("No services registered")
        return

    # Filter services based on enabled_only flag
    services_to_restart = []
    for name, service in config["services"].items():
        if enabled_only:
            # Only include enabled services
            if service.get("enabled", False):
                services_to_restart.append(name)
        else:
            # Include all services
            services_to_restart.append(name)

    if not services_to_restart:
        if enabled_only:
            click.echo("No enabled services found")
        else:
            click.echo("No services to restart")
        return

    click.echo(f"Restarting {len(services_to_restart)} services...")

    failed_services = []
    for name in services_to_restart:
        click.echo(f"Restarting {name}...")

        # Stop and start the service
        success, error = control_service(name, "restart")
        if not success:
            click.secho(
                f"✗ Failed to restart {name}: {error}", fg="red", bold=True, color=True
            )
            failed_services.append(name)
        else:
            click.secho(
                f"✓ {name} restarted successfully",
                fg="green",
                bold=True,
                color=True,
            )

    # Summary
    if failed_services:
        success_count = len(services_to_restart) - len(failed_services)
        click.secho(
            f"\n✓ {success_count} services restarted successfully",
            fg="green",
            bold=True,
            color=True,
        )
        click.secho(
            f"✗ {len(failed_services)} services failed: {', '.join(failed_services)}",
            fg="red",
            bold=True,
            color=True,
        )
    else:
        click.secho(
            f"\n✓ All {len(services_to_restart)} services restarted successfully",
            fg="green",
            bold=True,
            color=True,
        )


@click.command()
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


@click.command()
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


@click.command()
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


@click.command()
@click.argument("name", type=SERVICE_NAME)
def unregister(name):
    """Unregister a service"""
    config = load_config()

    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return

    # Kill processes using the port
    port = config["services"][name]["port"]
    from core.node_helper import kill_process_by_port

    kill_process_by_port(port)

    # Unregister the service
    success, error = unregister_service(name)
    if not success:
        click.echo(f"Error: {error}")
        return

    click.echo(f"Service '{name}' unregistered")
