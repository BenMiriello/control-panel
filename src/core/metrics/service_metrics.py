#!/usr/bin/env python3

import subprocess
import time
from typing import Dict, List, Optional

import psutil

from ..config import load_config


def get_gpu_usage_by_pid() -> Dict[int, Dict]:
    """Get GPU usage by PID using pynvml for real utilization data"""
    gpu_usage = {}

    try:
        # First try pynvml for real GPU utilization percentages
        import pynvml

        pynvml.nvmlInit()

        device_count = pynvml.nvmlDeviceGetCount()
        for device_idx in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_idx)

            # Get process utilization (GPU % usage per process)
            try:
                processes = pynvml.nvmlDeviceGetProcessUtilization(handle, 0)
                for proc in processes:
                    if hasattr(proc, "pid"):
                        pid = proc.pid
                        gpu_usage[pid] = {
                            "gpu_util_percent": proc.smUtil,  # GPU compute utilization %
                            "gpu_mem_percent": proc.memUtil,  # GPU memory utilization %
                            "vram_mb": 0,  # Will be filled from nvidia-smi below
                            "gpu_uuid": None,
                        }
            except (AttributeError, pynvml.NVMLError):
                # nvmlDeviceGetProcessUtilization not available or no data
                pass

    except (ImportError, Exception) as e:
        # pynvml not available, fallback to basic nvidia-smi
        print(f"pynvml unavailable: {e}")

    try:
        # Still get VRAM usage from nvidia-smi (more reliable for memory)
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory,gpu_uuid",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    try:
                        pid = int(parts[0])
                        vram_mb = int(parts[1])

                        # Update existing entry or create new one
                        if pid in gpu_usage:
                            gpu_usage[pid]["vram_mb"] = vram_mb
                            gpu_usage[pid]["gpu_uuid"] = (
                                parts[2] if len(parts) > 2 else None
                            )
                        else:
                            # No pynvml data, just VRAM info
                            gpu_usage[pid] = {
                                "gpu_util_percent": 0,  # Unknown without pynvml
                                "gpu_mem_percent": 0,
                                "vram_mb": vram_mb,
                                "gpu_uuid": parts[2] if len(parts) > 2 else None,
                            }
                    except ValueError:
                        continue

    except (subprocess.CalledProcessError, FileNotFoundError):
        # NVIDIA tools not available or no GPU processes
        pass

    return gpu_usage


def get_service_pids(service_name: str) -> List[int]:
    """Get all PIDs for a systemd service"""
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                f"control-panel@{service_name}.service",
                "-p",
                "MainPID",
                "-p",
                "ControlGroup",
                "--value",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.strip().split("\n")
        main_pid = int(lines[0]) if lines[0] and lines[0] != "0" else None

        pids = []
        if main_pid and psutil.pid_exists(main_pid):
            # Get main process and all children
            try:
                main_proc = psutil.Process(main_pid)
                pids.append(main_pid)
                pids.extend([child.pid for child in main_proc.children(recursive=True)])
            except psutil.NoSuchProcess:
                pass

        return pids
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return []


def get_process_metrics(pid: int) -> Optional[Dict]:
    """Get resource metrics for a specific PID"""
    try:
        proc = psutil.Process(pid)

        # Get basic metrics - use non-blocking CPU measurement for speed
        cpu_percent = proc.cpu_percent(interval=None)
        memory_info = proc.memory_info()

        # Get I/O stats if available
        try:
            io_counters = proc.io_counters()
            io_stats = {
                "read_bytes": io_counters.read_bytes,
                "write_bytes": io_counters.write_bytes,
            }
        except (psutil.AccessDenied, AttributeError):
            io_stats = {"read_bytes": 0, "write_bytes": 0}

        # Get network connections count
        try:
            connections = len(proc.connections())
        except psutil.AccessDenied:
            connections = 0

        return {
            "pid": pid,
            "cpu_percent": cpu_percent,
            "memory_rss": memory_info.rss,
            "memory_vms": memory_info.vms,
            "num_threads": proc.num_threads(),
            "io_stats": io_stats,
            "connections": connections,
            "status": proc.status(),
            "create_time": proc.create_time(),
        }
    except psutil.NoSuchProcess:
        return None


