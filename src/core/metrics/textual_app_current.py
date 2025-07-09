"""
New Textual-based metrics dashboard with proper table formatting
"""
import time
from typing import Dict, List, Set

from textual.app import App, ComposeResult
from textual.widgets import Footer, Static

from ..system_metrics import get_all_metrics
from .hardware_detector import get_hardware_info
from .service_metrics import get_all_service_metrics


class SystemMetricsWidget(Static):
    """Widget for displaying system metrics"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hardware_info = {}
        self.previous_metrics = {}

    def set_hardware_info(self, hardware_info: Dict):
        """Set hardware information"""
        self.hardware_info = hardware_info

    def update_metrics(self, metrics: Dict):
        """Update system metrics display"""
        lines = []

        # CPU
        cpu_percent = metrics.get("cpu_percent", 0)
        cpu_cores = self.hardware_info.get("cpu_cores", "Unknown")
        cpu_model = self.hardware_info.get("cpu_model", "Unknown CPU")
        cpu_bar = self.create_progress_bar(cpu_percent)
        cpu_trend = self.get_trend(
            cpu_percent, self.previous_metrics.get("cpu_percent", cpu_percent)
        )
        lines.append(
            f"CPU:      {cpu_percent:5.1f}% {cpu_bar} {cpu_trend}   {cpu_cores} cores ({cpu_model})"
        )

        # Memory
        memory_percent = metrics.get("memory_percent", 0)
        memory_used = self.format_bytes(metrics.get("memory_used", 0))
        memory_total = self.format_bytes(metrics.get("memory_total", 0))
        memory_bar = self.create_progress_bar(memory_percent)
        memory_trend = self.get_trend(
            memory_percent, self.previous_metrics.get("memory_percent", memory_percent)
        )
        lines.append(
            f"Memory:   {memory_percent:5.1f}% {memory_bar} {memory_trend}   {memory_used}/{memory_total}"
        )

        # GPU
        gpu_percent = metrics.get("gpu_percent", 0)
        gpu_name = self.hardware_info.get("gpu_name", "No GPU")
        if gpu_percent > 0:
            gpu_bar = self.create_progress_bar(gpu_percent)
            gpu_trend = self.get_trend(
                gpu_percent, self.previous_metrics.get("gpu_percent", gpu_percent)
            )
            lines.append(
                f"GPU:      {gpu_percent:5.1f}% {gpu_bar} {gpu_trend}   {gpu_name}"
            )
        else:
            lines.append(f"GPU:         -- [░░░░░░░░░░] →       {gpu_name}")

        # VRAM
        vram_percent = metrics.get("vram_percent", 0)
        vram_used = self.format_bytes(metrics.get("vram_used", 0))
        vram_total = self.format_bytes(metrics.get("vram_total", 0))
        if vram_percent > 0:
            vram_bar = self.create_progress_bar(vram_percent)
            vram_trend = self.get_trend(
                vram_percent, self.previous_metrics.get("vram_percent", vram_percent)
            )
            lines.append(
                f"VRAM:     {vram_percent:5.1f}% {vram_bar} {vram_trend}   {vram_used}/{vram_total}"
            )
        else:
            lines.append("VRAM:        -- [░░░░░░░░░░] →       --/--")

        # Disk
        disk_percent = metrics.get("disk_percent", 0)
        disk_used = self.format_bytes(metrics.get("disk_used", 0))
        disk_total = self.format_bytes(metrics.get("disk_total", 0))
        disk_type = self.hardware_info.get("disk_type", "Unknown")
        disk_bar = self.create_progress_bar(disk_percent)
        disk_trend = self.get_trend(
            disk_percent, self.previous_metrics.get("disk_percent", disk_percent)
        )
        lines.append(
            f"Disk:     {disk_percent:5.1f}% {disk_bar} {disk_trend}   {disk_used}/{disk_total} {disk_type}"
        )

        # Store for next comparison
        self.previous_metrics = metrics.copy()

        # Update the widget content
        self.update("\n".join(lines))

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format"""
        if bytes_value == 0:
            return "0B"

        for unit in ["B", "K", "M", "G", "T"]:
            if bytes_value < 1024:
                if unit == "B":
                    return f"{bytes_value}{unit}"
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f}P"

    def create_progress_bar(self, percent: float) -> str:
        """Create a progress bar visualization"""
        filled = int(percent / 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def get_trend(self, current: float, previous: float) -> str:
        """Get trend indicator"""
        diff = current - previous
        if abs(diff) < 0.1:
            return "→"
        elif diff > 0:
            return "↑"
        else:
            return "↓"


class ServicesTableWidget(Static):
    """Widget for displaying services in proper table format matching mockups"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.expanded_services: Set[str] = set()
        self.service_metrics: List[Dict] = []
        self.cursor_row = 0
        self.row_to_service_map: Dict[int, int] = {}
        self.selectable_rows: List[int] = []

    def update_services(self, service_metrics: List[Dict]):
        """Update the services table"""
        self.service_metrics = service_metrics
        self.row_to_service_map = {}
        self.selectable_rows = []

        lines = []

        # Table header with proper borders (narrower to fit 80 chars)
        lines.append(
            "┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━━━━┓"
        )
        lines.append(
            "┃ Service               ┃  CPU ┃  RAM ┃  GPU ┃ VRAM ┃ Status      ┃"
        )
        lines.append(
            "┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━━━━┩"
        )

        current_display_row = 3  # Start after header

        for service_index, service in enumerate(service_metrics):
            service_name = service["service_name"]
            metrics = service["metrics"]

            # Determine selection and expansion indicators
            is_selected = service_index == self.cursor_row
            is_expanded = service_name in self.expanded_services

            selection_indicator = "●" if is_selected else " "
            expansion_indicator = "▼" if is_expanded else "▶"

            # Format service name (shorter)
            service_display = (
                f"{selection_indicator} {expansion_indicator} {service_name}"
            )
            if service.get("port"):
                service_display += f":{service['port']}"
            service_display = service_display[:21]  # Truncate to fit column

            # Format metrics (shorter)
            cpu_str = (
                f"{metrics['cpu_percent']:4.1f}%"
                if metrics["cpu_percent"] >= 0
                else "   --"
            )
            memory_str = (
                self.format_bytes(int(metrics["memory_mb"] * 1024 * 1024))
                if metrics["memory_mb"] > 0
                else "   --"
            )

            # GPU metrics (shorter)
            gpu_vram_mb = metrics.get("gpu_vram_mb", 0)
            gpu_util_percent = metrics.get("gpu_util_percent", 0)

            if gpu_vram_mb > 0:
                gpu_str = f"{gpu_util_percent:4.1f}%"
                vram_str = f"{self.format_bytes(gpu_vram_mb * 1024 * 1024):>4}"
            else:
                gpu_str = "  --"
                vram_str = "  --"

            # Status with uptime (shorter)
            if service["status"] == "active":
                uptime_str = self.format_uptime(metrics["uptime_seconds"])
                status = f"Run {uptime_str}"
            else:
                status = "Inactive"
            status = status[:11]  # Truncate to fit

            # Track which rows are selectable (simplified)
            self.row_to_service_map[service_index] = service_index
            self.selectable_rows.append(service_index)

            # Add the main service row (narrower format)
            lines.append(
                f"│ {service_display:<21} │ {cpu_str:>4} │ {memory_str:>4} │ {gpu_str:>4} │ {vram_str:>4} │ {status:<11} │"
            )
            current_display_row += 1

            # Add expanded details if service is expanded
            if is_expanded:
                detail_lines = self._create_detailed_metrics(service)
                lines.extend(detail_lines)
                current_display_row += len(detail_lines)

        # Close the table (narrower)
        lines.append(
            "╰─────────────────────────────────────────────────────────────────────────────╯"
        )

        # Update the widget content
        self.update("\n".join(lines))

    def _create_detailed_metrics(self, service: Dict) -> List[str]:
        """Create detailed metrics display for expanded service"""
        lines = []
        metrics = service["metrics"]
        pids = service.get("pids", [])

        # Top border
        lines.append(
            "│ ├───────────────────────────────────────────────────────────────────────────────╮ │"
        )

        # CPU Usage detail
        cpu_percent = metrics.get("cpu_percent", 0)
        main_pid = pids[0] if pids else "N/A"
        threads = metrics.get("num_threads", 0)
        cpu_bar = self.create_progress_bar(cpu_percent, 12)
        lines.append(
            f"│ │ CPU Usage:    {cpu_bar} {cpu_percent:5.1f}%  (PID: {main_pid}, Threads: {threads}){' ' * (79 - len(str(main_pid)) - len(str(threads)) - 50)}│ │"
        )

        # Memory detail
        memory_mb = metrics.get("memory_mb", 0)
        memory_str = self.format_bytes(int(memory_mb * 1024 * 1024))
        lines.append(
            f"│ │ Memory:          {memory_str}  (RSS: {memory_str}){' ' * (79 - len(memory_str) * 2 - 20)}│ │"
        )

        # Network detail
        connections = metrics.get("connections", 0)
        lines.append(
            f"│ │ Network:      ↑--KB/s ↓--KB/s  (Connections: {connections}){' ' * (79 - len(str(connections)) - 35)}│ │"
        )

        # Disk I/O detail
        io_read_mb = metrics.get("io_read_mb", 0)
        io_write_mb = metrics.get("io_write_mb", 0)
        io_read_str = self.format_bytes(int(io_read_mb * 1024 * 1024))
        io_write_str = self.format_bytes(int(io_write_mb * 1024 * 1024))
        lines.append(
            f"│ │ Disk I/O:     Read: {io_read_str}/s  Write: {io_write_str}/s{' ' * (79 - len(io_read_str) - len(io_write_str) - 24)}│ │"
        )

        # Process uptime
        uptime_seconds = metrics.get("uptime_seconds", 0)
        uptime_str = self.format_uptime(uptime_seconds)
        lines.append(
            f"│ │ Uptime:       {uptime_str}{' ' * (79 - len(uptime_str) - 14)}│ │"
        )

        # Bottom border
        lines.append(
            "│ ╰───────────────────────────────────────────────────────────────────────────────╯ │"
        )

        return lines

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format"""
        if bytes_value == 0:
            return "0B"

        for unit in ["B", "K", "M", "G", "T"]:
            if bytes_value < 1024:
                if unit == "B":
                    return f"{bytes_value}{unit}"
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f}P"

    def format_uptime(self, seconds: int) -> str:
        """Format uptime into human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes}m"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h{minutes}m" if minutes > 0 else f"{hours}h"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d{hours}h" if hours > 0 else f"{days}d"

    def create_progress_bar(self, percent: float, width: int = 10) -> str:
        """Create a progress bar visualization"""
        filled = int(percent / (100 / width))
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def move_cursor_up(self):
        """Move cursor up"""
        if self.cursor_row > 0:
            self.cursor_row -= 1
            # DON'T rebuild entire display - this is causing lag
            # Just refresh the existing content
            self.refresh()

    def move_cursor_down(self):
        """Move cursor down"""
        max_row = len(self.service_metrics) - 1
        if self.cursor_row < max_row:
            self.cursor_row += 1
            # DON'T rebuild entire display - this is causing lag
            # Just refresh the existing content
            self.refresh()

    def get_selected_service_index(self) -> int:
        """Get the currently selected service index"""
        return self.row_to_service_map.get(self.cursor_row, 0)

    def toggle_expansion(self, service_index: int):
        """Toggle expansion of a service"""
        if service_index < len(self.service_metrics):
            service_name = self.service_metrics[service_index]["service_name"]

            if service_name in self.expanded_services:
                self.expanded_services.remove(service_name)
            else:
                # Clear other expanded services (only one expanded at a time)
                self.expanded_services.clear()
                self.expanded_services.add(service_name)

            # Refresh the display
            self.update_services(self.service_metrics)


class MetricsApp(App):
    """Main Textual application for the metrics dashboard"""

    CSS = """
    SystemMetricsWidget {
        border: solid $primary;
        border-title-color: $secondary;
        border-title-style: bold;
        height: auto;
        margin: 1;
        padding: 1;
    }

    ServicesTableWidget {
        border: solid $primary;
        border-title-color: $secondary;
        border-title-style: bold;
        height: auto;
        margin: 1;
        padding: 1;
    }

    .status-bar {
        background: $surface;
        color: $text;
        height: 1;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("up", "cursor_up", "Navigate Up"),
        ("down", "cursor_down", "Navigate Down"),
        ("right", "expand_service", "Expand"),
        ("left", "collapse_service", "Collapse"),
        ("enter", "service_actions", "Actions"),
    ]

    def __init__(self, refresh_interval: float = 5.0, **kwargs):
        super().__init__(**kwargs)
        self.refresh_interval = refresh_interval
        self.system_widget = None
        self.services_widget = None
        self.status_widget = None

        # Data storage
        self.hardware_info = {}

    def compose(self) -> ComposeResult:
        """Compose the UI"""
        # System metrics widget
        self.system_widget = SystemMetricsWidget()
        self.system_widget.border_title = "System Metrics (Live)"
        yield self.system_widget

        # Services table widget
        self.services_widget = ServicesTableWidget()
        self.services_widget.border_title = "Services"
        yield self.services_widget

        # Status bar
        self.status_widget = Static("", classes="status-bar")
        yield self.status_widget

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application"""
        # Get hardware info once
        self.hardware_info = get_hardware_info()
        self.system_widget.set_hardware_info(self.hardware_info)

        # Start the metrics update loop with 3 second intervals to reduce lag
        self.set_interval(self.refresh_interval, self.update_metrics)

        # Initial update
        await self.update_metrics()

    async def update_metrics(self) -> None:
        """Update all metrics"""
        # Get system metrics
        system_metrics = get_all_metrics()
        self.system_widget.update_metrics(system_metrics)

        # Get service metrics
        service_metrics = get_all_service_metrics()
        self.services_widget.update_services(service_metrics)

        # Update border titles with counts
        total_services = len(service_metrics)
        running_services = sum(1 for s in service_metrics if s["status"] == "active")
        self.services_widget.border_title = (
            f"Services ({total_services} total, {running_services} running)"
        )

        # Update status bar
        timestamp = time.strftime("%H:%M:%S")
        self.status_widget.update(
            f"Last updated: {timestamp} | ↑↓ Navigate | → Expand | ← Collapse | Enter Actions | q Quit"
        )

    def action_cursor_up(self) -> None:
        """Move cursor up in services table"""
        self.services_widget.move_cursor_up()

    def action_cursor_down(self) -> None:
        """Move cursor down in services table"""
        self.services_widget.move_cursor_down()

    def action_expand_service(self) -> None:
        """Expand selected service"""
        service_index = self.services_widget.get_selected_service_index()
        self.services_widget.toggle_expansion(service_index)

    def action_collapse_service(self) -> None:
        """Collapse selected service"""
        service_index = self.services_widget.get_selected_service_index()
        if service_index < len(self.services_widget.service_metrics):
            service_name = self.services_widget.service_metrics[service_index][
                "service_name"
            ]
            self.services_widget.expanded_services.discard(service_name)
            self.services_widget.update_services(self.services_widget.service_metrics)

    def action_service_actions(self) -> None:
        """Show service actions menu"""
        service_index = self.services_widget.get_selected_service_index()

        if service_index < len(self.services_widget.service_metrics):
            service = self.services_widget.service_metrics[service_index]
            service_name = service["service_name"]
            status = service["status"]

            # Create action options based on service status
            actions = []
            if status == "active":
                actions = ["Stop", "Restart", "View Logs", "Open Browser"]
            else:
                actions = ["Start", "View Logs"]

            # Show extended notification that stays visible longer
            action_text = (
                f"⚡ {service_name} ({status}) ⚡\nActions: "
                + " | ".join(actions)
                + "\n[Not yet implemented - press any key to continue]"
            )
            self.notify(action_text, title="Service Actions", timeout=5)


def run_metrics_dashboard(refresh_interval: float = 5.0):
    """Run the metrics dashboard application"""
    app = MetricsApp(refresh_interval=refresh_interval)
    app.run()


if __name__ == "__main__":
    run_metrics_dashboard()
