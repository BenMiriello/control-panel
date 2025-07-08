#!/usr/bin/env python3

import json
import re
import subprocess
from typing import Dict, Optional


def detect_cpu_info() -> Dict:
    """Detect CPU model and core count"""
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()

        # Extract model name
        model_match = re.search(r"model name\s*:\s*(.+)", cpuinfo)
        model = model_match.group(1).strip() if model_match else "Unknown CPU"

        # Clean up common CPU name patterns
        model = re.sub(r"\s+", " ", model)  # Multiple spaces
        model = re.sub(r"\(R\)|\(TM\)", "", model)  # Remove trademark symbols
        model = model.replace("Intel(R)", "").replace("AMD", "").strip()

        # Get core count
        core_count = len(re.findall(r"^processor\s*:", cpuinfo, re.MULTILINE))

        return {"model": model, "cores": core_count, "architecture": _detect_cpu_arch()}
    except (OSError, AttributeError):
        return {"model": "Unknown CPU", "cores": 1, "architecture": "unknown"}


def _detect_cpu_arch() -> str:
    """Detect CPU architecture"""
    try:
        result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
        arch = result.stdout.strip()

        # Normalize architecture names
        if arch in ["x86_64", "amd64"]:
            return "x64"
        elif arch in ["aarch64", "arm64"]:
            return "ARM64"
        elif arch.startswith("arm"):
            return "ARM"
        else:
            return arch
    except subprocess.CalledProcessError:
        return "unknown"


def detect_memory_info() -> Dict:
    """Detect memory type and configuration"""
    try:
        # Try to get memory info from dmidecode (requires root)
        try:
            result = subprocess.run(
                ["sudo", "dmidecode", "-t", "memory"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                output = result.stdout

                # Extract memory type (DDR4, DDR5, etc.)
                type_match = re.search(r"Type:\s*(DDR\d+)", output)
                memory_type = type_match.group(1) if type_match else None

                # Extract speed
                speed_match = re.search(r"Speed:\s*(\d+)\s*MT/s", output)
                speed = f"{speed_match.group(1)}MHz" if speed_match else None

                if memory_type:
                    return {
                        "type": memory_type,
                        "speed": speed,
                        "detection_method": "dmidecode",
                    }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

        # Fallback: basic detection from /proc/meminfo
        # Note: Could parse meminfo here for more detailed RAM info if needed

        return {"type": "RAM", "speed": None, "detection_method": "proc"}
    except OSError:
        return {"type": "Unknown", "speed": None, "detection_method": "none"}


def detect_storage_info() -> Dict:
    """Detect primary storage type"""
    try:
        # Check if root is on NVMe
        root_device = _get_root_device()
        if not root_device:
            return {"type": "Unknown", "interface": "unknown"}

        # Check for NVMe
        if "nvme" in root_device:
            return {"type": "NVMe SSD", "interface": "nvme"}

        # Check if it's an SSD or HDD
        device_name = root_device.replace("/dev/", "").rstrip("0123456789")

        try:
            # Check rotational flag
            with open(f"/sys/block/{device_name}/queue/rotational") as f:
                rotational = f.read().strip() == "1"

            if rotational:
                return {"type": "HDD", "interface": "sata"}
            else:
                return {"type": "SSD", "interface": "sata"}
        except OSError:
            pass

        return {"type": "Unknown", "interface": "unknown"}
    except Exception:
        return {"type": "Unknown", "interface": "unknown"}


def _get_root_device() -> Optional[str]:
    """Get the device that root filesystem is mounted on"""
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "SOURCE", "/"], capture_output=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def detect_gpu_models() -> Dict:
    """Detect GPU models and types"""
    gpus = []

    # Try NVIDIA first
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split(",")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    memory = parts[1].strip()
                    gpus.append({"name": name, "memory": memory, "vendor": "NVIDIA"})
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try AMD
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname", "--showmeminfo", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)

        for gpu_id, gpu_info in data.items():
            if "Card series" in gpu_info and "Memory" in gpu_info:
                name = gpu_info["Card series"]
                memory_info = gpu_info["Memory"]
                total_memory = memory_info.get("total_memory", "Unknown")

                gpus.append({"name": name, "memory": total_memory, "vendor": "AMD"})
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        pass

    return {"available": len(gpus) > 0, "gpus": gpus}


def get_hardware_info() -> Dict:
    """Get comprehensive hardware information"""
    return {
        "cpu": detect_cpu_info(),
        "memory": detect_memory_info(),
        "storage": detect_storage_info(),
        "gpu": detect_gpu_models(),
    }