def aggregate_process_metrics(metrics_list: List[Dict], pids: List[int]) -> Dict:
    """Aggregate metrics from multiple processes including GPU usage"""
    if not metrics_list:
        return {
            "cpu_percent": 0.0,
            "memory_mb": 0,
            "num_threads": 0,
            "connections": 0,
            "io_read_mb": 0.0,
            "io_write_mb": 0.0,
            "gpu_vram_mb": 0,
            "oldest_create_time": None,
        }

    total_cpu = sum(m["cpu_percent"] for m in metrics_list)
    total_memory = sum(m["memory_rss"] for m in metrics_list)
    total_threads = sum(m["num_threads"] for m in metrics_list)
    total_connections = sum(m["connections"] for m in metrics_list)
    total_read = sum(m["io_stats"]["read_bytes"] for m in metrics_list)
    total_write = sum(m["io_stats"]["write_bytes"] for m in metrics_list)
    oldest_time = min(m["create_time"] for m in metrics_list)

    # Get GPU usage for all PIDs in this service
    gpu_usage_by_pid = get_gpu_usage_by_pid()
    total_vram = sum(gpu_usage_by_pid.get(pid, {}).get("vram_mb", 0) for pid in pids)
    max_gpu_util = max(
        (gpu_usage_by_pid.get(pid, {}).get("gpu_util_percent", 0) for pid in pids),
        default=0,
    )

    return {
        "cpu_percent": total_cpu,
        "memory_mb": total_memory / (1024 * 1024),
        "num_threads": total_threads,
        "connections": total_connections,
        "io_read_mb": total_read / (1024 * 1024),
        "io_write_mb": total_write / (1024 * 1024),
        "gpu_vram_mb": total_vram,
        "gpu_util_percent": max_gpu_util,
        "oldest_create_time": oldest_time,
    }


def get_service_metrics(service_name: str) -> Dict:
    """Get comprehensive metrics for a service"""
    config = load_config()

    if service_name not in config["services"]:
        return {"available": False, "error": "Service not found"}

    service_config = config["services"][service_name]

    # Get service status
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "is-active",
                f"control-panel@{service_name}.service",
            ],
            capture_output=True,
            text=True,
        )
        is_active = result.stdout.strip() == "active"
    except subprocess.CalledProcessError:
        is_active = False

    if not is_active:
        return {
            "available": True,
            "service_name": service_name,
            "status": "inactive",
            "port": service_config.get("port"),
            "metrics": {
                "cpu_percent": 0.0,
                "memory_mb": 0,
                "num_threads": 0,
                "connections": 0,
                "io_read_mb": 0.0,
                "io_write_mb": 0.0,
                "gpu_vram_mb": 0,
                "gpu_util_percent": 0,
                "uptime_seconds": 0,
            },
        }

    # Get PIDs and collect metrics
    pids = get_service_pids(service_name)
    process_metrics = []

    for pid in pids:
        metrics = get_process_metrics(pid)
        if metrics:
            process_metrics.append(metrics)

    # Aggregate metrics
    aggregated = aggregate_process_metrics(process_metrics, pids)

    # Calculate uptime
    uptime_seconds = 0
    if aggregated["oldest_create_time"]:
        uptime_seconds = time.time() - aggregated["oldest_create_time"]

    return {
        "available": True,
        "service_name": service_name,
        "status": "active",
        "port": service_config.get("port"),
        "pids": pids,
        "metrics": {
            "cpu_percent": aggregated["cpu_percent"],
            "memory_mb": aggregated["memory_mb"],
            "num_threads": aggregated["num_threads"],
            "connections": aggregated["connections"],
            "io_read_mb": aggregated["io_read_mb"],
            "io_write_mb": aggregated["io_write_mb"],
            "gpu_vram_mb": aggregated["gpu_vram_mb"],
            "gpu_util_percent": aggregated["gpu_util_percent"],
            "uptime_seconds": uptime_seconds,
        },
    }


def get_all_service_metrics() -> List[Dict]:
    """Get metrics for all registered services"""
    config = load_config()
    service_metrics = []

    for service_name in config["services"].keys():
        metrics = get_service_metrics(service_name)
        if metrics["available"]:
            service_metrics.append(metrics)

    return service_metrics
