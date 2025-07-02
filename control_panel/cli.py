#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import webbrowser

import click
from click.shell_completion import CompletionItem
from tabulate import tabulate

# Import from package-relative paths
try:
    from control_panel.utils.config import CONFIG_DIR, load_config, save_config
    from control_panel.utils.node_helper import (
        get_node_service_command,
        kill_process_by_port,
    )
    from control_panel.utils.service import (
        control_service,
        detect_service_port,
        get_service_status,
        register_service,
        unregister_service,
    )

    PACKAGE_MODE = True
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import CONFIG_DIR, load_config, save_config
    from utils.node_helper import get_node_service_command, kill_process_by_port
    from utils.service import (
        control_service,
        detect_service_port,
        get_service_status,
        register_service,
        unregister_service,
    )

    PACKAGE_MODE = False


# Helper functions for multi-shell completion support


def _get_config_file(shell):
    """Get the config file path for a given shell"""
    import os

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
    import os

    if shell == "zsh":
        return os.path.expanduser("~/.panel_completion.zsh")
    return None


class CompleteCommands(click.ParamType):
    name = "command"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for commands."""
        commands = [
            "register",
            "list",
            "ls",
            "ps",
            "start",
            "stop",
            "restart",
            "restart-all",
            "auto",
            "disable",
            "logs",
            "open",
            "unregister",
            "edit",
            "add_range",
            "web",
            "completion",
            "backup",
            "restore",
            "update",
            "import_config",
            "uninstall",
        ]
        return [CompletionItem(cmd) for cmd in commands if cmd.startswith(incomplete)]


class CompletePortRanges(click.ParamType):
    name = "port_range"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for port ranges."""
        try:
            config = load_config()
            ranges = list(config["port_ranges"].keys())
            return [
                CompletionItem(range_name)
                for range_name in ranges
                if range_name.startswith(incomplete)
            ]
        except Exception:
            return []


class CompleteSmartPorts(click.ParamType):
    name = "port"

    def shell_complete(self, ctx, param, incomplete):
        """Return smart port suggestions based on available ranges."""
        try:
            config = load_config()
            used_ports = {
                service.get("port", 0) for service in config["services"].values()
            }
            base_ports = [r["start"] for r in config["port_ranges"].values()]

            suggestions = []
            for base in base_ports:
                # Try increments of 10 first: 8000, 8010, 8020...
                found_increment_10 = False
                for i in range(0, 100, 10):
                    port = base + i
                    if port not in used_ports and 1024 <= port <= 65535:
                        suggestions.append(CompletionItem(str(port)))
                        found_increment_10 = True
                        break

                # If no increment of 10 available, try increments of 5: 8005, 8015...
                if not found_increment_10:
                    for i in range(5, 100, 5):
                        port = base + i
                        if port not in used_ports and 1024 <= port <= 65535:
                            suggestions.append(CompletionItem(str(port)))
                            break

            return [s for s in suggestions if s.value.startswith(incomplete)]
        except Exception:
            return []


