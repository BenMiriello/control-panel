#!/usr/bin/env python3

import re
import subprocess

from ..config import load_config, save_config
from .lifecycle import control_service, get_service_status


def rename_service(old_name, new_name):
    """Rename a service and update all related configurations"""
    # Validate new name
    if not re.match(r"^[a-zA-Z0-9_-]+$", new_name):
        return (
            False,
            "Service name can only contain letters, numbers, hyphens, and underscores",
        )

    if len(new_name) > 50:
        return False, "Service name must be 50 characters or less"

    if new_name == old_name:
        return True, "No change needed"

    # Load config
    config = load_config()

    if old_name not in config["services"]:
        return False, f"Service '{old_name}' not found"

    if new_name in config["services"]:
        return False, f"Service '{new_name}' already exists"

    try:
        # Get current service status
        status, enabled = get_service_status(old_name)

        # Stop the old service if running
        if status == "active":
            success, error = control_service(old_name, "stop")
            if not success:
                return False, f"Failed to stop service: {error}"

        # Disable the old service
        if enabled:
            subprocess.run(
                ["systemctl", "--user", "disable", f"control-panel@{old_name}.service"],
                check=False,
            )

        # Copy service configuration to new name
        config["services"][new_name] = config["services"][old_name].copy()

        # Remove old service from config
        del config["services"][old_name]

        # Save updated config
        save_config(config)

        # If the service was enabled, enable the new one
        if enabled:
            subprocess.run(
                ["systemctl", "--user", "enable", f"control-panel@{new_name}.service"],
                check=False,
            )

        # If the service was running, start the new one
        if status == "active":
            success, error = control_service(new_name, "start")
            if not success:
                # Rollback on failure
                config["services"][old_name] = config["services"][new_name].copy()
                del config["services"][new_name]
                save_config(config)
                return False, f"Failed to start renamed service: {error}"

        return True, f"Service renamed from '{old_name}' to '{new_name}'"

    except Exception as e:
        # Rollback on any error
        if new_name in config["services"]:
            del config["services"][new_name]
        save_config(config)
        return False, f"Error renaming service: {str(e)}"
