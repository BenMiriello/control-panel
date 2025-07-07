#!/usr/bin/env python3

import importlib
from pathlib import Path

import click


class CommandGroup:
    """Represents a group of related commands"""

    def __init__(self, name, commands=None):
        self.name = name
        self.commands = commands or []


def discover_commands(commands_dir):
    """Automatically discover and import all commands from the commands directory

    Returns a dictionary mapping group names to lists of (command_name, command_obj, example)
    """
    commands_dir_path = Path(commands_dir)
    if not commands_dir_path.exists():
        return {}

    groups = {}

    # Scan all Python files in commands directory
    for cmd_file in commands_dir_path.glob("*.py"):
        if cmd_file.stem.startswith("__"):
            continue

        module_name = f"cli.commands.{cmd_file.stem}"
        try:
            module = importlib.import_module(module_name)

            # Get the group name for this module (default based on filename)
            group_name = getattr(
                module, "__group__", _default_group_name(cmd_file.stem)
            )

            if group_name not in groups:
                groups[group_name] = []

            # Find all click commands in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, click.Command):
                    # Skip hidden commands from help and completion
                    if getattr(attr, "hidden", False):
                        continue
                    # Get example usage
                    example = getattr(attr, "__example__", _default_example(attr.name))
                    groups[group_name].append((attr.name, attr, example))

        except ImportError as e:
            print(f"Warning: Could not import {module_name}: {e}")
            continue

    return groups


def _default_group_name(filename):
    """Generate default group name from filename"""
    if "status" in filename:
        return "Status & Info"
    elif "service" in filename:
        return "Service Management"
    elif "config" in filename:
        return "Configuration"
    elif "utility" in filename or "util" in filename:
        return "Utilities"
    else:
        return "Other"


def _default_example(command_name):
    """Generate default example for a command"""
    examples = {
        "start": "panel start myapp",
        "stop": "panel stop myapp",
        "restart": "panel restart myapp",
        "register": "panel register myapp",
        "unregister": "panel unregister myapp",
        "ps": "panel ps -a",
        "status": "panel status",
        "info": "panel info myapp",
        "list": "panel list",
        "web": "panel web",
        "completion": "panel completion --install",
        "backup": "panel backup",
        "restore": "panel restore file.json",
        "logs": "panel logs myapp",
        "edit": "panel edit myapp",
        "kill-port": "panel kill-port 8080",
        "open-browser": "panel open-browser myapp",
    }
    return examples.get(command_name, f"panel {command_name}")


def register_discovered_commands(cli_group, commands_dir):
    """Discover and register all commands with the CLI group"""
    command_groups = discover_commands(commands_dir)

    registered = []
    for group_name, commands in command_groups.items():
        for cmd_name, cmd_obj, example in commands:
            cli_group.add_command(cmd_obj)
            registered.append(cmd_name)

    return registered


def format_grouped_help(command_groups):
    """Format help text with grouped commands in columns"""
    if not command_groups:
        return "No commands available."

    help_lines = []

    for group_name, commands in command_groups.items():
        if not commands:
            continue

        help_lines.append(f"\n{group_name}:")

        # Calculate column widths
        max_name_width = max(len(cmd[0]) for cmd in commands) if commands else 0
        max_desc_width = (
            max(len(cmd[1].help or "") for cmd in commands) if commands else 0
        )

        # Ensure minimum widths and reasonable limits
        name_width = max(12, min(max_name_width + 2, 20))
        desc_width = max(25, min(max_desc_width + 2, 40))

        for cmd_name, cmd_obj, example in sorted(commands):
            description = (cmd_obj.help or "").split("\n")[0]  # First line only
            if len(description) > desc_width - 2:
                description = description[: desc_width - 5] + "..."

            help_lines.append(
                f"  {cmd_name:<{name_width}} {description:<{desc_width}} {example}"
            )

    return "\n".join(help_lines)


class GroupedMultiCommand(click.MultiCommand):
    """Custom MultiCommand that groups commands in help output"""

    def __init__(self, commands_dir, **kwargs):
        super().__init__(**kwargs)
        self.commands_dir = commands_dir
        self._command_groups = None

    def get_command_groups(self):
        """Get discovered command groups (cached)"""
        if self._command_groups is None:
            self._command_groups = discover_commands(self.commands_dir)
        return self._command_groups

    def list_commands(self, ctx):
        """List all available commands"""
        command_groups = self.get_command_groups()
        commands = []
        for group_commands in command_groups.values():
            commands.extend([cmd[0] for cmd in group_commands])
        return sorted(commands)

    def get_command(self, ctx, name):
        """Get a specific command by name"""
        command_groups = self.get_command_groups()
        for group_commands in command_groups.values():
            for cmd_name, cmd_obj, example in group_commands:
                if cmd_name == name:
                    return cmd_obj

        # Also check for hidden commands (not in command_groups but still executable)
        return self._get_hidden_command(name)

    def _get_hidden_command(self, name):
        """Get a hidden command by name"""
        commands_dir_path = Path(self.commands_dir)
        if not commands_dir_path.exists():
            return None

        # Scan all Python files in commands directory
        for cmd_file in commands_dir_path.glob("*.py"):
            if cmd_file.stem.startswith("__"):
                continue

            module_name = f"cli.commands.{cmd_file.stem}"
            try:
                module = importlib.import_module(module_name)

                # Find all click commands in the module, including hidden ones
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, click.Command) and attr.name == name:
                        return attr

            except ImportError:
                continue

        return None

    def format_commands(self, ctx, formatter):
        """Format commands with grouping"""
        command_groups = self.get_command_groups()
        help_text = format_grouped_help(command_groups)

        if help_text.strip():
            formatter.write_paragraph()
            formatter.write(help_text)
