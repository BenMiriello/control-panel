#!/usr/bin/env python3

import click

# Import from package-relative paths
try:
    from control_panel.utils.config import load_config
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import load_config

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
            'restore', 'import_config', 'uninstall', 'kill_port'
        ]
        return [click.CompletionItem(cmd) for cmd in commands if cmd.startswith(incomplete)]

# Commonly used completion instances
SERVICE_NAME = CompleteServices()
COMMAND_NAME = CompleteCommands()