class CompleteServiceNames(click.ParamType):
    name = "service_name"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for service names."""
        try:
            config = load_config()
            service_names = list(config["services"].keys())
            return [
                CompletionItem(service_name)
                for service_name in service_names
                if service_name.startswith(incomplete)
            ]
        except Exception:
            return []


SERVICE_NAME = CompleteServiceNames()
PORT_RANGE = click.STRING
SMART_PORT = click.INT


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass


@cli.command()
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


@cli.command()
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
        if "=" in env_var:
            key, value = env_var.split("=", 1)
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
    with open(env_file, "w") as f:
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

        # Color-code the service name based on status
        if status == "active":
            colored_name = click.style(name, fg="green", bold=True)
            colored_status = click.style("active", fg="green")
        else:
            colored_name = click.style(name, fg="red")
            colored_status = click.style(status, fg="red")

        # Color-code the port
        colored_port = click.style(str(service["port"]), fg="cyan")

        # Green checkmark for enabled services
        enabled_mark = click.style("✓", fg="green", bold=True) if enabled else ""

        rows.append(
            [
                colored_name,
                colored_port,
                colored_status,
                enabled_mark,
                service["command"],
            ]
        )

    # Sort by name
    rows.sort(key=lambda x: x[0])

    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]
    # Force colors even over SSH
    output = tabulate(rows, headers=headers, tablefmt="simple")
    click.echo(output, color=True)


@cli.command()
@click.argument("name", type=SERVICE_NAME)
def start(name):
    """Start a service"""
    success, error = control_service(name, "start")
    if not success:
        click.secho(
            f"✗ Failed to start {name}: {error}",
            fg="red",
            bold=True,
            err=True,
            color=True,
        )
        return

    click.secho(
        f"✓ Service '{click.style(name, fg='cyan', bold=True)}' started successfully",
        fg="green",
        bold=True,
        color=True,
    )


@cli.command()
@click.argument("name", type=SERVICE_NAME)
@click.option("--force", is_flag=True, help="Force kill the process")
def stop(name, force=False):
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
    kill_result, kill_msg = kill_process_by_port(port, force)

    if kill_result:
        click.secho(
            f"🔪 Killed processes on port {port}: {kill_msg}",
            fg="yellow",
            bold=True,
            color=True,
        )

    click.secho(
        f"✓ Service '{click.style(name, fg='cyan', bold=True)}' stopped successfully",
        fg="green",
        bold=True,
        color=True,
    )


@cli.command()
@click.argument("name", type=SERVICE_NAME)
def restart(name):
    """Restart a service"""
    # First stop (with cleanup)
    config = load_config()

    if name not in config["services"]:
        click.secho(
            f"✗ Service '{name}' not found", fg="red", bold=True, err=True, color=True
        )
        return

    # Stop service and kill processes
    success, error = control_service(name, "stop")
    port = config["services"][name]["port"]
    kill_process_by_port(port)

    # Start service again
    success, error = control_service(name, "start")
    if not success:
        click.secho(
            f"✗ Error restarting {name}: {error}",
            fg="red",
            bold=True,
            err=True,
            color=True,
        )
        return

    click.secho(
        f"✓ Service '{click.style(name, fg='cyan', bold=True)}' restarted successfully",
        fg="green",
        bold=True,
        color=True,
    )


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


@cli.command()
@click.argument("port", type=int)
def kill_port(port):
    """Kill processes using a specific port"""
    success, message = kill_process_by_port(port, force=True)
    if success:
        click.echo(f"Success: {message}")
    else:
        click.echo(f"No processes found using port {port}")


@cli.command()
@click.argument("backup_file")
def restore(backup_file):
    """Restore configuration from a backup file"""
    try:
        with open(backup_file) as f:
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

    with open(backup_path, "w") as f:
        json.dump(config, f, indent=2)

    click.echo(f"Current configuration backed up to {backup_path}")

    # Restore from backup
    save_config(backup_data)
    click.echo(f"Configuration restored from {backup_file}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=9000, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
@click.option(
    "--register", is_flag=True, help="Register as a service instead of running directly"
)
def web(host, port, no_browser, register):
    """Start the web UI"""

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
            success, result = register_service(
                service_name, web_ui_command, port, "", "default", env_vars
            )

            if not success:
                click.echo(f"Error registering web UI service: {result}")
                return

            click.echo(
                f"Web UI registered as service '{service_name}' on port {result}"
            )

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


@cli.command()
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
    import os

    # Auto-detect shell if not specified
    if not shell:
        shell_path = os.environ.get("SHELL", "")
        shell_name = os.path.basename(shell_path)
        if "bash" in shell_name:
            shell = "bash"
        elif "zsh" in shell_name:
            shell = "zsh"
        elif "fish" in shell_name:
            shell = "fish"
        else:
            # Try detecting from $0 as fallback
            current_shell = os.environ.get("0", "")
            if "bash" in current_shell:
                shell = "bash"
            elif "zsh" in current_shell:
                shell = "zsh"
            elif "fish" in current_shell:
                shell = "fish"
            else:
                click.secho(
                    "Could not detect shell. Please specify with --shell",
                    fg="red",
                    err=True,
                )
                click.echo("Supported shells: bash, zsh, fish")
                return

    config_file = _get_config_file(shell)
    completion_file = _get_completion_file(shell) if shell == "zsh" else None

    # Handle test option
    if test:
        click.echo(f"Testing completion for {shell}...")
        if not os.path.exists(config_file):
            click.secho(f"✗ Shell config file not found: {config_file}", fg="red")
            return

        try:
            with open(config_file) as f:
                content = f.read()

                if shell == "zsh" and completion_file:
                    installed = (
                        f"source {completion_file}" in content
                        and os.path.exists(completion_file)
                    )
                else:
                    installed = f"_PANEL_COMPLETE={shell}_source panel" in content

                if installed:
                    click.secho(
                        f"✓ Completion appears to be installed for {shell}", fg="green"
                    )
                    # TODO: Test actual tab completion functionality
                else:
                    click.secho(f"✗ Completion not found in {shell} config", fg="red")
                    click.echo(f"Run: panel completion --install --shell {shell}")
        except Exception as e:
            click.secho(f"✗ Error checking completion: {e}", fg="red")
        return

    # Handle uninstall option
    if uninstall:
        click.echo(f"Removing completion for {shell}...")
        try:
            # Remove from shell config
            if os.path.exists(config_file):
                with open(config_file) as f:
                    lines = f.readlines()

                # Filter out panel completion lines
                filtered_lines = []
                skip_next = False
                for line in lines:
                    if skip_next:
                        skip_next = False
                        continue
                    if "Panel CLI completion" in line:
                        skip_next = True  # Skip the actual completion line too
                        continue
                    if "_PANEL_COMPLETE" in line or (
                        completion_file and f"source {completion_file}" in line
                    ):
                        continue
                    filtered_lines.append(line)

                with open(config_file, "w") as f:
                    f.writelines(filtered_lines)

            # Remove completion file for zsh
            if completion_file and os.path.exists(completion_file):
                os.remove(completion_file)

            click.secho(f"✓ Completion removed from {shell}", fg="green")
            click.echo(f"Restart your shell or run: source {config_file}")
        except Exception as e:
            click.secho(f"✗ Error removing completion: {e}", fg="red")
        return

    if install:
        click.echo(f"Installing completion for {shell}...")
        try:
            # Check if config file directory exists
            config_dir = os.path.dirname(config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                click.echo(f"Created directory: {config_dir}")

            # Generate completion script based on shell
            if shell == "bash":
                script = "_PANEL_COMPLETE=bash_source panel"
                completion_content = f'eval "$({script})"'
            elif shell == "zsh":
                # Use custom zsh completion instead of Click (which has issues)
                custom_completion = """# Panel completion for zsh
