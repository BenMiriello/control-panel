#!/usr/bin/env python3

import click
import subprocess
import sys
import os
import shutil
import tempfile
import json
from pathlib import Path
from tabulate import tabulate

from control_panel.utils.config import load_config, save_config, CONFIG_DIR, CONFIG_FILE
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
    try:
        from control_panel.web_ui import start_web_ui
        click.echo(f"Starting Control Panel web UI at http://{host}:{port}")
        start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)
    except ImportError as e:
        click.echo(f"Error: {e}")
        click.echo("Please reinstall with compatible Flask version:")
        click.echo("  pip install 'flask>=2.0.0,<2.2.0' 'werkzeug>=2.0.0,<2.1.0'")

@cli.command()
@click.option("--shell", type=click.Choice(["bash", "zsh", "fish"]), help="Shell type")
def completion(shell):
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

@cli.command()
@click.option('--backup/--no-backup', default=True, 
              help='Create a backup of configuration (default: Yes)')
def uninstall(backup):
    """Uninstall Control Panel but optionally preserve settings"""
    if not click.confirm("Are you sure you want to uninstall Control Panel?"):
        return
    
    click.echo("Uninstalling Control Panel...")
    
    # Create backup of config if needed
    if backup:
        backup_dir = Path.home() / ".config" / "control-panel-backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy config file
        if CONFIG_FILE.exists():
            backup_file = backup_dir / "services.json"
            shutil.copy(CONFIG_FILE, backup_file)
            click.echo(f"Configuration backed up to {backup_file}")
    
    # Stop all services
    config = load_config()
    for name in config["services"].keys():
        try:
            click.echo(f"Stopping service '{name}'...")
            subprocess.run(["systemctl", "--user", "stop", f"control-panel@{name}.service"],
                          stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"],
                          stderr=subprocess.DEVNULL)
        except Exception:
            pass
    
    # Remove systemd service template
    try:
        systemd_service = Path.home() / ".config" / "systemd" / "user" / "control-panel@.service"
        if systemd_service.exists():
            os.unlink(systemd_service)
        
        # Reload systemd configuration
        subprocess.run(["systemctl", "--user", "daemon-reload"])
    except Exception as e:
        click.echo(f"Warning: Could not remove systemd service template: {e}")
    
    # Clean up configuration directory if not backing up
    if not backup:
        if click.confirm("Do you want to remove all Control Panel configuration?"):
            try:
                if CONFIG_DIR.exists():
                    shutil.rmtree(CONFIG_DIR)
                    click.echo("Configuration directory removed.")
            except Exception as e:
                click.echo(f"Warning: Could not remove configuration directory: {e}")
    
    click.echo("Control Panel has been uninstalled.")
    
    if backup:
        click.echo("\nYour services configuration has been preserved.")
        click.echo("To restore when reinstalling, run:")
        click.echo("  panel restore")
    
    click.echo("\nYou may need to remove the package using pip or your package manager:")
    click.echo("  pip uninstall control-panel")

@cli.command()
def restore():
    """Restore configuration from a previous backup"""
    backup_dir = Path.home() / ".config" / "control-panel-backup"
    backup_file = backup_dir / "services.json"
    
    if not backup_file.exists():
        click.echo("Error: No backup configuration found.")
        return
    
    if not click.confirm("Restore configuration from backup? This will overwrite current settings."):
        return
    
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy backup to config location
    shutil.copy(backup_file, CONFIG_FILE)
    
    # Create env directory if it doesn't exist
    env_dir = CONFIG_DIR / "env"
    env_dir.mkdir(exist_ok=True)
    
    # Load the restored config
    config = load_config()
    
    # Recreate environment files
    for name, service in config["services"].items():
        env_file = env_dir / f"{name}.env"
        with open(env_file, 'w') as f:
            f.write(f"COMMAND={service['command']}\n")
            f.write(f"PORT={service['port']}\n")
            for key, value in service.get("env", {}).items():
                f.write(f"{key}={value}\n")
    
    click.echo(f"Configuration restored with {len(config['services'])} services.")
    click.echo("You may need to enable services for autostart:")
    for name in config["services"].keys():
        if config["services"][name].get("enabled", False):
            click.echo(f"  panel enable {name}")

