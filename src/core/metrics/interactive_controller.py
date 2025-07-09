#!/usr/bin/env python3

import sys
import threading
import time
from typing import Dict, List

from rich.console import Console

from ..system_metrics import get_all_metrics
from .display_formatter import MetricsFormatter
from .hardware_detector import get_hardware_info
from .service_metrics import get_all_service_metrics


class InteractiveController:
    """Handles interactive navigation and control of the metrics dashboard"""

    def __init__(self, refresh_interval: float = 1.0):
        self.refresh_interval = refresh_interval
        self.selected_index = 0
        self.running = False
        self.formatter = MetricsFormatter()
        self.console = Console()

        # Data storage
        self.system_metrics: Dict = {}
        self.previous_system_metrics: Dict = {}
        self.service_metrics: List[Dict] = []
        self.hardware_info: Dict = {}

        # Navigation state
        self.expanded_services: set = set()  # Track which services are expanded

        # Threading
        self.data_thread = None
        self.input_thread = None
        self.lock = threading.Lock()

    def initialize(self):
        """Initialize hardware detection and initial data"""
        self.console.print("[yellow]Initializing metrics dashboard...[/]")

        # Detect hardware info once
        self.hardware_info = get_hardware_info()
        self.formatter.set_hardware_info(self.hardware_info)

        # Get initial data
        self._update_data()

    def _update_data(self):
        """Update system and service metrics data"""
        with self.lock:
            # Store previous system metrics for trend calculation
            self.previous_system_metrics = self.system_metrics.copy()

            # Get fresh metrics
            self.system_metrics = get_all_metrics()
            self.service_metrics = get_all_service_metrics()

            # Ensure selected index is valid
            if self.service_metrics:
                self.selected_index = min(
                    self.selected_index, len(self.service_metrics) - 1
                )
                self.selected_index = max(0, self.selected_index)
            else:
                self.selected_index = 0

    def _data_refresh_loop(self):
        """Background thread for refreshing metrics data"""
        while self.running:
            self._update_data()
            time.sleep(self.refresh_interval)

    def _handle_input_blessed(self, term):
        """Handle keyboard input using blessed terminal"""
        # This is now handled inline in the main loop
        pass

    def _move_selection(self, direction: int):
        """Move the selection cursor up or down"""
        with self.lock:
            if self.service_metrics:
                new_index = self.selected_index + direction
                self.selected_index = max(
                    0, min(new_index, len(self.service_metrics) - 1)
                )
                # Don't auto-collapse when just navigating - only when expanding another

    def _expand_service(self):
        """Expand service details (close others)"""
        if not self.service_metrics or self.selected_index >= len(self.service_metrics):
            return

        selected_service = self.service_metrics[self.selected_index]
        service_name = selected_service["service_name"]

        # Clear all expanded services and expand only the selected one
        self.expanded_services.clear()
        self.expanded_services.add(service_name)

    def _collapse_service(self):
        """Collapse service details"""
        if not self.service_metrics or self.selected_index >= len(self.service_metrics):
            return

        selected_service = self.service_metrics[self.selected_index]
        service_name = selected_service["service_name"]
        self.expanded_services.discard(service_name)

    def _show_service_actions(self):
        """Show quick actions menu for selected service (placeholder for blessed implementation)"""
        if not self.service_metrics or self.selected_index >= len(self.service_metrics):
            return

        # For now, just show a simple message - could be enhanced later
        # In a real implementation, we'd pause the display and show a menu
        pass

    def _restart_service(self, service_name: str):
        """Restart a service"""
        import subprocess

        self.console.print(f"[yellow]Restarting {service_name}...[/]")
        try:
            subprocess.run(["panel", "restart", service_name], check=True)
            self.console.print(f"[green]✓ {service_name} restarted successfully[/]")
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗ Failed to restart {service_name}: {e}[/]")

    def _stop_service(self, service_name: str):
        """Stop a service"""
        import subprocess

        self.console.print(f"[yellow]Stopping {service_name}...[/]")
        try:
            subprocess.run(["panel", "stop", service_name], check=True)
            self.console.print(f"[green]✓ {service_name} stopped successfully[/]")
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗ Failed to stop {service_name}: {e}[/]")

    def _view_logs(self, service_name: str):
        """View service logs"""
        import subprocess

        self.console.print(f"[cyan]Opening logs for {service_name}...[/]")
        try:
            subprocess.run(["panel", "logs", service_name])
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗ Failed to view logs for {service_name}: {e}[/]")

    def _edit_service(self, service_name: str):
        """Edit service configuration"""
        self.console.print(
            f"[yellow]Use 'panel edit {service_name}' to modify configuration[/]"
        )

    def _open_browser(self, service_name: str):
        """Open service in browser"""
        import subprocess

        self.console.print(f"[blue]Opening {service_name} in browser...[/]")
        try:
            subprocess.run(["panel", "open-browser", service_name], check=True)
            self.console.print(f"[green]✓ Opened {service_name} in browser[/]")
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]✗ Failed to open {service_name}: {e}[/]")

    def run_interactive(self):
        """Run the interactive metrics dashboard using blessed for better terminal control"""
        self.initialize()

        # Check if we have a real terminal
        if not sys.stdin.isatty():
            self.console.print(
                "[yellow]No terminal detected, falling back to simple mode...[/]"
            )
            self.run_simple(json_output=False)
            return

        try:
            from blessed import Terminal
        except ImportError:
            self.console.print(
                "[red]Blessed library not available, falling back to simple mode...[/]"
            )
            self.run_simple(json_output=False)
            return

        self.running = True
        term = Terminal()

        # Start background threads
        self.data_thread = threading.Thread(target=self._data_refresh_loop, daemon=True)

        self.data_thread.start()

        try:
            with term.cbreak(), term.hidden_cursor():
                # Clear screen and start at top
                print(term.clear + term.home, end="", flush=True)

                while self.running:
                    try:
                        # Move to top-left corner
                        print(term.home, end="", flush=True)

                        with self.lock:
                            layout = self.formatter.create_layout(
                                self.system_metrics,
                                self.service_metrics,
                                self.selected_index,
                                self.previous_system_metrics,
                                terminal_height=term.height,
                                expanded_services=self.expanded_services,
                            )

                        # Render Rich content to string
                        with self.console.capture() as capture:
                            self.console.print(layout)

                        output = capture.get()
                        lines = output.split("\n")

                        # Ensure we don't exceed terminal height
                        max_lines = term.height - 1
                        if len(lines) > max_lines:
                            lines = lines[:max_lines]

                        # Print each line and clear remainder
                        for i, line in enumerate(lines):
                            print(
                                term.move_xy(0, i) + term.clear_eol + line,
                                end="",
                                flush=True,
                            )

                        # Clear any remaining lines
                        for i in range(len(lines), term.height):
                            print(
                                term.move_xy(0, i) + term.clear_eol, end="", flush=True
                            )

                        # Use proper blessed input handling (non-blocking, no double calls)
                        key = term.inkey(timeout=0)  # Non-blocking
                        if key:
                            # Process input immediately
                            if key.lower() == "q" or key.code == term.KEY_ESCAPE:
                                self.running = False
                                break
                            elif key.code == term.KEY_UP:
                                self._move_selection(-1)
                            elif key.code == term.KEY_DOWN:
                                self._move_selection(1)
                            elif key.code == term.KEY_RIGHT:
                                self._expand_service()
                            elif key.code == term.KEY_LEFT:
                                self._collapse_service()
                            elif key.code == term.KEY_ENTER:
                                self._show_service_actions()

                        # Fast refresh rate for responsiveness (no sleeping after input)
                        time.sleep(0.02)  # 50Hz refresh rate

                    except Exception as e:
                        print(term.clear + term.home, end="", flush=True)
                        self.console.print(f"[red]Display error: {e}[/]")
                        break

        except KeyboardInterrupt:
            self.running = False
        except Exception as e:
            self.running = False
            self.console.print(f"[red]Interactive mode error: {e}[/]")

        # Clean shutdown
        self.running = False
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=1)

    def run_simple(self, json_output: bool = False):
        """Run a simple one-time metrics display"""
        self.initialize()

        if json_output:
            import json

            data = {
                "system": self.system_metrics,
                "services": self.service_metrics,
                "hardware": self.hardware_info,
            }
            print(json.dumps(data, indent=2))
        else:
            layout = self.formatter.create_layout(
                self.system_metrics, self.service_metrics
            )
            self.console.print(layout)
