#!/usr/bin/env python3

import click

# Import command modules
from . import service_commands

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass

# Add service lifecycle commands
cli.add_command(service_commands.start)
cli.add_command(service_commands.stop)
cli.add_command(service_commands.restart)
cli.add_command(service_commands.enable)
cli.add_command(service_commands.disable)
cli.add_command(service_commands.auto)

# Export the CLI function as main for entry_point in setup.py
main = cli