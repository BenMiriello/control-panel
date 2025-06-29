#!/usr/bin/env python3

import os
import click
import subprocess
import sys
import json
import webbrowser
from pathlib import Path
from tabulate import tabulate

# Import from package-relative paths
try:
    from control_panel.utils.config import load_config, save_config, CONFIG_DIR, CONFIG_FILE
    from control_panel.utils.service import register_service, unregister_service, get_service_status, control_service, detect_service_port
    from control_panel.utils.node_helper import kill_process_by_port, get_node_service_command
    PACKAGE_MODE = True
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import load_config, save_config, CONFIG_DIR, CONFIG_FILE
    from utils.service import register_service, unregister_service, get_service_status, control_service, detect_service_port
    from utils.node_helper import kill_process_by_port, get_node_service_command
    PACKAGE_MODE = False

def get_service_names():
    """Get a list of all registered service names"""
    config = load_config()
    return list(config["services"].keys())

class CompleteServices(click.ParamType):
    name = "service"
    
    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for services that match the incomplete string."""
        service_names = get_service_names()
        return [click.CompletionItem(name) for name in service_names if name.startswith(incomplete)]

class CompleteCommands(click.ParamType):
    name = "command"
    
    def shell_complete(self, ctx, param, incomplete):
        """Return completion suggestions for commands."""
        commands = [
            'register', 'list', 'start', 'stop', 'restart', 
            'auto', 'disable', 'logs', 'unregister', 'edit',
            'add_range', 'web', 'completion', 'backup',
            'restore', 'update', 'import_config', 'uninstall'
        ]
        return [click.CompletionItem(cmd) for cmd in commands if cmd.startswith(incomplete)]

SERVICE_NAME = CompleteServices()
COMMAND_NAME = CompleteCommands()

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass

# Service management commands moved to cli/management_commands.py

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

# logs and unregister commands moved to cli/management_commands.py

# System commands moved to cli/system_commands.py

# Export the CLI function as main for entry_point in setup.py
main = cli

if __name__ == '__main__':
    cli()
