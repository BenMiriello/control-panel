#!/usr/bin/env python3

import argparse
from pathlib import Path
import subprocess
import threading
import time
import webbrowser

# Import Flask app from the main web_ui module
from control_panel.web_ui import app


def start_web_ui(host="127.0.0.1", port=9000, debug=False, open_browser=True):
    """Start the web UI"""
    if open_browser:
        # Open browser in a separate thread after a delay
        def open_browser_delayed():
            time.sleep(1)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser_delayed).start()

    app.run(host=host, port=port, debug=debug)


def parse_args():
    parser = argparse.ArgumentParser(description="Control Panel Web UI")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (0.0.0.0 for all interfaces)"
    )
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open browser automatically"
    )
    return parser.parse_args()


# Create a service file for the Control Panel to start at boot
def create_control_panel_service():
    """Create a systemd service for starting the Control Panel at boot"""
    service_file = (
        Path.home() / ".config" / "systemd" / "user" / "control-panel.service"
    )
    service_dir = service_file.parent
    service_dir.mkdir(parents=True, exist_ok=True)

    # Generate service file content
    service_content = """[Unit]
Description=Control Panel Web UI
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/panel web --background
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""

    # Write service file
    with open(service_file, "w") as f:
        f.write(service_content)

    # Reload systemd and enable the service
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    subprocess.run(["systemctl", "--user", "enable", "control-panel.service"])

    return "Control Panel service installed for auto-start at system boot."


def setup_control_panel_autostart():
    """Set up the Control Panel to start automatically at system boot"""
    try:
        msg = create_control_panel_service()
        print(f"Success: {msg}")
        return True
    except Exception as e:
        print(f"Error setting up auto-start: {e}")
        return False


if __name__ == "__main__":
    args = parse_args()
    start_web_ui(
        host=args.host,
        port=args.port,
        debug=args.debug,
        open_browser=not args.no_browser,
    )
