#!/usr/bin/env python3

import click
import subprocess
from pathlib import Path
from tabulate import tabulate

from control_panel.utils.config import load_config, save_config
from control_panel.utils.service import register_service, unregister_service, get_service_status, control_service

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

SERVICE_NAME = CompleteServices()

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Control Panel - Manage your services and ports"""
    pass

@cli.command()
@click.option('--name', required=True, help='Service name')
@click.option('--command', required=True, help='Command to start the service')
@click.option('--port', type=int, help='Port to run on (optional, will auto-assign if not specified)')
@click.option('--dir', default='', help='Working directory (defaults to home directory)')
@click.option('--range', 'range_name', default='default', help='Port range to use for auto-assignment')
@click.option('--env', multiple=True, help='Environment variables in KEY=VALUE format')
def register(name, command, port, dir, range_name, env):
    """Register a new service"""
    success, result = register_service(name, command, port, dir, range_name, env)
    
    if not success:
        click.echo(f"Error: {result}")
        return
    
    click.echo(f"Service '{name}' registered on port {result}")
    click.echo(f"To start: panel start {name}")
    click.echo(f"To enable at startup: panel enable {name}")

@cli.command()
def list():
    """List all registered services"""
    config = load_config()
    
    if not config["services"]:
        click.echo("No services registered")
        return
    
    # Get status for each service
    rows = []
    for name, service in config["services"].items():
        try:
            status, enabled = get_service_status(name)
            enabled_mark = "✓" if enabled else ""
            
            rows.append([name, service["port"], status, enabled_mark, service["command"]])
        except Exception as e:
            # Handle errors gracefully
            rows.append([name, service["port"], "error", "", service["command"]])
    
    # Sort by name
    rows.sort(key=lambda x: x[0])
    
    # Print table
    headers = ["Service", "Port", "Status", "Auto-start", "Command"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def start(name):
    """Start a service"""
    success, error = control_service(name, "start")
    if not success:
        click.echo(f"Error: {error}")
        return
    
    click.echo(f"Service '{name}' started")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def stop(name):
    """Stop a service"""
    success, error = control_service(name, "stop")
    if not success:
        click.echo(f"Error: {error}")
        return
    
    click.echo(f"Service '{name}' stopped")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def restart(name):
    """Restart a service"""
    success, error = control_service(name, "restart")
    if not success:
        click.echo(f"Error: {error}")
        return
    
    click.echo(f"Service '{name}' restarted")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def enable(name):
    """Enable a service to start automatically"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = True
    save_config(config)
    
    click.echo(f"Service '{name}' enabled to start automatically")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def disable(name):
    """Disable a service from starting automatically"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"])
    
    # Update config
    config["services"][name]["enabled"] = False
    save_config(config)
    
    click.echo(f"Service '{name}' disabled from starting automatically")

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def logs(name):
    """View logs for a service"""
    config = load_config()
    
    if name not in config["services"]:
        click.echo(f"Error: Service '{name}' not found")
        return
    
    # This will follow logs until Ctrl+C is pressed
    try:
        subprocess.run(["journalctl", "--user", "-f", "-u", f"control-panel@{name}.service"])
    except KeyboardInterrupt:
        pass

@cli.command()
@click.argument('name', type=SERVICE_NAME)
def unregister(name):
    """Unregister a service"""
    success, error = unregister_service(name)
    if not success:
        click.echo(f"Error: {error}")
        return
    
    click.echo(f"Service '{name}' unregistered")

@cli.command()
@click.argument('range_name')
@click.argument('start', type=int)
@click.argument('end', type=int)
def add_range(range_name, start, end):
    """Add a new port range"""
    if end <= start:
        click.echo("Error: End port must be greater than start port")
        return
    
    config = load_config()
    config["port_ranges"][range_name] = {"start": start, "end": end}
    save_config(config)
    
    click.echo(f"Port range '{range_name}' added: {start}-{end}")

@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=9000, type=int, help='Port to listen on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
def web(host, port, no_browser):
    """Start the web UI for Control Panel"""
    from control_panel.web_ui import start_web_ui
    
    click.echo(f"Starting Control Panel web UI at http://{host}:{port}")
    start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)

@cli.command()
@click.option("--shell", type=click.Choice(["bash", "zsh", "fish"]), help="Shell type")
def install_completion(shell):
    """Install shell completion for the panel command"""
    if not shell:
        shell = click.prompt(
            "Which shell do you use?",
            type=click.Choice(["bash", "zsh", "fish"])
        )
    
    if shell == "bash":
        path = Path.home() / ".bash_completion"
        script = f"""
# Control Panel completion
_panel_completion() {{
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${{COMP_WORDS[*]}}" COMP_CWORD=$COMP_CWORD _PANEL_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"
        if [[ $type == 'file' || $type == 'dir' ]]; then
            COMPREPLY+=($value)
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done
    return 0
}}

complete -o nosort -F _panel_completion panel
"""
    elif shell == "zsh":
        path = Path.home() / ".zshrc"
        script = """
# Control Panel completion
eval "$(_PANEL_COMPLETE=zsh_source panel)"
"""
    elif shell == "fish":
        path = Path.home() / ".config" / "fish" / "completions" / "panel.fish"
        path.parent.mkdir(parents=True, exist_ok=True)
        script = """
# Control Panel completion
eval (env _PANEL_COMPLETE=fish_source panel)
"""
    
    if path.exists():
        with open(path, "r") as f:
            content = f.read()
        
        if "Control Panel completion" in content:
            click.echo(f"Completion for {shell} already installed.")
            return
        
        with open(path, "a") as f:
            f.write(f"\n{script}\n")
    else:
        with open(path, "w") as f:
            f.write(script)
    
    click.echo(f"Shell completion for {shell} has been installed.")
    click.echo(f"Please restart your shell or run 'source {path}' to enable completion.")

def main():
    """Entry point for the CLI"""
    cli()

if __name__ == '__main__':
    main()
