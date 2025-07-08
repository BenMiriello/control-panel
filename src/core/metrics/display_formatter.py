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
            bytes_value /= 1024
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
            f"CPU:     {cpu_usage:5.1f}% {cpu_bar} [{cpu_color}]{cpu_trend}[/] {cpu_usage:4.1f}%{cpu_info}"
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
            f"Memory:  {memory_percent:5.1f}% {memory_bar} [{memory_color}]{memory_trend}[/] {memory_percent:4.1f}%   {memory_used}/{memory_total}{memory_type}"
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
                f"GPU:     {gpu_util:5.1f}% {gpu_bar} [{gpu_trend_color}]{gpu_trend}[/] {gpu_util:4.1f}%{gpu_name}"
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
                f"VRAM:    {gpu_mem_percent:5.1f}% {vram_bar} [{gpu_trend_color}]{gpu_trend}[/] {gpu_mem_percent:4.1f}%   {gpu_mem_used_str}/{gpu_mem_total_str}"
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
            f"Disk:    {disk_percent:5.1f}% {disk_bar} [{disk_color}]{disk_trend}[/] {disk_percent:4.1f}%   {disk_used}/{disk_total}{storage_type}"
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
        self, service_metrics: List[Dict], selected_index: int = 0
    ) -> Panel:
        """Create the services table panel"""
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Service", style="white", width=25)
        table.add_column("CPU", justify="right", width=6)
        table.add_column("RAM", justify="right", width=6)
        table.add_column("GPU", justify="right", width=5)
        table.add_column("VRAM", justify="right", width=7)
        table.add_column("Status", width=15)

        total_services = len(service_metrics)
        running_services = sum(1 for s in service_metrics if s["status"] == "active")

        for i, service in enumerate(service_metrics):
            # Selection indicator
            indicator = "●" if i == selected_index else " "
            service_name = f"{indicator} {service['service_name']}"
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

            # GPU metrics - show percentage of system GPU usage (estimated)
            gpu_vram_mb = metrics.get("gpu_vram_mb", 0)
            if gpu_vram_mb > 0:
                # For GPU utilization, we can't easily get per-process GPU %, so show active indicator
                gpu_str = "CUDA"  # Indicates CUDA/GPU usage
                vram_str = self.format_bytes(gpu_vram_mb * 1024 * 1024)
            else:
                gpu_str = "--"
                vram_str = "--"

            # Status with uptime
            if service["status"] == "active":
                uptime_str = self.format_uptime(metrics["uptime_seconds"])
                status = f"Running {uptime_str}"
                status_style = "green"
            else:
                status = "Inactive"
                status_style = "dim"

            # Add row with conditional styling
            if i == selected_index:
                table.add_row(
                    f"[bold green]{service_name}[/]",
                    f"[bold]{cpu_str}[/]",
                    f"[bold]{memory_str}[/]",
                    f"[bold]{gpu_str}[/]",
                    f"[bold]{vram_str}[/]",
                    f"[bold {status_style}]{status}[/]",
                )
            else:
                table.add_row(
                    service_name,
                    cpu_str,
                    memory_str,
                    gpu_str,
                    vram_str,
                    f"[{status_style}]{status}[/]",
                )

        title = f"Services ({total_services} total, {running_services} running)"
        return Panel(table, title=title, border_style="blue")

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

        # Dynamic services height: header(3) + services + borders(2) + bottom line(1)
        services_content_height = (
            len(service_metrics) + 6
        )  # 3 for header, 2 for borders, 1 for bottom

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
            self.create_services_table(service_metrics, selected_index)
        )
        layout["help"].update(self.create_help_text())

        return layout
