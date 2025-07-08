#!/usr/bin/env python3

import click

# Command group metadata
__group__ = "Status & Info"

# Import from core business logic
from core.config import load_config
from core.service import get_service_port_status, get_service_status
from core.services.ports import detect_service_ports


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


# Custom command classes to add shortcuts with proper formatting
class InfoCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: i")
                break
        return "\n".join(lines)


class StatusCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: s")
                break
        return "\n".join(lines)


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


@click.command("status", cls=StatusCommand)
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


# Mark the 's' command as hidden from help and completion
s.hidden = True


@click.command(cls=InfoCommand)
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

    # Always show detailed information for active services
    if status_info == "active":
        _show_detailed_info(name)


def _show_detailed_info(name):
    """Show comprehensive port and process information for a service"""
    click.echo(f"\n{click.style('=== DETAILED ANALYSIS ===', bold=True, fg='cyan')}")

    # Get raw detection data
    try:
        detection_result = detect_service_ports(name)
        detected_ports = detection_result.get("detected_ports", {})
        main_pid = detection_result.get("main_pid")
        container_info = detection_result.get("container_info")

        # Show service architecture
        click.echo(f"\n{click.style('Service Architecture:', bold=True)}")

        if container_info:
            _show_container_details(container_info)
        else:
            _show_process_tree(detected_ports, main_pid)

        # Show comprehensive port analysis
        _show_port_analysis(detected_ports, main_pid, container_info)

    except Exception as e:
        click.echo(f"\n{click.style('Error getting detailed info:', fg='red')} {e}")


def _show_container_details(container_info):
    """Display container architecture information"""
    runtime = container_info.get("runtime", "unknown")
    container_id = container_info.get("container_id", "unknown")
    container_name = container_info.get("container_name", "unknown")
    network_mode = container_info.get("network_mode", "unknown")

    click.echo(
        f"  ├── {click.style('Container Runtime:', bold=True)} {runtime.title()}"
    )
    click.echo(
        f"  ├── {click.style('Container ID:', bold=True)} {container_id[:12]}..."
    )
    click.echo(f"  ├── {click.style('Container Name:', bold=True)} {container_name}")
    click.echo(f"  └── {click.style('Network Mode:', bold=True)} {network_mode}")

    # Show port mappings
    port_mappings = container_info.get("port_mappings", {})
    if port_mappings:
        click.echo(f"\n{click.style('Port Mappings:', bold=True)}")
        for internal_port, external_port in port_mappings.items():
            if network_mode == "host":
                click.echo(f"  ├── {internal_port} → {external_port} (host network)")
            else:
                click.echo(f"  ├── Container {internal_port} → Host {external_port}")


def _show_process_tree(detected_ports, main_pid):
    """Display process hierarchy for non-containerized services"""
    if not detected_ports:
        click.echo("  └── No processes detected")
        return

    click.echo(f"  ├── {click.style('SystemD Service', bold=True)}")

    if main_pid and main_pid in detected_ports:
        port = detected_ports[main_pid]
        click.echo(f"  │   └── Main Process (PID {main_pid}) → Port {port}")

        # Show child processes
        child_pids = [pid for pid in detected_ports.keys() if pid != main_pid]
        if child_pids:
            click.echo("  │")
            for i, pid in enumerate(child_pids):
                port = detected_ports[pid]
                is_last = i == len(child_pids) - 1
                connector = "└──" if is_last else "├──"
                click.echo(f"  │   {connector} Child Process (PID {pid}) → Port {port}")
    else:
        # No main PID or main PID doesn't have port
        for i, (pid, port) in enumerate(detected_ports.items()):
            is_last = i == len(detected_ports) - 1
            connector = "└──" if is_last else "├──"
            click.echo(f"  {connector} Process (PID {pid}) → Port {port}")


def _show_port_analysis(detected_ports, main_pid, container_info):
    """Show detailed port analysis and selection logic"""
    if not detected_ports and not container_info:
        return

    click.echo(f"\n{click.style('Port Selection Analysis:', bold=True)}")

    if container_info:
        external_ports = container_info.get("external_ports", [])
        internal_ports = container_info.get("internal_ports", [])

        if external_ports:
            click.echo(f"  ├── Available External Ports: {', '.join(external_ports)}")
            click.echo(f"  ├── Available Internal Ports: {', '.join(internal_ports)}")

            # Show selection logic for containers
            primary_port = external_ports[0] if external_ports else None
            if primary_port:
                click.echo(
                    f"  └── {click.style('Primary Port Selected:', fg='green')} {primary_port} (first external port)"
                )
        else:
            click.echo("  └── No external ports detected")
    else:
        # Process-based selection
        if detected_ports:
            all_ports = list(detected_ports.values())
            click.echo(f"  ├── All Detected Ports: {', '.join(map(str, all_ports))}")

            # Show selection priority
            if main_pid and main_pid in detected_ports:
                main_port = detected_ports[main_pid]
                click.echo(
                    f"  ├── {click.style('SystemD Main PID Port:', fg='yellow')} {main_port} (high priority)"
                )

            # Apply web heuristics to show reasoning
            web_ports = [p for p in all_ports if _is_web_port(p)]
            if web_ports:
                click.echo(f"  ├── Web Ports Found: {', '.join(map(str, web_ports))}")
                primary = min(web_ports)
                click.echo(
                    f"  └── {click.style('Primary Port Selected:', fg='green')} {primary} (web heuristic)"
                )
            else:
                primary = min(all_ports)
                click.echo(
                    f"  └── {click.style('Primary Port Selected:', fg='green')} {primary} (lowest port)"
                )


def _is_web_port(port):
    """Check if port is in common web ranges"""
    web_ranges = [
        (80, 80),
        (443, 443),  # Standard HTTP/HTTPS
        (3000, 3010),  # Development servers
        (5000, 5010),  # Flask, etc.
        (8000, 8090),  # Django, web servers
        (11430, 11440),  # Ollama range
    ]

    return any(start <= port <= end for start, end in web_ranges)


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
