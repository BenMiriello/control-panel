#!/usr/bin/env python3

import time
from typing import Dict, List

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class MetricsFormatter:
    """Handles formatting and display of metrics data"""

    def __init__(self):
        self.console = Console()
        self.hardware_info = None

    def set_hardware_info(self, hardware_info: Dict):
        """Set hardware information for display enhancement"""
        self.hardware_info = hardware_info

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format"""
        if bytes_value == 0:
            return "0B"

        for unit in ["B", "K", "M", "G", "T"]:
            if bytes_value < 1024:
                if unit == "B":
                    return f"{bytes_value}{unit}"
                else:
                    return f"{bytes_value:.1f}{unit}"
            bytes_value = int(bytes_value / 1024)
        return f"{bytes_value:.1f}P"

    def format_uptime(self, seconds: float) -> str:
        """Format uptime seconds into human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h{minutes}m" if minutes > 0 else f"{hours}h"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d{hours}h" if hours > 0 else f"{days}d"

    def create_progress_bar(self, percentage: float, width: int = 10) -> str:
        """Create a text-based progress bar"""
        filled = int(percentage / 100 * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def format_trend_indicator(self, current: float, previous: float) -> tuple:
        """Format trend indicator with color"""
        if previous is None:
            return "→", "white"

        diff = current - previous
        if abs(diff) < 0.1:  # Stable threshold
            return "→", "white"
        elif diff > 0:
            return "↑", "green"
        else:
            return "↓", "red"

    def create_system_panel(
        self, system_metrics: Dict, previous_metrics: Dict = None
    ) -> Panel:
        """Create the system metrics panel"""
        lines = []

        # CPU
        cpu_usage = system_metrics["cpu"]["usage"]
        cpu_bar = self.create_progress_bar(cpu_usage)
        cpu_trend, cpu_color = self.format_trend_indicator(
            cpu_usage, previous_metrics["cpu"]["usage"] if previous_metrics else None
        )

        cpu_info = ""
        if self.hardware_info and "cpu" in self.hardware_info:
            cpu_model = self.hardware_info["cpu"]["model"]
            cpu_cores = self.hardware_info["cpu"]["cores"]
            cpu_info = f"   {cpu_cores} cores ({cpu_model})"

        lines.append(
            f"CPU:     {cpu_usage:5.1f}% {cpu_bar} [{cpu_color}]{cpu_trend}[/] {cpu_info}"
        )

        # Memory
        memory = system_metrics["memory"]
        memory_percent = memory["percent"]
        memory_bar = self.create_progress_bar(memory_percent)
        memory_trend, memory_color = self.format_trend_indicator(
            memory_percent,
            previous_metrics["memory"]["percent"] if previous_metrics else None,
        )

        memory_used = self.format_bytes(memory["used"])
        memory_total = self.format_bytes(memory["total"])
        memory_type = ""
        if self.hardware_info and "memory" in self.hardware_info:
            mem_info = self.hardware_info["memory"]
            if mem_info["type"] != "RAM":
                memory_type = f" {mem_info['type']}"

        lines.append(
            f"Memory:  {memory_percent:5.1f}% {memory_bar} [{memory_color}]{memory_trend}[/]   {memory_used}/{memory_total}{memory_type}"
        )

        # GPU (if available)
        gpu_info = system_metrics.get("gpu", {})
        if gpu_info.get("available", False) and gpu_info.get("gpus"):
            gpu = gpu_info["gpus"][0]  # Show first GPU
            gpu_util = gpu["util_percent"]
            gpu_bar = self.create_progress_bar(gpu_util)
            gpu_trend, gpu_trend_color = self.format_trend_indicator(gpu_util, None)

            gpu_name = ""
            if self.hardware_info and self.hardware_info["gpu"]["available"]:
                gpu_name = f"   {self.hardware_info['gpu']['gpus'][0]['name']}"

            lines.append(
                f"GPU:     {gpu_util:5.1f}% {gpu_bar} [{gpu_trend_color}]{gpu_trend}[/] {gpu_name}"
            )

            # VRAM
            gpu_mem_used = gpu["memory_used"] * 1024 * 1024  # Convert MB to bytes
            gpu_mem_total = gpu["memory_total"] * 1024 * 1024
            gpu_mem_percent = (
                (gpu_mem_used / gpu_mem_total) * 100 if gpu_mem_total > 0 else 0
            )
            vram_bar = self.create_progress_bar(gpu_mem_percent)

            gpu_mem_used_str = self.format_bytes(gpu_mem_used)
            gpu_mem_total_str = self.format_bytes(gpu_mem_total)

            lines.append(
                f"VRAM:    {gpu_mem_percent:5.1f}% {vram_bar} [{gpu_trend_color}]{gpu_trend}[/]   {gpu_mem_used_str}/{gpu_mem_total_str}"
            )

        # Disk
        disk = system_metrics["disk"]
        disk_percent = disk["percent"]
        disk_bar = self.create_progress_bar(disk_percent)
        disk_trend, disk_color = self.format_trend_indicator(
            disk_percent,
            previous_metrics["disk"]["percent"] if previous_metrics else None,
        )

        disk_used = self.format_bytes(disk["used"])
        disk_total = self.format_bytes(disk["total"])
        storage_type = ""
        if self.hardware_info and "storage" in self.hardware_info:
            storage_type = f" {self.hardware_info['storage']['type']}"

        lines.append(
            f"Disk:    {disk_percent:5.1f}% {disk_bar} [{disk_color}]{disk_trend}[/]   {disk_used}/{disk_total}{storage_type}"
        )

        # Temperature (if available)
        temp_info = system_metrics["cpu"].get("temperature", {})
        if temp_info.get("available", False) and temp_info.get("sensors"):
            # Find CPU temperature
            cpu_temp = None
            gpu_temp = None

            for sensor in temp_info["sensors"]:
                if "cpu" in sensor["type"].lower() or "core" in sensor["type"].lower():
                    cpu_temp = sensor["temp"]
                    break

            # GPU temperature from GPU metrics
            if gpu_info.get("available", False) and gpu_info.get("gpus"):
                gpu_temp = gpu_info["gpus"][0].get("temperature")

            if cpu_temp is not None:
                temp_status = (
                    "Normal" if cpu_temp < 70 else ("Warm" if cpu_temp < 85 else "Hot")
                )
                temp_color = (
                    "green" if cpu_temp < 70 else ("yellow" if cpu_temp < 85 else "red")
                )

                temp_details = f"CPU: {cpu_temp:.0f}°C"
                if gpu_temp is not None:
                    temp_details += f" | GPU: {gpu_temp:.0f}°C"

                lines.append(
                    f"Temp:    {cpu_temp:5.0f}°C  [{temp_color}][{temp_status}][/]     [{disk_color}]{disk_trend}[/] 1°C    {temp_details}"
                )

        content = "\n".join(lines)
        return Panel(content, title="System Metrics (Live)", border_style="blue")

    def create_services_table(
        self,
        service_metrics: List[Dict],
        selected_index: int = 0,
        expanded_services: set = None,
    ) -> Panel:
        """Create the services table with proper expanded view layout"""
        if expanded_services is None:
            expanded_services = set()

        content_lines = []

        # Create header
        content_lines.append(
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓"
        )
        content_lines.append(
            "┃ Service                   ┃    CPU ┃    RAM ┃     GPU ┃    VRAM ┃ Status          ┃"
        )
        content_lines.append(
            "┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩"
        )

        total_services = len(service_metrics)
        running_services = sum(1 for s in service_metrics if s["status"] == "active")

        for i, service in enumerate(service_metrics):
            # Selection indicator and expansion indicator
            selection_indicator = "●" if i == selected_index else " "
            expansion_indicator = (
                "▼" if service["service_name"] in expanded_services else "▶"
            )
            service_name = (
                f"{selection_indicator} {expansion_indicator} {service['service_name']}"
            )
            if service.get("port"):
                service_name += f":{service['port']}"

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

            # Create service row with proper formatting
            service_row = f"│ {service_name:<25} │ {cpu_str:>6} │ {memory_str:>6} │ {gpu_str:>7} │ {vram_str:>7} │ {status:<15} │"

            if i == selected_index:
                content_lines.append(f"[bold green]{service_row}[/]")
            else:
                content_lines.append(service_row)

            # Add expanded details as separate full-width panel
            if service["service_name"] in expanded_services:
                content_lines.extend(
                    self._create_detailed_metrics_panel(service, i == selected_index)
                )

        # Close table
        content_lines.append(
            "└───────────────────────────┴────────┴────────┴─────────┴─────────┴─────────────────┘"
        )

        # Join all content
        content = "\n".join(content_lines)

        title = f"Services ({total_services} total, {running_services} running)"
        return Panel(content, title=title, border_style="blue")

    def _create_detailed_metrics_panel(
        self, service: Dict, is_selected: bool
    ) -> List[str]:
        """Create detailed metrics panel in nested box format matching roadmap specification"""
        metrics = service["metrics"]
        pids = service.get("pids", [])

        # Style for detail rows
        detail_style = "[dim cyan]" if is_selected else "[dim]"
        end_style = "[/]"

        lines = []

        # Create nested detail box with proper indentation
        lines.append(
            "│ │ ├───────────────────────────────────────────────────────────────────────────────╮ │"
        )

        # CPU Usage detail with progress bar and PID info
        cpu_percent = metrics.get("cpu_percent", 0)
        cpu_bar = self.create_progress_bar(cpu_percent, width=12)
        main_pid = pids[0] if pids else "N/A"
        threads = metrics.get("num_threads", 0)
        lines.append(
            f"│ │ │ {detail_style}CPU Usage:    {cpu_bar} {cpu_percent:5.1f}%  (PID: {main_pid}, Threads: {threads}){end_style}                 │ │"
        )

        # Memory detail with RSS info
        memory_mb = metrics.get("memory_mb", 0)
        memory_bytes = int(memory_mb * 1024 * 1024)
        memory_str = self.format_bytes(memory_bytes)
        lines.append(
            f"│ │ │ {detail_style}Memory:       {memory_str:>8}  (RSS: {memory_str}){end_style}                                          │ │"
        )

        # GPU detail if available
        gpu_vram_mb = metrics.get("gpu_vram_mb", 0)
        gpu_util_percent = metrics.get("gpu_util_percent", 0)
        if gpu_vram_mb > 0:
            gpu_bar = self.create_progress_bar(gpu_util_percent, width=12)
            vram_str = self.format_bytes(gpu_vram_mb * 1024 * 1024)
            lines.append(
                f"│ │ │ {detail_style}GPU Usage:    {gpu_bar} {gpu_util_percent:5.1f}%  (VRAM: {vram_str}){end_style}                     │ │"
            )

        # Network detail
        connections = metrics.get("connections", 0)
        lines.append(
            f"│ │ │ {detail_style}Network:      ↑--KB/s ↓--KB/s  (Connections: {connections}){end_style}                               │ │"
        )

        # Disk I/O detail
        io_read_mb = metrics.get("io_read_mb", 0)
        io_write_mb = metrics.get("io_write_mb", 0)
        io_read_str = self.format_bytes(int(io_read_mb * 1024 * 1024))
        io_write_str = self.format_bytes(int(io_write_mb * 1024 * 1024))
        lines.append(
            f"│ │ │ {detail_style}Disk I/O:     Read: {io_read_str:>6}/s  Write: {io_write_str:>6}/s{end_style}                                 │ │"
        )

        # Process uptime
        uptime_seconds = metrics.get("uptime_seconds", 0)
        uptime_str = self.format_uptime(uptime_seconds)
        lines.append(
            f"│ │ │ {detail_style}Uptime:       {uptime_str}{end_style}                                                            │ │"
        )

        # Close nested detail box
        lines.append(
            "│ │ ╰───────────────────────────────────────────────────────────────────────────────╯ │"
        )

        return lines

    def _add_service_details(self, table: Table, service: Dict, is_selected: bool):
        """Add expanded details for a service in roadmap format"""
        metrics = service["metrics"]
        pids = service.get("pids", [])

        # Style for detail rows
        detail_style = "[dim cyan]" if is_selected else "[dim]"
        end_style = "[/]"

        # Create detail box header
        table.add_row(
            f"{detail_style}│ ┌─ Detailed Metrics ─────────────────────────────────────────┐{end_style}",
            "",
            "",
            "",
            "",
            "",
        )

        # CPU Usage detail with progress bar and PID info
        cpu_percent = metrics.get("cpu_percent", 0)
        cpu_bar = self.create_progress_bar(cpu_percent, width=8)
        main_pid = pids[0] if pids else "N/A"
        threads = metrics.get("num_threads", 0)
        table.add_row(
            f"{detail_style}│ │ CPU Usage: {cpu_bar} {cpu_percent:.1f}% (PID: {main_pid}, Threads: {threads}){end_style}",
            "",
            "",
            "",
            "",
            "",
        )

        # Memory detail with RSS info
        memory_mb = metrics.get("memory_mb", 0)
        memory_bytes = int(memory_mb * 1024 * 1024)
        memory_percent = (memory_mb / (64 * 1024)) * 100  # Rough estimate for bar
        memory_bar = self.create_progress_bar(min(memory_percent, 100), width=8)
        memory_str = self.format_bytes(memory_bytes)
        table.add_row(
            f"{detail_style}│ │ Memory:    {memory_bar} {memory_str} (RSS: {memory_str}){end_style}",
            "",
            "",
            "",
            "",
            "",
        )

        # Network detail
        connections = metrics.get("connections", 0)
        table.add_row(
            f"{detail_style}│ │ Network:   ↑--KB/s ↓--KB/s (Connections: {connections}){end_style}",
            "",
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
        table.add_row(
            f"{detail_style}│ │ Disk I/O:  Read: {io_read_str}/s Write: {io_write_str}/s{end_style}",
            "",
            "",
            "",
            "",
            "",
        )

        # Close detail box
        table.add_row(
            f"{detail_style}│ └────────────────────────────────────────────────────────────┘{end_style}",
            "",
            "",
            "",
            "",
            "",
        )

    def create_help_text(self) -> Text:
        """Create help text for controls"""
        timestamp = time.strftime("%H:%M:%S")
        help_parts = [
            f"Last updated: {timestamp}",
            "↑↓ Navigate",
            "→ Expand",
            "← Collapse",
            "Enter Actions",
            "q Quit",
        ]
        return Text(" | ".join(help_parts), style="dim")

    def create_layout(
        self,
        system_metrics: Dict,
        service_metrics: List[Dict],
        selected_index: int = 0,
        previous_system_metrics: Dict = None,
        terminal_height: int = None,
        expanded_services: set = None,
    ) -> Layout:
        """Create the main layout with vertical centering and dynamic sizing"""
        layout = Layout()

        # Calculate content heights dynamically
        # System panel: CPU, Memory, Disk (3) + GPU/VRAM (2 if available) + temp (1 if available) + borders (2)
        base_lines = 3  # CPU, Memory, Disk
        gpu_lines = 2 if system_metrics.get("gpu", {}).get("available", False) else 0
        temp_lines = (
            1
            if system_metrics.get("cpu", {})
            .get("temperature", {})
            .get("available", False)
            else 0
        )
        border_lines = 2  # Top and bottom borders
        system_height = base_lines + gpu_lines + temp_lines + border_lines
        help_height = 1  # Fixed height for help text

        # Dynamic services height: header(3) + services + expanded details + borders(2) + bottom line(1)
        if expanded_services is None:
            expanded_services = set()

        expanded_count = sum(
            1 for s in service_metrics if s["service_name"] in expanded_services
        )
        # Calculate lines per expanded service: top border + CPU + Memory + GPU (if available) + Network + Disk I/O + Uptime + bottom border
        lines_per_service = 7  # Base: top border + CPU + Memory + Network + Disk I/O + Uptime + bottom border
        # Add 1 more line for GPU if any service has GPU usage
        if any(
            s.get("metrics", {}).get("gpu_vram_mb", 0) > 0
            for s in service_metrics
            if s["service_name"] in expanded_services
        ):
            lines_per_service += 1
        expanded_detail_lines = expanded_count * lines_per_service

        services_content_height = (
            len(service_metrics) + expanded_detail_lines + 6
        )  # base services + expansion details + header + borders

        # Calculate total content height
        total_content_height = system_height + services_content_height + help_height

        # Calculate vertical padding for centering (if terminal height provided)
        if terminal_height and total_content_height < terminal_height:
            padding_needed = terminal_height - total_content_height
            top_padding = padding_needed // 2
            bottom_padding = padding_needed - top_padding

            # Create layout with padding
            layout.split_column(
                Layout(name="top_pad", size=top_padding),
                Layout(name="system", size=system_height),
                Layout(name="services", size=services_content_height),
                Layout(name="help", size=help_height),
                Layout(name="bottom_pad", size=bottom_padding),
            )

            # Add empty content to padding areas
            layout["top_pad"].update("")
            layout["bottom_pad"].update("")
        else:
            # No centering needed or terminal too small
            layout.split_column(
                Layout(name="system", size=system_height),
                Layout(name="services", size=services_content_height),
                Layout(name="help", size=help_height),
            )

        layout["system"].update(
            self.create_system_panel(system_metrics, previous_system_metrics)
        )
        layout["services"].update(
            self.create_services_table(
                service_metrics, selected_index, expanded_services
            )
        )
        layout["help"].update(self.create_help_text())

        return layout
