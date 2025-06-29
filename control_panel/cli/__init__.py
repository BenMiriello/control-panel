#!/usr/bin/env python3

import click

# Import all command modules
from . import service_commands, management_commands, config_commands, system_commands

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass

# Register service lifecycle commands
cli.add_command(service_commands.start)
cli.add_command(service_commands.stop)
cli.add_command(service_commands.restart)
cli.add_command(service_commands.enable)
cli.add_command(service_commands.disable)
cli.add_command(service_commands.auto)

# Register service management commands
cli.add_command(management_commands.register)
cli.add_command(management_commands.unregister)
cli.add_command(management_commands.list)
cli.add_command(management_commands.logs)
cli.add_command(management_commands.edit)

# Register configuration commands
cli.add_command(config_commands.add_range)
cli.add_command(config_commands.backup)
cli.add_command(config_commands.restore)
cli.add_command(config_commands.import_config)

# Register system commands
cli.add_command(system_commands.web)
cli.add_command(system_commands.kill_port)
cli.add_command(system_commands.completion)
cli.add_command(system_commands.uninstall)

# Export the CLI function as main for entry_point in setup.py
main = cli