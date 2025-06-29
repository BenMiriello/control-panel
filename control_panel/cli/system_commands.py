#!/usr/bin/env python3

import click
import subprocess
import threading
import webbrowser

# Import from package-relative paths
try:
    from control_panel.utils.config import load_config, save_config
    from control_panel.utils.service import register_service, control_service
    from control_panel.utils.node_helper import kill_process_by_port
    PACKAGE_MODE = True
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import load_config, save_config
    from utils.service import register_service, control_service
    from utils.node_helper import kill_process_by_port
    PACKAGE_MODE = False

@click.command()
@click.argument('port', type=int)
def kill_port(port):
    """Kill processes using a specific port"""
    success, message = kill_process_by_port(port, force=True)
    if success:
        click.echo(f"Success: {message}")
    else:
        click.echo(f"No processes found using port {port}")

@click.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=9000, type=int, help='Port to listen on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.option('--register', is_flag=True, help='Register as a service instead of running directly')
def web(host, port, no_browser, register):
    """Start the web UI"""
    # Check if the web UI is already registered as a service
    config = load_config()
    service_name = "panel-web"
    
    if register or service_name in config["services"]:
        # Register the web UI as a service if needed
        if service_name not in config["services"]:
            # Determine the correct command to run the web UI
            if PACKAGE_MODE:
                web_ui_command = f"panel-web --host {host} --port {port}"
            else:
                web_ui_command = f"python3 web_ui.py --host {host} --port {port}"
            
            # Register the service
            env_vars = [f"HOST={host}", f"PORT={port}"]
            success, result = register_service(service_name, web_ui_command, port, "", "default", env_vars)
            
            if not success:
                click.echo(f"Error registering web UI service: {result}")
                return
            
            click.echo(f"Web UI registered as service '{service_name}' on port {result}")
            
            # Enable auto-start
            config = load_config()
            config["services"][service_name]["enabled"] = True
            save_config(config)
            subprocess.run(["systemctl", "--user", "enable", f"control-panel@{service_name}.service"])
        
        # Start the service
        success, error = control_service(service_name, "start")
        if not success:
            click.echo(f"Error starting web UI service: {error}")
            click.echo(f"Check logs with: panel logs {service_name}")
            return
        
        click.echo(f"Web UI service '{service_name}' started on http://{host}:{port}")
        click.echo(f"View logs with: panel logs {service_name}")
        
        # Open browser if requested
        if not no_browser:
            webbrowser.open(f"http://localhost:{port}")
    else:
        # Run the web UI directly (legacy mode)
        click.echo("Starting Web UI directly (not as a service)")
        click.echo("To register as a service, use --register flag")
        
        # Import here to avoid circular imports
        try:
            from control_panel.web_ui import start_web_ui
        except ImportError:
            # Fallback to local import if package is not fully installed
            try:
                from web_ui import start_web_ui
            except ImportError:
                click.echo("Error: web_ui module not found!")
                return
        
        click.echo(f"Starting Control Panel web UI at http://{host}:{port}")
        start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)

@click.command()
def completion():
    """Generate shell completion script"""
    click.echo("Shell completion is automatically available when you install the package.")
    click.echo("For bash, add this to your ~/.bashrc:")
    click.echo('eval "$(_PANEL_COMPLETE=bash_source panel)"')
    click.echo("")
    click.echo("For zsh, add this to your ~/.zshrc:")
    click.echo('eval "$(_PANEL_COMPLETE=zsh_source panel)"')
    click.echo("")
    click.echo("For fish, add this to your ~/.config/fish/completions/panel.fish:")
    click.echo('eval (env _PANEL_COMPLETE=fish_source panel)')

@click.command()
@click.confirmation_option(prompt='Are you sure you want to uninstall all services?')
def uninstall():
    """Uninstall all services and remove configuration"""
    config = load_config()
    
    if not config["services"]:
        click.echo("No services to uninstall")
        return
    
    # Stop and disable all services
    for service_name in config["services"]:
        click.echo(f"Stopping and disabling service: {service_name}")
        subprocess.run(["systemctl", "--user", "stop", f"control-panel@{service_name}.service"],
                      stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "--user", "disable", f"control-panel@{service_name}.service"],
                      stderr=subprocess.DEVNULL)
    
    # Remove configuration
    from control_panel.utils.config import CONFIG_DIR
    import shutil
    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)
        click.echo(f"Removed configuration directory: {CONFIG_DIR}")
    
    click.echo("All services uninstalled and configuration removed")