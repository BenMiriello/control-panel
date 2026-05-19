#!/usr/bin/env python3

import os
from pathlib import Path

# Import from core business logic
# Import completion types from CLI module
from .discovery import GroupedMultiCommand

# Helper functions for multi-shell completion support


def _get_config_file(shell):
    """Get the config file path for a given shell"""
    if shell == "bash":
        return os.path.expanduser("~/.bashrc")
    elif shell == "zsh":
        return os.path.expanduser("~/.zshrc")
    elif shell == "fish":
        return os.path.expanduser("~/.config/fish/config.fish")
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def _get_completion_file(shell):
    """Get completion file path for shells that use separate files"""
    if shell == "zsh":
        return os.path.expanduser("~/.panel_completion.zsh")
    return None


# Use the new grouped multi-command for automatic discovery
cli = GroupedMultiCommand(
    commands_dir=Path(__file__).parent / "commands",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Control Panel - Manage your services and ports",
)


# Add commands from control.py


# Commands are now automatically discovered from the commands/ directory
# No manual registration needed!

# Export the CLI function as main for entry_point in setup.py
main = cli

if __name__ == "__main__":
    cli()
