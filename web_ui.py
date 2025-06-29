#!/usr/bin/env python3

from pathlib import Path
import subprocess
import time
import webbrowser

import click
from flask import Flask, jsonify, redirect, render_template, request, url_for

from utils.config import load_config, save_config
from utils.service import (
    control_service,
    get_service_status,
    register_service,
    unregister_service,
)
from utils.system_metrics import get_all_metrics

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates" / "web"),
    static_folder=str(Path(__file__).resolve().parent / "static"),
)


@app.route("/")
def index():
    config = load_config()
    services = []

    for name, service in config["services"].items():
        status, enabled = get_service_status(name)
        services.append(
            {
                "name": name,
                "port": service["port"],
                "command": service["command"],
                "status": status,
                "enabled": enabled,
            }
        )

    # Sort by name
    services.sort(key=lambda x: x["name"])

    # Get port ranges
    port_ranges = config.get("port_ranges", {})

    return render_template("index.html", services=services, port_ranges=port_ranges)


@app.route("/api/metrics")
def get_metrics():
    """API endpoint to get current system metrics"""
    return jsonify(get_all_metrics())


@app.route("/services/control/<name>/<action>")
def service_control(name, action):
    if action in ["start", "stop", "restart"]:
        success, error = control_service(name, action)
        if not success:
            return jsonify({"status": "error", "message": error})
    elif action == "enable":
        config = load_config()
        if name not in config["services"]:
            return jsonify(
                {"status": "error", "message": f"Service '{name}' not found"}
            )

        subprocess.run(
            ["systemctl", "--user", "enable", f"control-panel@{name}.service"]
        )
        config["services"][name]["enabled"] = True
        save_config(config)
    elif action == "disable":
        config = load_config()
        if name not in config["services"]:
            return jsonify(
                {"status": "error", "message": f"Service '{name}' not found"}
            )

        subprocess.run(
            ["systemctl", "--user", "disable", f"control-panel@{name}.service"]
        )
        config["services"][name]["enabled"] = False
        save_config(config)
    else:
        return jsonify({"status": "error", "message": f"Unknown action: {action}"})

    return redirect(url_for("index"))


@app.route("/services/add", methods=["GET", "POST"])
def add_service():
    if request.method == "POST":
        name = request.form.get("name")
        command = request.form.get("command")
        port = request.form.get("port")
        directory = request.form.get("directory", "")
        range_name = request.form.get("range", "default")
        env_vars = request.form.get("env_vars", "").splitlines()

        if port:
            try:
                port = int(port)
            except ValueError:
                return jsonify({"status": "error", "message": "Port must be a number"})
        else:
            port = None

        success, result = register_service(
            name, command, port, directory, range_name, env_vars
        )

        if not success:
            return jsonify({"status": "error", "message": result})

        return redirect(url_for("index"))

    # GET request - show form
    config = load_config()
    port_ranges = config.get("port_ranges", {})
    return render_template("add_service.html", port_ranges=port_ranges)


@app.route("/services/delete/<name>")
def delete_service(name):
    success, error = unregister_service(name)
    if not success:
        return jsonify({"status": "error", "message": error})

    return redirect(url_for("index"))


@app.route("/ranges/add", methods=["GET", "POST"])
def add_range():
    if request.method == "POST":
        range_name = request.form.get("name")
        start = request.form.get("start")
        end = request.form.get("end")

        try:
            start = int(start)
            end = int(end)
        except ValueError:
            return jsonify(
                {"status": "error", "message": "Start and end must be numbers"}
            )

        if end <= start:
            return jsonify(
                {
                    "status": "error",
                    "message": "End port must be greater than start port",
                }
            )

        config = load_config()
        config["port_ranges"][range_name] = {"start": start, "end": end}
        save_config(config)

        return redirect(url_for("index"))

    # GET request - show form
    return render_template("add_range.html")


@app.route("/logs/<name>")
def view_logs(name):
    config = load_config()

    if name not in config["services"]:
        return jsonify({"status": "error", "message": f"Service '{name}' not found"})

    # Get recent logs
    result = subprocess.run(
        ["journalctl", "--user", "-n", "100", "-u", f"control-panel@{name}.service"],
        capture_output=True,
        text=True,
    )

    logs = result.stdout

    return render_template("logs.html", name=name, logs=logs)


def start_web_ui(host="127.0.0.1", port=9000, debug=False, open_browser=True):
    """Start the web UI"""
    if open_browser:
        # Open browser in a separate thread after a delay
        def open_browser_delayed():
            time.sleep(1)
            webbrowser.open(f"http://{host}:{port}")

        import threading

        threading.Thread(target=open_browser_delayed).start()

    app.run(host=host, port=port, debug=debug)


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=9000, type=int, help="Port to listen on")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
def main(host, port, no_browser):
    """Start the web UI for Control Panel"""
    click.echo(f"Starting Control Panel web UI at http://{host}:{port}")
    start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)


if __name__ == "__main__":
    main()
