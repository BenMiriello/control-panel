# No changes to imports and the first part of the file

# Just update the web command
@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to (0.0.0.0 for all interfaces)')
@click.option('--port', default=9000, type=int, help='Port to listen on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.option('--background', '-b', is_flag=True, help='Run web UI in the background')
def web(host, port, no_browser, background):
    """Start the web UI for Control Panel"""
    try:
        from control_panel.web_ui import start_web_ui

        if background:
            # Register as a service and start it
            config = load_config()
            service_name = "control-panel-web"
            
            # Check if already registered
            if service_name not in config["services"]:
                # Get path to the current script
                script_path = Path(sys.executable)
                
                # Create the command to run the web UI
                command = f"{script_path} -m control_panel.web_ui --host={host} --port={port}"
                
                # Register the service
                success, result = register_service(
                    service_name, 
                    command, 
                    port, 
                    "", 
                    "default", 
                    []
                )
                
                if not success:
                    click.echo(f"Error registering web UI service: {result}")
                    return
                
                click.echo(f"Web UI registered as service '{service_name}' on port {port}")
            
            # Start the service
            success, error = control_service(service_name, "start")
            if not success:
                click.echo(f"Error: {error}")
                return
                
            click.echo(f"Web UI started in background at http://{host}:{port}")
            click.echo(f"To check status: panel list")
            click.echo(f"To stop: panel stop {service_name}")
        else:
            # Run directly in foreground
            click.echo(f"Starting Control Panel web UI at http://{host}:{port}")
            click.echo("Press Ctrl+C to stop")
            start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)
    except ImportError as e:
        click.echo(f"Error: {e}")
        click.echo("Please reinstall with compatible Flask version:")
        click.echo("  pip install 'flask>=2.0.0,<2.2.0' 'werkzeug>=2.0.0,<2.1.0'")
