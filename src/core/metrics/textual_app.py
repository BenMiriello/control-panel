"""
New Textual-based metrics dashboard with proper table formatting
"""
import threading
import time
from typing import Dict, List, Set

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Label, Static

from ..system_metrics import get_all_metrics
from .hardware_detector import get_hardware_info
from .service_metrics import get_all_service_metrics


class BackgroundDataCollector:
    """Background data collector that runs in a separate thread"""

    def __init__(self, data_refresh_interval: float = 2.0):
        self.data_refresh_interval = data_refresh_interval
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # Cached data
        self.system_metrics = {}
        self.service_metrics = []
        self.hardware_info = {}
        self.last_update = 0

    def start(self):
        """Start background data collection"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._collect_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop background data collection"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _collect_loop(self):
        """Background loop for collecting metrics"""
        while self.running:
            try:
                # Collect data outside the lock
                system_data = get_all_metrics()
                service_data = get_all_service_metrics()

                # Update cached data atomically
                with self.lock:
                    self.system_metrics = system_data
                    self.service_metrics = service_data
                    self.last_update = time.time()

            except Exception as e:
                print(f"Background data collection error: {e}")

            time.sleep(self.data_refresh_interval)

    def get_data(self):
        """Get cached data thread-safely"""
        with self.lock:
            return {
                "system_metrics": self.system_metrics.copy(),
                "service_metrics": self.service_metrics.copy(),
                "last_update": self.last_update,
            }

    def set_hardware_info(self, hardware_info):
        """Set hardware info (called once at startup)"""
        with self.lock:
            self.hardware_info = hardware_info


class ServiceActionsModal(ModalScreen[str]):
    """Modal dialog for service actions that returns the selected action"""

    def __init__(self, service_name: str, service_status: str, **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name
        self.service_status = service_status

    def compose(self) -> ComposeResult:
        """Compose the modal dialog"""
        # Create actions based on service status
        actions = []
        if self.service_status == "active":
            actions = [
                ("1", "Stop Service"),
                ("2", "Restart Service"),
                ("3", "View Logs"),
                ("4", "Open Browser"),
            ]
        else:
            actions = [
                ("1", "Start Service"),
                ("2", "View Logs"),
            ]

        with Vertical(id="actions-modal"):
            yield Label(
                f"Service: {self.service_name} ({self.service_status})",
                id="service-title",
            )
            yield Label("Select an action:", id="action-prompt")

            for key, action in actions:
                yield Button(f"{key}) {action}", id=f"action-{key}")

            yield Button("q) Cancel", id="action-cancel")

    def on_mount(self) -> None:
        """Set modal title after mounting"""
        self.border_title = "Service Actions"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press and return selected action"""
        action_id = event.button.id

        if action_id == "action-cancel":
            self.dismiss(None)
        elif action_id == "action-1":
            if self.service_status == "active":
                self.dismiss("stop")
            else:
                self.dismiss("start")
        elif action_id == "action-2":
            if self.service_status == "active":
                self.dismiss("restart")
            else:
                self.dismiss("logs")
        elif action_id == "action-3":
            self.dismiss("logs")
        elif action_id == "action-4":
            self.dismiss("browser")

    def on_key(self, event) -> None:
        """Handle key press"""
        if event.key == "q":
            self.dismiss(None)
        elif event.key in ["1", "2", "3", "4"]:
            # Find the corresponding button and trigger its action
            button_id = f"action-{event.key}"
            try:
                button = self.query_one(f"#{button_id}", Button)
                button.press()
            except Exception as e:
                print(f"Button press failed: {e}")


