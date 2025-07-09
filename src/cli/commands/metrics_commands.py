#!/usr/bin/env python3

import click

# Command group metadata
__group__ = "Monitoring"

from core.metrics.interactive_controller import InteractiveController
from core.metrics.textual_app import run_metrics_dashboard


@click.command()
@click.option(
    "-l",
    "--live",
    is_flag=True,
    default=True,
    help="Interactive live dashboard (default)",
)
@click.option("-s", "--simple", is_flag=True, help="System metrics only, no services")
@click.option(
    "-j", "--json", "json_output", is_flag=True, help="Machine-readable JSON output"
)
@click.option(
    "-i",
    "--interval",
    type=float,
    default=1.0,
    help="Refresh rate in seconds (default: 1.0)",
)
@click.option(
    "--debug", is_flag=True, hidden=True, help="Debug mode with fallback display"
)
def metrics(live, simple, json_output, interval, debug):
    """Interactive real-time system and service monitoring dashboard

    Shortcut: m
    """
    controller = InteractiveController(refresh_interval=interval)

    if json_output:
        # JSON output mode
        controller.run_simple(json_output=True)
    elif simple:
        # Simple display mode
        controller.run_simple(json_output=False)
    elif debug:
        # Debug mode - just print once
        controller.initialize()
        layout = controller.formatter.create_layout(
            controller.system_metrics, controller.service_metrics
        )
        controller.console.print(layout)
    else:
        # Interactive live dashboard using Textual
        try:
            run_metrics_dashboard(refresh_interval=interval)
        except Exception as e:
            # Fallback to Rich+blessed implementation
            print(f"Textual dashboard failed: {e}")
            print("Falling back to Rich implementation...")
            try:
                controller.run_interactive()
            except Exception as e2:
                controller.console.print(f"[red]Interactive mode failed: {e2}[/]")
                controller.console.print("[yellow]Falling back to simple mode...[/]")
                controller.run_simple(json_output=False)


# Custom command class for proper help formatting
class MetricsCommand(click.Command):
    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        lines = help_text.split("\n")
        for i, line in enumerate(lines):
            if line == "Options:":
                lines.insert(i, "")
                lines.insert(i, "Shortcut: m")
                break
        return "\n".join(lines)


# Update the command to use the custom class
metrics.cls = MetricsCommand
