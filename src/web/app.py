#!/usr/bin/env python3

from pathlib import Path
import threading
import time
import webbrowser

import click
from flask import Flask

# Import route modules
from .routes.api import register_api_routes
from .routes.pages import register_page_routes
from .routes.services import register_service_routes


def create_app():
    """Create and configure the Flask app"""
    # In the new src/ structure, templates and static are directly in web/
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__, template_folder=str(template_dir), static_folder=str(static_dir)
    )

    # Register route modules
    register_api_routes(app)
    register_page_routes(app)
    register_service_routes(app)

    return app


app = create_app()


def start_web_ui(host="0.0.0.0", port=9000, debug=False, open_browser=True):
    """Start the web UI"""
    if open_browser:
        # Open browser in a separate thread after a delay
        def open_browser_delayed():
            time.sleep(1)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser_delayed).start()

    print(f"Starting Control Panel web UI at http://{host}:{port}")
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    app.run(host=host, port=port, debug=debug)


@click.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=9000, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
def main(host, port, no_browser):
    """Start the web UI for Control Panel"""
    start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)


if __name__ == "__main__":
    main()
