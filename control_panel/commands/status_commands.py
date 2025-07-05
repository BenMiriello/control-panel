#!/usr/bin/env python3

import click

# Import required modules
try:
    from control_panel.utils.config import load_config
    from control_panel.utils.service import get_service_port_status, get_service_status
except ImportError:
    from utils.config import load_config
    from utils.service import get_service_port_status, get_service_status


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


@click.command()
@click.argument("name", type=SERVICE_NAME, required=False)
def status(name):
    """Show service status and port management details"""
    if name:
        # Show single service info
        _show_service_info(name)
    else:
        # Show all running services
        _show_all_running_services()


@click.command()
@click.argument("name", type=SERVICE_NAME, required=False)
def info(name):
    """Show detailed service information (alias for status)"""
    if name:
        _show_service_info(name)
    else:
        _show_all_running_services()


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


def _show_all_running_services():
    """Display status for all running services in table format like 'panel list'"""
    config = load_config()

    # Get status for running services only
    rows = []
    for name, service in config["services"].items():
        status_info, enabled = get_service_status(name)
        if status_info == "active":  # Only include running services
            # Get port validation status for running services
            port_status = get_service_port_status(name)

            # Service names always default color (not colored by status)
            colored_name = name

            # Color-code the status
            colored_status = click.style("active", fg="green")

            # Port display with indicators
            primary_port = port_status.get("primary_port")
            port_display = (
                str(primary_port) if primary_port else str(service.get("port", "none"))
            )
            validation = port_status.get("validation", "unknown")

            if validation == "port_mismatch":
                port_display += "*"  # Port mismatch indicator
            elif validation == "no_port_detected":
                port_display += "?"  # No port detected indicator
            elif validation == "dynamic_port":
                port_display = str(primary_port) + "~"  # Dynamic port indicator

            colored_port = click.style(port_display, fg="cyan")

            # Green checkmark for enabled services
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
        click.echo("No services currently running")
        return

    # Sort by name
    rows.sort(key=lambda x: x[0])

    # Print table using same format as 'panel list'
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]

    from tabulate import tabulate

    output = tabulate(rows, headers=headers, tablefmt="simple")
    click.echo(output, color=True)