_panel_completion() {
    local context state line

    _arguments -C \\
        '1: :->commands' \\
        '*: :->args' && return 0

    case $state in
        commands)
            local commands=(
                'register:Register a new service'
                'list:List all registered services'
                'start:Start a service'
                'stop:Stop a service'
                'restart:Restart a service'
                'auto:Enable auto-start and start service'
                'disable:Disable auto-start'
                'logs:View service logs'
                'open-browser:Open service URL'
                'unregister:Unregister a service'
                'edit:Edit service configuration'
                'web:Start web UI'
                'completion:Setup shell completion'
            )
            _describe -t commands 'panel commands' commands
            ;;
        args)
            case $words[2] in
                start|stop|restart|auto|disable|logs|unregister|edit|open-browser)
                    # Get service list directly
                    local services=(${(f)"$(python3 -c "import json; f=open('$HOME/.config/control-panel/services.json'); data=json.load(f); print('\\\\n'.join(data['services'].keys()))" 2>/dev/null)"})
                    if [[ ${#services[@]} -gt 0 ]]; then
                        _describe -t services 'services' services
                    fi
                    ;;
            esac
            ;;
    esac
}

# Register the completion
if command -v compdef >/dev/null 2>&1; then
    compdef _panel_completion panel 2>/dev/null || true
fi"""

                # Write custom completion file
                with open(completion_file, "w") as f:
                    f.write(custom_completion)

                completion_content = f"source {completion_file}"
                script = completion_content  # For the duplicate check
            elif shell == "fish":
                script = "_PANEL_COMPLETE=fish_source panel"
                completion_content = f"eval ({script})"

            # Check if already installed
            try:
                if os.path.exists(config_file):
                    with open(config_file) as f:
                        content = f.read()

                    # Check based on shell type
                    if shell == "zsh":
                        already_installed = (
                            f"source {completion_file}" in content
                            and os.path.exists(completion_file)
                        )
                    else:
                        already_installed = (
                            f"_PANEL_COMPLETE={shell}_source panel" in content
                        )

                    if already_installed:
                        click.secho(
                            f"✓ Completion already installed for {shell}", fg="green"
                        )
                        click.echo(
                            "Use --test to verify it's working, or --uninstall to remove"
                        )
                        return
            except Exception as e:
                click.echo(f"Warning: Could not check existing installation: {e}")
                # Continue with installation anyway

            # Add completion to shell config
            with open(config_file, "a") as f:
                f.write(f"\n# Panel CLI completion\n{completion_content}\n")

            click.secho(f"✓ Completion installed for {shell}", fg="green")
            click.echo(f"Restart your shell or run: source {config_file}")

        except Exception as e:
            click.secho(f"✗ Failed to install completion: {e}", fg="red", err=True)
    else:
        # Show usage instructions
        click.echo("Use one of these options:")
        click.echo("  --install              Install completion (auto-detects shell)")
        click.echo("  --install --shell zsh  Install for specific shell")
        click.echo("  --test                 Test if completion is working")
        click.echo("  --uninstall            Remove completion")
        click.echo()
        click.echo("Supported shells: bash, zsh, fish")


# Command aliases
@cli.command("ls")
def ls():
    """List all registered services (alias for 'list')"""
    # Call the existing list command
    ctx = click.get_current_context()
    ctx.invoke(list)


@cli.command("ps")
def ps():
    """Show running services"""
    config = load_config()

    if not config["services"]:
        click.echo("No services registered")
        return

    # Get status for each service and filter for running ones
    running_services = []
    for name, service in config["services"].items():
        status, enabled = get_service_status(name)
        if status == "active":
            # Color-code active services (ps only shows running ones)
            colored_name = click.style(name, fg="green", bold=True)
            colored_port = click.style(str(service["port"]), fg="cyan")
            colored_status = click.style("active", fg="green")
            enabled_mark = click.style("✓", fg="green", bold=True) if enabled else ""
            running_services.append(
                [
                    colored_name,
                    colored_port,
                    colored_status,
                    enabled_mark,
                    service["command"],
                ]
            )

    if not running_services:
        click.echo("No services currently running")
        return

    # Sort by name
    running_services.sort(key=lambda x: x[0])

    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]
    output = tabulate(running_services, headers=headers, tablefmt="simple")
    click.echo(output, color=True)


@cli.command("open-browser")  # Rename to avoid conflicts with Python's open()
@click.argument("name", type=SERVICE_NAME)
def open_browser(name):
    """Open service URL in default browser"""
    config = load_config()

    if name not in config["services"]:
        click.secho(
            f"✗ Service '{name}' not found", fg="red", bold=True, err=True, color=True
        )
        return

    port = config["services"][name]["port"]
    url = f"http://localhost:{port}"

    try:
        webbrowser.open(url)
        click.secho(
            f"🌐 Opening {click.style(url, fg='cyan', bold=True)} in browser",
            fg="green",
            bold=True,
            color=True,
        )
    except Exception as e:
        click.secho(
            f"✗ Failed to open browser: {e}", fg="red", bold=True, err=True, color=True
        )


@cli.command("restart-all")
@click.option(
    "--enabled-only",
    is_flag=True,
    help="Only restart services that are enabled for auto-start",
)
def restart_all(enabled_only):
    """Restart all services (or just enabled ones)"""
    config = load_config()

    if not config["services"]:
        click.echo("No services registered")
        return

    services_to_restart = []
    for name, service in config["services"].items():
        if enabled_only and not service.get("enabled", False):
            continue
        services_to_restart.append(name)

    if not services_to_restart:
        if enabled_only:
            click.echo("No enabled services to restart")
        else:
            click.echo("No services to restart")
        return

    click.echo(f"Restarting {len(services_to_restart)} service(s)...")

    failed_services = []
    for name in services_to_restart:
        click.secho(
            f"🔄 Restarting {click.style(name, fg='cyan', bold=True)}...",
            fg="yellow",
            color=True,
        )

        # Stop service and kill processes
        control_service(name, "stop")
        port = config["services"][name]["port"]
        kill_process_by_port(port)

        # Start service again
        success, error = control_service(name, "start")
        if not success:
            click.secho(
                f"✗ Failed to restart {name}: {error}", fg="red", bold=True, color=True
            )
            failed_services.append(name)
        else:
            click.secho(
                f"✓ {click.style(name, fg='cyan', bold=True)} restarted successfully",
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


# Export the CLI function as main for entry_point in setup.py
main = cli

if __name__ == "__main__":
    cli()
