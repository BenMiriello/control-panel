#!/usr/bin/env python3

import importlib
from pathlib import Path

import click


def auto_register_commands(cli_group, package_name="cli.commands"):
    """Automatically discover and register command modules"""

    # Get the commands directory
    commands_dir = Path(__file__).parent / "commands"

    if not commands_dir.exists():
        return []

    registered_commands = []

    # Scan for command modules
    for cmd_file in commands_dir.glob("*_commands.py"):
        if cmd_file.stem == "__init__":
            continue

        try:
            # Import the module
            module_name = f"{package_name}.{cmd_file.stem}"
            module = importlib.import_module(module_name)

            # Find all click.Command objects in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, click.Command):
                    # Register the command
                    cli_group.add_command(attr)
                    registered_commands.append(attr.name)

        except ImportError as e:
            # Skip modules that can't be imported
            print(f"Warning: Could not import {module_name}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error processing {cmd_file}: {e}")
            continue

    return registered_commands


def generate_dynamic_completion_script(cli_group, shell="zsh"):
    """Generate completion script dynamically from registered commands"""

    # Get all registered commands
    commands = cli_group.commands

    # Commands that need service name completion
    service_commands = []
    for cmd_name, cmd in commands.items():
        # Check if the command has a SERVICE_NAME parameter
        for param in cmd.params:
            if hasattr(param, "type") and hasattr(param.type, "name"):
                if param.type.name == "service_name":
                    service_commands.append(cmd_name)
                    break

    if shell == "zsh":
        return _generate_zsh_completion(commands, service_commands)
    elif shell == "bash":
        return _generate_bash_completion(commands, service_commands)
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def _generate_zsh_completion(commands, service_commands):
    """Generate zsh completion script"""

    # Build command list dynamically
    cmd_list = []
    for cmd_name, cmd in commands.items():
        description = cmd.help or f"{cmd_name.title()} command"
        # Clean up description for shell
        description = description.split("\n")[0]  # First line only
        description = description.replace(
            "'", ""
        )  # Remove quotes entirely to avoid escaping issues
        cmd_list.append(f"'{cmd_name}:{description}'")

    commands_section = "\n                ".join(cmd_list)
    service_commands_pattern = "|".join(service_commands)

    return f"""# Panel completion for zsh
_panel_completion() {{
    local context state line

    _arguments -C \\
        '1: :->commands' \\
        '*: :->args' && return 0

    case $state in
        commands)
            local commands=(
                {commands_section}
            )
            _describe -t commands 'panel commands' commands
            ;;
        args)
            case $words[2] in
                {service_commands_pattern})
                    # Get service list directly
                    local services=(${{(f)"$(python3 -c "import json; f=open('$HOME/.config/control-panel/services.json'); data=json.load(f); print('\\\\n'.join(data['services'].keys()))" 2>/dev/null)"}})
                    if [[ ${{#services[@]}} -gt 0 ]]; then
                        _describe -t services 'services' services
                    fi
                    ;;
            esac
            ;;
    esac
}}

compdef _panel_completion panel
"""


def _generate_bash_completion(commands, service_commands):
    """Generate bash completion script"""

    cmd_names = " ".join(commands.keys())
    service_commands_pattern = "|".join(service_commands)

    return f"""# Panel completion for bash
_panel_completion() {{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"

    if [[ ${{COMP_CWORD}} == 1 ]]; then
        opts="{cmd_names}"
        COMPREPLY=( $(compgen -W "${{opts}}" -- ${{cur}}) )
        return 0
    fi

    case "${{prev}}" in
        {service_commands_pattern})
            # Get service names
            local services=$(python3 -c "import json; f=open('$HOME/.config/control-panel/services.json'); data=json.load(f); print(' '.join(data['services'].keys()))" 2>/dev/null)
            COMPREPLY=( $(compgen -W "${{services}}" -- ${{cur}}) )
            ;;
    esac
}}

complete -F _panel_completion panel
"""