class SystemMetricsWidget(Static):
    """Widget for displaying system metrics"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hardware_info = {}
        self.previous_metrics = {}
        self.trend_hold_count = {}  # Hold trend states longer
        self.trend_directions = {}  # Store actual trend directions
        # Remove unused trend_baseline

    def set_hardware_info(self, hardware_info: Dict):
        """Set hardware information"""
        self.hardware_info = hardware_info

    def update_metrics(self, metrics: Dict):
        """Update system metrics display"""
        lines = []

        # CPU - improved formatting
        cpu_data = metrics.get("cpu", {})
        cpu_percent = cpu_data.get("usage", 0)
        cpu_cores = self.hardware_info.get("cpu", {}).get("cores", "Unknown")
        cpu_model = self.hardware_info.get("cpu", {}).get("model", "Unknown CPU")
        cpu_bar = self.create_progress_bar(cpu_percent)
        cpu_trend = self.get_trend(
            "cpu",
            cpu_percent,
            self.previous_metrics.get("cpu", {}).get("usage", cpu_percent),
        )
        lines.append(
            f"CPU:     {cpu_percent:5.1f}% {cpu_bar} {cpu_trend}   {cpu_cores} cores ({cpu_model})"
        )

        # Memory - improved formatting
        memory_data = metrics.get("memory", {})
        memory_percent = memory_data.get("percent", 0)
        memory_used = self.format_bytes(memory_data.get("used", 0))
        memory_total = self.format_bytes(memory_data.get("total", 0))
        memory_bar = self.create_progress_bar(memory_percent)
        memory_trend = self.get_trend(
            "memory",
            memory_percent,
            self.previous_metrics.get("memory", {}).get("percent", memory_percent),
        )
        lines.append(
            f"Memory:  {memory_percent:5.1f}% {memory_bar} {memory_trend}   {memory_used}/{memory_total}"
        )

        # GPU - improved formatting and alignment
        gpu_data = metrics.get("gpu", {})
        gpu_available = gpu_data.get("available", False)
        if gpu_available and gpu_data.get("gpus"):
            gpu_info = gpu_data["gpus"][0]  # Use first GPU
            gpu_percent = gpu_info.get("util_percent", 0)
            # Get actual GPU name from hardware info
            hw_gpu_info = self.hardware_info.get("gpu", {})
            if hw_gpu_info.get("available") and hw_gpu_info.get("gpus"):
                gpu_name = hw_gpu_info["gpus"][0].get("name", "GPU")
                # Clean up GPU name to remove extra text
                if "NVIDIA" in gpu_name:
                    gpu_name = gpu_name.replace("NVIDIA ", "").replace("GeForce ", "")
            else:
                gpu_name = "GPU"
            gpu_bar = self.create_progress_bar(gpu_percent)
            gpu_trend = self.get_trend(
                "gpu",
                gpu_percent,
                self.previous_metrics.get("gpu", {})
                .get("gpus", [{}])[0]
                .get("util_percent", gpu_percent),
            )
            lines.append(
                f"GPU:     {gpu_percent:5.1f}% {gpu_bar} {gpu_trend}   {gpu_name}"
            )
        else:
            lines.append(f"GPU:         -- [{self.create_empty_bar()}]     No GPU")

        # VRAM - improved formatting and alignment
        if gpu_available and gpu_data.get("gpus"):
            gpu_info = gpu_data["gpus"][0]
            vram_used_mb = gpu_info.get("memory_used", 0)
            vram_total_mb = gpu_info.get("memory_total", 0)
            vram_percent = (
                (vram_used_mb / vram_total_mb * 100) if vram_total_mb > 0 else 0
            )
            vram_used = self.format_bytes(vram_used_mb * 1024 * 1024)
            vram_total = self.format_bytes(vram_total_mb * 1024 * 1024)
            vram_bar = self.create_progress_bar(vram_percent)
            prev_vram_used = (
                self.previous_metrics.get("gpu", {})
                .get("gpus", [{}])[0]
                .get("memory_used", vram_used_mb)
            )
            prev_vram_percent = (
                (prev_vram_used / vram_total_mb * 100) if vram_total_mb > 0 else 0
            )
            vram_trend = self.get_trend("vram", vram_percent, prev_vram_percent)
            lines.append(
                f"VRAM:    {vram_percent:5.1f}% {vram_bar} {vram_trend}   {vram_used}/{vram_total}"
            )
        else:
            lines.append(f"VRAM:        -- [{self.create_empty_bar()}]     --/--")

        # Disk - improved formatting
        disk_data = metrics.get("disk", {})
        disk_percent = disk_data.get("percent", 0)
        disk_used = self.format_bytes(disk_data.get("used", 0))
        disk_total = self.format_bytes(disk_data.get("total", 0))
        disk_type = self.hardware_info.get("storage", {}).get("type", "Unknown")
        disk_bar = self.create_progress_bar(disk_percent)
        disk_trend = self.get_trend(
            "disk",
            disk_percent,
            self.previous_metrics.get("disk", {}).get("percent", disk_percent),
        )
        lines.append(
            f"Disk:    {disk_percent:5.1f}% {disk_bar} {disk_trend}   {disk_used}/{disk_total} {disk_type}"
        )

        # Update the widget content
        self.update("\n".join(lines))

        # Store for next comparison AFTER displaying (so trends use the ACTUAL previous values)
        self.previous_metrics = metrics.copy()

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
        """Create a progress bar visualization - 2x wider (20 chars)"""
        filled = int(percent / 5)  # 20 chars total, so divide by 5 instead of 10
        empty = 20 - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def create_empty_bar(self) -> str:
        """Create an empty progress bar for inactive items"""
        return "░" * 20

    def get_trend(self, metric_name: str, current: float, previous: float) -> str:
        """Get trend indicator with better state holding"""
        # If we're already holding a trend, use baseline for comparison
        if (
            metric_name in self.trend_hold_count
            and self.trend_hold_count[metric_name] > 0
        ):
            self.trend_hold_count[metric_name] -= 1
            stored_trend = self.trend_directions.get(metric_name, " ")
            return stored_trend

        # Calculate new trend - use previous value for fresh comparison
        diff = current - previous

        # Determine trend direction - very low threshold to catch small changes
        if abs(diff) < 0.05:  # Very low threshold to catch small changes
            trend = " "  # Blank space instead of right arrow
        elif diff > 0:
            trend = "↗"  # Diagonal up-right arrow
        else:
            trend = "↘"  # Diagonal down-right arrow

        # If new significant trend detected, start holding it
        if trend != " ":
            self.trend_hold_count[metric_name] = 3  # Hold for 3 cycles
            self.trend_directions[metric_name] = trend  # Store the actual direction
            return trend
        else:
            # No significant change and no active hold
            return " "  # Blank space for stable metrics


class ServicesTableWidget(DataTable):
    """Widget for displaying services using DataTable for proper performance"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.expanded_services: Set[str] = set()
        self.service_metrics: List[Dict] = []
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Set up the table columns"""
        self.add_column("Service", width=23)
        self.add_column("CPU", width=6)
        self.add_column("RAM", width=6)
        self.add_column("GPU", width=6)
        self.add_column("VRAM", width=6)
        self.add_column("Status", width=12)

    def update_services(self, service_metrics: List[Dict]):
        """Update the services table - simple rebuild approach for now"""
        # Store service metrics for later use
        self.service_metrics = service_metrics

        # Store the current cursor position to restore it
        current_cursor = self.cursor_coordinate

        # Clear and rebuild - this ensures consistency
        self.clear()

        # Rebuild the table
        for service_index, service in enumerate(service_metrics):
            service_name = service["service_name"]
            metrics = service["metrics"]

            # Format service display with expand/collapse indicator
            is_expanded = service_name in self.expanded_services
            expansion_indicator = "▼" if is_expanded else "▶"

            # Format service name
            service_display = f"{expansion_indicator} {service_name}"
            if service.get("port"):
                service_display += f":{service['port']}"

            # Format metrics
            cpu_str = (
                f"{metrics['cpu_percent']:.1f}%"
                if metrics["cpu_percent"] >= 0
                else "--"
            )
            memory_str = (
                self.format_bytes(int(metrics["memory_mb"] * 1024 * 1024))
                if metrics["memory_mb"] > 0
                else "--"
            )

            # GPU metrics
            gpu_vram_mb = metrics.get("gpu_vram_mb", 0)
            gpu_util_percent = metrics.get("gpu_util_percent", 0)

            if gpu_vram_mb > 0:
                gpu_str = f"{gpu_util_percent:.1f}%"
                vram_str = self.format_bytes(gpu_vram_mb * 1024 * 1024)
            else:
                gpu_str = "--"
                vram_str = "--"

            # Status with uptime
            if service["status"] == "active":
                uptime_str = self.format_uptime(metrics["uptime_seconds"])
                status = f"Running {uptime_str}"
            else:
                status = "Inactive"

            # Add the main service row
            self.add_row(
                service_display, cpu_str, memory_str, gpu_str, vram_str, status
            )

            # Add expanded details if service is expanded
            if is_expanded:
                self._add_detailed_metrics(service)

        # Restore cursor position if possible
        try:
            if current_cursor and current_cursor.row < self.row_count:
                self.move_cursor(row=current_cursor.row)
        except Exception as e:
            print(f"Cursor restore failed: {e}")

    def _needs_table_rebuild(self, previous: List[Dict], current: List[Dict]) -> bool:
        """Check if table structure has changed and needs rebuilding"""
        if len(previous) != len(current):
            return True

        # If this is the first run, we need to rebuild
        if not previous:
            return True

        # Check if service names changed
        for i, (prev, curr) in enumerate(zip(previous, current)):
            if prev["service_name"] != curr["service_name"]:
                return True

        # For now, only rebuild if expansion state changed
        # We'll skip expansion state checking to avoid constant rebuilds
        return False

    def _rebuild_table(self, service_metrics: List[Dict]):
        """Rebuild the entire table (only when structure changes)"""
        self.clear()

        for service_index, service in enumerate(service_metrics):
            service_name = service["service_name"]
            metrics = service["metrics"]

            # Format service display with expand/collapse indicator
            is_expanded = service_name in self.expanded_services
            expansion_indicator = "▼" if is_expanded else "▶"

            # Format service name
            service_display = f"{expansion_indicator} {service_name}"
            if service.get("port"):
                service_display += f":{service['port']}"

            # Format metrics
            cpu_str = (
                f"{metrics['cpu_percent']:.1f}%"
                if metrics["cpu_percent"] >= 0
                else "--"
            )
            memory_str = (
                self.format_bytes(int(metrics["memory_mb"] * 1024 * 1024))
                if metrics["memory_mb"] > 0
                else "--"
            )

            # GPU metrics
            gpu_vram_mb = metrics.get("gpu_vram_mb", 0)
            gpu_util_percent = metrics.get("gpu_util_percent", 0)

            if gpu_vram_mb > 0:
                gpu_str = f"{gpu_util_percent:.1f}%"
                vram_str = self.format_bytes(gpu_vram_mb * 1024 * 1024)
            else:
                gpu_str = "--"
                vram_str = "--"

            # Status with uptime
            if service["status"] == "active":
                uptime_str = self.format_uptime(metrics["uptime_seconds"])
                status = f"Running {uptime_str}"
            else:
                status = "Inactive"

            # Add the main service row
            self.add_row(
                service_display, cpu_str, memory_str, gpu_str, vram_str, status
            )

            # Add expanded details if service is expanded
            if is_expanded:
                self._add_detailed_metrics(service)

    def _update_existing_rows(self, service_metrics: List[Dict]):
        """Update only changed cells in existing rows"""
        row_index = 0

        for service_index, service in enumerate(service_metrics):
            service_name = service["service_name"]
            metrics = service["metrics"]

            # Format metrics
            cpu_str = (
                f"{metrics['cpu_percent']:.1f}%"
                if metrics["cpu_percent"] >= 0
                else "--"
            )
            memory_str = (
                self.format_bytes(int(metrics["memory_mb"] * 1024 * 1024))
                if metrics["memory_mb"] > 0
                else "--"
            )

            # GPU metrics
            gpu_vram_mb = metrics.get("gpu_vram_mb", 0)
            gpu_util_percent = metrics.get("gpu_util_percent", 0)

            if gpu_vram_mb > 0:
                gpu_str = f"{gpu_util_percent:.1f}%"
                vram_str = self.format_bytes(gpu_vram_mb * 1024 * 1024)
            else:
                gpu_str = "--"
                vram_str = "--"

            # Status with uptime
            if service["status"] == "active":
                uptime_str = self.format_uptime(metrics["uptime_seconds"])
                status = f"Running {uptime_str}"
            else:
                status = "Inactive"

            # Update only the changing cells (columns 1-5, skip service name)
            try:
                self.update_cell(row_index, 1, cpu_str)
                self.update_cell(row_index, 2, memory_str)
                self.update_cell(row_index, 3, gpu_str)
                self.update_cell(row_index, 4, vram_str)
                self.update_cell(row_index, 5, status)

                row_index += 1

                # Skip expanded detail rows
                if service_name in self.expanded_services:
                    row_index += 1  # Skip the single detail row

            except Exception:
                # If update fails, fallback to rebuild
                self._rebuild_table(service_metrics)
                break

    def _add_detailed_metrics(self, service: Dict):
        """Add detailed metrics rows to DataTable with proper formatting"""
        metrics = service["metrics"]
        pids = service.get("pids", [])

        # CPU detail with proper formatting
        cpu_percent = metrics.get("cpu_percent", 0)
        main_pid = pids[0] if pids else "N/A"
        threads = metrics.get("num_threads", 0)
        cpu_bar = self.create_progress_bar(cpu_percent, 8)

        self.add_row(
            f"  ├─ CPU: {cpu_bar} {cpu_percent:.1f}%",
            f"PID: {main_pid}",
            f"Threads: {threads}",
            "",
            "",
            "",
        )

        # Memory detail with proper formatting
        memory_mb = metrics.get("memory_mb", 0)
        memory_str = self.format_bytes(int(memory_mb * 1024 * 1024))
        self.add_row(f"  ├─ Memory: {memory_str}", "RSS Memory", "", "", "", "")

        # Network detail with proper formatting
        connections = metrics.get("connections", 0)
        self.add_row(
            "  ├─ Network: ↑--KB/s ↓--KB/s",
            f"Connections: {connections}",
            "",
            "",
            "",
            "",
        )

        # Disk I/O detail
        io_read_mb = metrics.get("io_read_mb", 0)
        io_write_mb = metrics.get("io_write_mb", 0)
        io_read_str = self.format_bytes(int(io_read_mb * 1024 * 1024))
        io_write_str = self.format_bytes(int(io_write_mb * 1024 * 1024))
        self.add_row(
            f"  ├─ Disk I/O: Read {io_read_str}/s",
            f"Write {io_write_str}/s",
            "",
            "",
            "",
            "",
        )

        # Uptime with proper formatting
        uptime_seconds = metrics.get("uptime_seconds", 0)
        uptime_str = self.format_uptime(uptime_seconds)
        self.add_row(f"  ╰─ Uptime: {uptime_str}", "", "", "", "", "")

    def _create_detailed_metrics_old(self, service: Dict) -> List[str]:
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
        """Move cursor up - use DataTable's built-in navigation"""
        self.action_cursor_up()

    def move_cursor_down(self):
        """Move cursor down - use DataTable's built-in navigation"""
        self.action_cursor_down()

    def get_selected_service_index(self) -> int:
        """Get the currently selected service index using DataTable cursor"""
        cursor_row = self.cursor_row
        # Map cursor row to service index, accounting for detail rows
        service_count = 0
        for i, service in enumerate(self.service_metrics):
            if service_count == cursor_row:
                return i
            service_count += 1
            # If service is expanded, skip the detail rows
            if service["service_name"] in self.expanded_services:
                service_count += 1  # Skip single detail row
        return 0

    def toggle_expansion(self, service_index: int):
        """Toggle expansion of a service"""
        if service_index < len(self.service_metrics):
            service_name = self.service_metrics[service_index]["service_name"]

            if service_name in self.expanded_services:
                self.expanded_services.remove(service_name)
                # Debug: notify about collapse
                print(f"DEBUG: Collapsing {service_name}")
            else:
                # Clear other expanded services (only one expanded at a time)
                self.expanded_services.clear()
                self.expanded_services.add(service_name)
                # Debug: notify about expand
                print(f"DEBUG: Expanding {service_name}")

            # Refresh the display
            self.update_services(self.service_metrics)