@cli.command()
@click.option('--force', is_flag=True, help='Update even if no repository is found')
def update(force):
    """Update the Control Panel software"""
    repo_dir = Path(__file__).resolve().parent.parent
    git_dir = repo_dir / ".git"
    
    if not git_dir.exists() and not force:
        click.echo("Error: Could not find repository. Are you running from an installed version?")
        click.echo("If you want to update anyway, use --force")
        return
    
    if git_dir.exists():
        # Update repository
        click.echo("Updating from repository...")
        try:
            original_dir = os.getcwd()
            os.chdir(repo_dir)
            
            # Pull latest changes
            subprocess.run(["git", "pull"], check=True)
            
            os.chdir(original_dir)
        except Exception as e:
            click.echo(f"Error during git update: {e}")
            return
    
    # Run the install script if it exists
    install_script = repo_dir / "install.sh"
    if install_script.exists():
        click.echo("Running install script...")
        try:
            subprocess.run(["bash", str(install_script)], check=True)
        except Exception as e:
            click.echo(f"Error during installation: {e}")
            return
    else:
        # Fallback to reinstalling package
        click.echo("Reinstalling package...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repo_dir)], check=True)
        except Exception as e:
            click.echo(f"Error during package installation: {e}")
            return
    
    click.echo("Control Panel updated successfully!")

@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file for backup')
def backup(output):
    """Backup all Control Panel configuration"""
    # Default output location
    if not output:
        timestamp = subprocess.check_output(["date", "+%Y%m%d-%H%M%S"]).decode().strip()
        output = f"control-panel-backup-{timestamp}.json"
    
    # Load configuration
    config = load_config()
    
    # Write to backup file
    with open(output, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"Configuration backed up to {output}")
    click.echo(f"To restore: panel import {output}")

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--merge/--overwrite', default=True, 
              help='Merge with existing config or overwrite (default: merge)')
def import_config(input_file, merge):
    """Import configuration from a backup file"""
    # Load backup file
    with open(input_file, 'r') as f:
        imported_config = json.load(f)
    
    if merge:
        # Load current config
        current_config = load_config()
        
        # Merge services and port ranges
        for name, service in imported_config.get("services", {}).items():
            current_config["services"][name] = service
        
        for name, range_info in imported_config.get("port_ranges", {}).items():
            current_config["port_ranges"][name] = range_info
        
        # Save merged config
        save_config(current_config)
        
        # Re-create environment files
        env_dir = CONFIG_DIR / "env"
        for name, service in current_config["services"].items():
            env_file = env_dir / f"{name}.env"
            with open(env_file, 'w') as f:
                f.write(f"COMMAND={service['command']}\n")
                f.write(f"PORT={service['port']}\n")
                for key, value in service.get("env", {}).items():
                    f.write(f"{key}={value}\n")
        
        click.echo(f"Imported and merged configuration with {len(imported_config.get('services', {}))} services")
    else:
        # Save imported config directly
        save_config(imported_config)
        
        # Re-create environment files
        env_dir = CONFIG_DIR / "env"
        for name, service in imported_config.get("services", {}).items():
            env_file = env_dir / f"{name}.env"
            with open(env_file, 'w') as f:
                f.write(f"COMMAND={service['command']}\n")
                f.write(f"PORT={service['port']}\n")
                for key, value in service.get("env", {}).items():
                    f.write(f"{key}={value}\n")
        
        click.echo(f"Imported configuration with {len(imported_config.get('services', {}))} services (overwriting previous config)")

def main():
    """Entry point for the CLI"""
    cli()

if __name__ == '__main__':
    main()
