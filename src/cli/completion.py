#!/usr/bin/env python3

import click
from click.shell_completion import CompletionItem

from core.config import load_config


class CompleteServiceNames(click.ParamType):
    name = "service_name"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for service names."""
        try:
            config = load_config()
            service_names = list(config["services"].keys())
            return [
                CompletionItem(service_name)
                for service_name in service_names
                if service_name.startswith(incomplete)
            ]
        except Exception:
            return []


class CompletePortRanges(click.ParamType):
    name = "port_range"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for port ranges."""
        try:
            config = load_config()
            ranges = list(config["port_ranges"].keys())
            return [
                CompletionItem(range_name)
                for range_name in ranges
                if range_name.startswith(incomplete)
            ]
        except Exception:
            return []


class CompleteCommands(click.ParamType):
    name = "command"

    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for panel commands - dynamically discovered."""
        try:
            from pathlib import Path

            from .discovery import discover_commands

            # Get commands directory path
            commands_dir = Path(__file__).parent / "commands"
            command_groups = discover_commands(commands_dir)

            # Extract all command names from discovered commands
            commands = []
            for group_commands in command_groups.values():
                commands.extend([cmd[0] for cmd in group_commands])

            return [
                CompletionItem(cmd) for cmd in commands if cmd.startswith(incomplete)
            ]
        except Exception:
            # Fallback to empty list if discovery fails
            return []


# Create instances for use in commands
SERVICE_NAME = CompleteServiceNames()
PORT_RANGE = CompletePortRanges()
COMMAND_NAME = CompleteCommands()

# Simple types from original CLI
SMART_PORT = click.INT
