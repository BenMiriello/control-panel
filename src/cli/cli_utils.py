#!/usr/bin/env python3

import click

from core.config import load_config


def shorten_command(command, max_length=50):
    """Shorten command display for list view"""
    if len(command) <= max_length:
        return command

    # Cut in half and add ... in middle
    half_length = (max_length - 3) // 2  # -3 for "..."
    start = command[:half_length]
    end = command[-half_length:]
    return f"{start}...{end}"


def with_service_validation(func):
    """Decorator for commands that require valid service names"""

    def wrapper(name, *args, **kwargs):
        config = load_config()
        if name not in config["services"]:
            click.secho(f"✗ Service '{name}' not found", fg="red", bold=True)
            return
        return func(name, *args, **kwargs)

    return wrapper


def format_service_status(status):
    """Format service status with appropriate colors"""
    colors = {"active": "green", "inactive": "red", "failed": "red", "dead": "red"}
    return click.style(status, fg=colors.get(status, "white"))


def format_port_display(port_status):
    """Format port display with validation indicators"""
    primary_port = port_status.get("primary_port")
    validation = port_status.get("validation", "unknown")

    if not primary_port:
        port_display = "none"
    else:
        port_display = str(primary_port)

    # Add validation indicators
    if validation == "port_mismatch":
        port_display += "*"  # Port mismatch indicator
    elif validation == "no_port_detected":
        port_display += "?"  # No port detected indicator
    elif validation == "dynamic_port":
        port_display += "~"  # Dynamic port indicator

    return port_display
