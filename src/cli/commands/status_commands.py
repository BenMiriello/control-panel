#!/usr/bin/env python3

import click

# Command group metadata
__group__ = "Status & Info"

# Import from core business logic
from core.config import load_config
from core.service import get_service_port_status, get_service_status


# Create our own SERVICE_NAME completion to avoid circular imports
class CompleteServiceNames(click.ParamType):
    name = "service_name"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for service names."""
        try:
            config = load_config()
            service_names = list(config["services"].keys())
            from click.shell_completion import CompletionItem

            return [
                CompletionItem(service_name)
                for service_name in service_names
                if service_name.startswith(incomplete)
            ]
        except Exception:
            return []


SERVICE_NAME = CompleteServiceNames()


def shorten_command(command, max_length=50):
    """Shorten command display for list view"""
    if len(command) <= max_length:
        return command

    # Cut in half and add ... in middle
    half_length = (max_length - 3) // 2  # -3 for "..."
    start = command[:half_length]
    end = command[-half_length:]
    return f"{start}...{end}"


@click.command("ps")
@click.argument("name", type=SERVICE_NAME, required=False)
@click.option("--active", "-a", is_flag=True, help="Show only active/running services")
def ps(name, active):
    """Show services (default: all services, use -a for active only)

    Examples:
      panel ps              # Show all services
      panel ps --active     # Show only running services
      panel ps myservice    # Show detailed info for 'myservice'
      panel ps -a           # Shorthand for active services
    """
    if name:
        # Show detailed info for specific service (same as info command)
        _show_service_info(name)
    else:
        # Show table view - all services or just active ones
        _show_services_table(active_only=active)


@click.command("status")
@click.argument("name", type=SERVICE_NAME, required=False)
@click.option("--active", "-a", is_flag=True, help="Show only active/running services")
def status(name, active):
    """Show services (alias for ps)"""
    # Delegate to ps command
    ps.callback(name, active)


@click.command("s")
@click.argument("name", type=SERVICE_NAME, required=False)
@click.option("--active", "-a", is_flag=True, help="Show only active/running services")
def s(name, active):
    """Show services (short alias for ps/status)"""
    # Delegate to ps command
    ps.callback(name, active)


@click.command()
@click.argument("name", type=SERVICE_NAME)
def info(name):
    """Show detailed service information"""
    _show_service_info(name)


def _show_service_info(name):
    """Display detailed information for a single service"""
    config = load_config()
    if name not in config["services"]:
        click.secho(f"✗ Service '{name}' not found", fg="red", bold=True)
        return

    service = config["services"][name]
    port_status = get_service_port_status(name)

    click.echo(f"\n{click.style('Service:', bold=True)} {name}")
    click.echo(f"{click.style('Command:', bold=True)} {service['command']}")
    click.echo(f"{click.style('Working Dir:', bold=True)} {service['working_dir']}")
    click.echo(
        f"{click.style('Auto-start:', bold=True)} {'✓ Enabled' if service.get('enabled', False) else '✗ Disabled'}"
    )

    # Port management section
    click.echo(f"\n{click.style('Port Management:', bold=True)}")
    mode = port_status.get("port_management", "managed")
    mode_color = "cyan" if mode == "auto_detect" else "green"
    click.echo(f"  Mode: {click.style(mode, fg=mode_color)}")

    if mode == "managed":
        managed_port = port_status.get("managed_port")
        click.echo(
            f"  Managed Port: {click.style(str(managed_port), fg='yellow') if managed_port else 'Not set'}"
        )

    # Current status
    status_info, _ = get_service_status(name)
    status_color = "green" if status_info == "active" else "red"
    click.echo(
        f"\n{click.style('Current Status:', bold=True)} {click.style(status_info, fg=status_color)}"
    )

    if status_info == "active":
        primary_port = port_status.get("primary_port")
        validation = port_status.get("validation", "unknown")

        click.echo(
            f"Primary Port: {click.style(str(primary_port), fg='cyan') if primary_port else 'None detected'}"
        )

        # Validation status
        validation_display = {
            "port_matches": click.style("✓ Port matches", fg="green"),
            "port_mismatch": click.style("* Port mismatch", fg="yellow"),
            "dynamic_port": click.style("~ Dynamic port", fg="cyan"),
            "no_port_detected": click.style("? No port detected", fg="red"),
        }.get(validation, validation)
        click.echo(f"Validation: {validation_display}")

        # Show detected ports if multiple
        detected_ports = port_status.get("detected_ports", {})
        if len(detected_ports) > 1:
            click.echo(f"\n{click.style('All Detected Ports:', bold=True)}")
            main_pid = port_status.get("main_pid")
            for pid, port in detected_ports.items():
                marker = " (main)" if pid == main_pid else ""
                click.echo(f"  PID {pid}: {port}{marker}")


def _show_services_table(active_only=False):
    """Display services in table format"""
    config = load_config()

    if not config["services"]:
        click.echo("No services registered")
        return

    # Get status for each service
    rows = []
    for name, service in config["services"].items():
        status_info, enabled = get_service_status(name)

        # Filter by active status if requested
        if active_only and status_info != "active":
            continue

        # Service name (colored for active services)
        if status_info == "active":
            colored_name = click.style(name, fg="green", bold=True)
        else:
            colored_name = name

        # Status with color
        if status_info == "active":
            colored_status = click.style("active", fg="green")
        else:
            colored_status = status_info

        # Port display with validation indicators (for all services)
        port_status = get_service_port_status(name)
        # Import format_port_display from cli_utils
        from ..cli_utils import format_port_display

        port_display = format_port_display(port_status)
        if status_info == "active":
            colored_port = click.style(port_display, fg="cyan")
        else:
            # Inactive services don't get colored ports but still get indicators
            colored_port = port_display

        # Auto-start indicator
        enabled_mark = click.style("✓", fg="green", bold=True) if enabled else ""

        rows.append(
            [
                colored_name,
                colored_port,
                colored_status,
                enabled_mark,
                shorten_command(service["command"]),
            ]
        )

    if not rows:
        if active_only:
            click.echo("No services currently running")
        else:
            click.echo("No services registered")
        return

    # Sort by name (strip color codes for sorting)
    rows.sort(key=lambda x: x[0])

    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]

    from tabulate import tabulate

    output = tabulate(rows, headers=headers, tablefmt="simple")
    click.echo(output, color=True)
