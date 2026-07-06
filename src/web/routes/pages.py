#!/usr/bin/env python3

import subprocess

from flask import jsonify, redirect, render_template, request, url_for

from core.config import load_config, save_config
from core.services.listing import build_service_list


def register_page_routes(app):
    """Register page routes with the Flask app"""

    @app.route("/")
    def index():
        config = load_config()
        services = build_service_list(config)

        # Get port ranges
        port_ranges = config.get("port_ranges", {})

        return render_template("index.html", services=services, port_ranges=port_ranges)

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
            return jsonify(
                {"status": "error", "message": f"Service '{name}' not found"}
            )

        # Get recent logs
        result = subprocess.run(
            [
                "journalctl",
                "--user",
                "-n",
                "100",
                "-u",
                f"control-panel@{name}.service",
            ],
            capture_output=True,
            text=True,
        )

        logs = result.stdout

        return render_template("logs.html", name=name, logs=logs)
