#!/usr/bin/env python3

import click

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass

# Import all command modules
try:
    from control_panel.cli.service_commands import start, stop, restart, enable, disable, auto
    from control_panel.cli.management_commands import register, unregister, list, logs, edit
    from control_panel.cli.config_commands import add_range, backup, restore, import_config
    from control_panel.cli.system_commands import web, kill_port, completion, uninstall
except ImportError:
    from cli.service_commands import start, stop, restart, enable, disable, auto
    from cli.management_commands import register, unregister, list, logs, edit
    from cli.config_commands import add_range, backup, restore, import_config
    from cli.system_commands import web, kill_port, completion, uninstall

# Register service lifecycle commands
cli.add_command(start)
cli.add_command(stop)
cli.add_command(restart)
cli.add_command(enable)
cli.add_command(disable)
cli.add_command(auto)

# Register service management commands
cli.add_command(register)
cli.add_command(unregister)
cli.add_command(list)
cli.add_command(logs)
cli.add_command(edit)

# Register configuration commands
cli.add_command(add_range)
cli.add_command(backup)
cli.add_command(restore)
cli.add_command(import_config)

# Register system commands
cli.add_command(web)
cli.add_command(kill_port)
cli.add_command(completion)
cli.add_command(uninstall)

# Export the CLI function as main for entry_point in setup.py
main = cli

if __name__ == '__main__':
    cli()