class MetricsApp(App):
    """Main Textual application for the metrics dashboard"""

    # Disable mouse support to avoid SSH terminal issues
    ENABLE_COMMAND_PALETTE = False

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

    ServiceActionsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }

    #actions-modal {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        border-title-color: $secondary;
        border-title-style: bold;
        padding: 2;
        margin: 2;
        min-height: 10;
    }

    #service-title {
        text-align: center;
        color: $secondary;
        text-style: bold;
        margin-bottom: 1;
    }

    #action-prompt {
        text-align: center;
        margin-bottom: 1;
    }

    #actions-modal Button {
        width: 100%;
        margin-bottom: 1;
    }

    #action-cancel {
        color: $error;
        background: $surface;
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

    def __init__(
        self,
        refresh_interval: float = 0.1,
        data_refresh_interval: float = 2.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # Disable mouse support for SSH compatibility
        self.mouse_capture = False
        self.refresh_interval = refresh_interval  # Fast UI updates
        self.data_refresh_interval = data_refresh_interval  # Slower data collection
        self.system_widget = None
        self.services_widget = None
        self.status_widget = None

        # Background data collector
        self.data_collector = BackgroundDataCollector(data_refresh_interval)
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
        self.data_collector.set_hardware_info(self.hardware_info)

        # Start background data collection
        self.data_collector.start()

        # Do initial sync data collection to avoid loading state
        system_data = get_all_metrics()
        service_data = get_all_service_metrics()

        # Set initial data in collector
        with self.data_collector.lock:
            self.data_collector.system_metrics = system_data
            self.data_collector.service_metrics = service_data
            self.data_collector.last_update = time.time()

        # Start fast UI update loop (just refreshes from cached data)
        self.set_interval(self.refresh_interval, self.update_display)

        # Initial update
        await self.update_display()

        # Set focus to services widget for keyboard navigation
        self.services_widget.focus()

    async def on_unmount(self) -> None:
        """Cleanup when app shuts down"""
        self.data_collector.stop()

    async def update_display(self) -> None:
        """Update display from cached data (fast, no blocking)"""
        # Get cached data from background collector
        data = self.data_collector.get_data()

        if not data["system_metrics"] or not data["service_metrics"]:
            # No data yet, show loading
            self.status_widget.update("Loading metrics...")
            return

        # Debug: Log when we actually update
        # print(f"Updating display with data: {len(data['system_metrics'])} system, {len(data['service_metrics'])} services")

        # Update widgets with cached data (instant)
        self.system_widget.update_metrics(data["system_metrics"])
        self.services_widget.update_services(data["service_metrics"])

        # Update border titles with counts
        service_metrics = data["service_metrics"]
        total_services = len(service_metrics)
        running_services = sum(1 for s in service_metrics if s["status"] == "active")
        self.services_widget.border_title = (
            f"Services ({total_services} total, {running_services} running)"
        )

        # Update status bar without current time
        data_time = (
            time.strftime("%H:%M:%S", time.localtime(data["last_update"]))
            if data["last_update"]
            else "00:00:00"
        )
        self.status_widget.update(
            f"Data: {data_time} | ↑↓ Navigate | → Expand | ← Collapse | Enter Actions | q Quit"
        )

    def action_cursor_up(self) -> None:
        """Move cursor up in services table"""
        self.services_widget.move_cursor_up()

    def action_cursor_down(self) -> None:
        """Move cursor down in services table"""
        self.services_widget.move_cursor_down()

    def action_expand_service(self) -> None:
        """Expand selected service"""
        if not self.services_widget.service_metrics:
            self.notify("No services available", title="Debug", timeout=2)
            return

        service_index = self.services_widget.get_selected_service_index()
        if service_index < len(self.services_widget.service_metrics):
            service_name = self.services_widget.service_metrics[service_index][
                "service_name"
            ]
            self.notify(
                f"Expanding service: {service_name} (index: {service_index})",
                title="Debug",
                timeout=2,
            )
            self.services_widget.toggle_expansion(service_index)
        else:
            self.notify(
                f"Invalid service index: {service_index}/{len(self.services_widget.service_metrics)}",
                title="Debug",
                timeout=2,
            )

    def action_collapse_service(self) -> None:
        """Collapse selected service"""
        service_index = self.services_widget.get_selected_service_index()
        if service_index < len(self.services_widget.service_metrics):
            service_name = self.services_widget.service_metrics[service_index][
                "service_name"
            ]
            self.services_widget.expanded_services.discard(service_name)
            self.services_widget.update_services(self.services_widget.service_metrics)

    async def action_service_actions(self) -> None:
        """Show service actions menu"""
        service_index = self.services_widget.get_selected_service_index()

        if service_index < len(self.services_widget.service_metrics):
            service = self.services_widget.service_metrics[service_index]
            service_name = service["service_name"]
            status = service["status"]

            # Create and show the modal
            modal = ServiceActionsModal(service_name, status)

            # Show modal and wait for result
            action = await self.push_screen(modal)

            # Handle the selected action if one was chosen
            if action:
                await self.handle_service_action(service_name, action)

    async def handle_service_action(self, service_name: str, action: str) -> None:
        """Handle the selected service action"""
        if action == "start":
            self.notify(
                f"Starting {service_name}...", title="Service Action", timeout=3
            )
            # TODO: Implement actual service start
        elif action == "stop":
            self.notify(
                f"Stopping {service_name}...", title="Service Action", timeout=3
            )
            # TODO: Implement actual service stop
        elif action == "restart":
            self.notify(
                f"Restarting {service_name}...", title="Service Action", timeout=3
            )
            # TODO: Implement actual service restart
        elif action == "logs":
            self.notify(
                f"Opening logs for {service_name}...", title="Service Action", timeout=3
            )
            # TODO: Implement log viewing
        elif action == "browser":
            self.notify(
                f"Opening browser for {service_name}...",
                title="Service Action",
                timeout=3,
            )
            # TODO: Implement browser opening


def run_metrics_dashboard(refresh_interval: float = 2.0):
    """Run the metrics dashboard application"""
    # Use fast UI updates (0.1s) with slower data collection (2.0s default)
    app = MetricsApp(refresh_interval=0.1, data_refresh_interval=refresh_interval)
    app.run()


if __name__ == "__main__":
    run_metrics_dashboard()
