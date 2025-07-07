#!/usr/bin/env python3

import subprocess

from flask import jsonify, redirect, render_template, request, url_for

from core.config import load_config, save_config
from core.service import (
    control_service,
    detect_service_port,
    get_service_port_status,
    register_service,
    rename_service,
    unregister_service,
)
from core.services.ports import detect_service_ports, set_port_management_mode


def register_service_routes(app):
    """Register service management routes with the Flask app"""

    @app.route("/services/control/<name>/<action>")
    def service_control(name, action):
        if action in ["start", "stop", "restart"]:
            success, error = control_service(name, action)
            if not success:
                return redirect(
                    url_for(
                        "index",
                        action=action,
                        service=name,
                        status="error",
                        message=error,
                    )
                )
        elif action == "enable":
            config = load_config()
            if name not in config["services"]:
                return redirect(
                    url_for(
                        "index",
                        action=action,
                        service=name,
                        status="error",
                        message=f"Service '{name}' not found",
                    )
                )

            result = subprocess.run(
                ["systemctl", "--user", "enable", f"control-panel@{name}.service"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return redirect(
                    url_for(
                        "index",
                        action=action,
                        service=name,
                        status="error",
                        message=result.stderr,
                    )
                )

            config["services"][name]["enabled"] = True
            save_config(config)
        elif action == "disable":
            config = load_config()
            if name not in config["services"]:
                return redirect(
                    url_for(
                        "index",
                        action=action,
                        service=name,
                        status="error",
                        message=f"Service '{name}' not found",
                    )
                )

            result = subprocess.run(
                ["systemctl", "--user", "disable", f"control-panel@{name}.service"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return redirect(
                    url_for(
                        "index",
                        action=action,
                        service=name,
                        status="error",
                        message=result.stderr,
                    )
                )

            config["services"][name]["enabled"] = False
            save_config(config)
        else:
            return redirect(
                url_for(
                    "index",
                    action=action,
                    service=name,
                    status="error",
                    message=f"Unknown action: {action}",
                )
            )

        return redirect(url_for("index", action=action, service=name, status="success"))

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
                    return redirect(
                        url_for(
                            "index",
                            action="register",
                            service=name or "unknown",
                            status="error",
                            message="Port must be a number",
                        )
                    )
            else:
                port = None

            success, result = register_service(
                name, command, port, directory, range_name, env_vars
            )

            if not success:
                return redirect(
                    url_for(
                        "index",
                        action="register",
                        service=name,
                        status="error",
                        message=result,
                    )
                )

            return redirect(
                url_for("index", action="register", service=name, status="success")
            )

        # GET request - show form
        config = load_config()
        port_ranges = config.get("port_ranges", {})
        return render_template("add_service.html", port_ranges=port_ranges)

    @app.route("/services/delete/<name>")
    def delete_service(name):
        success, error = unregister_service(name)
        if not success:
            return redirect(
                url_for(
                    "index",
                    action="delete",
                    service=name,
                    status="error",
                    message=error,
                )
            )

        return redirect(
            url_for("index", action="delete", service=name, status="success")
        )

    @app.route("/services/edit/<name>", methods=["GET", "POST"])
    def edit_service(name):
        config = load_config()

        if name not in config["services"]:
            return redirect(
                url_for(
                    "index",
                    action="edit",
                    service=name,
                    status="error",
                    message=f"Service '{name}' not found",
                )
            )

        service = config["services"][name]

        if request.method == "POST":
            # Get form data
            new_name = request.form.get("name", "").strip()
            command = request.form.get("command", "").strip()
            port = request.form.get("port", "").strip()
            working_dir = request.form.get("path", "").strip()
            env_vars = request.form.get("env_vars", "").strip()
            port_mode = request.form.get("port_mode", "managed")

            try:
                # Handle service name change first if needed
                if new_name and new_name != name:
                    success, message = rename_service(name, new_name)
                    if not success:
                        return redirect(
                            url_for(
                                "index",
                                action="edit",
                                service=name,
                                status="error",
                                message=message,
                            )
                        )
                    # Update name for subsequent operations
                    name = new_name
                    # Reload config after rename
                    config = load_config()
                    service = config["services"][name]

                # Update command if provided
                if command:
                    service["command"] = command

                # Update working directory if provided
                if working_dir:
                    service["working_dir"] = working_dir

                # Handle port mode setting - ALWAYS set the mode regardless of port value
                if port_mode == "managed":
                    if port and port.isdigit():
                        port_num = int(port)
                        success, message = set_port_management_mode(
                            name, "managed", port_num
                        )
                    else:
                        success, message = set_port_management_mode(name, "managed")

                    if not success:
                        return redirect(
                            url_for(
                                "index",
                                action="edit",
                                service=name,
                                status="error",
                                message=message,
                            )
                        )
                elif port_mode == "auto_detect":
                    # If switching to auto-detect, try to detect port and use it as managed port
                    detected_port = detect_service_port(name)
                    if detected_port:
                        success, message = set_port_management_mode(name, "auto_detect")
                        if success:
                            # Update the managed port to the detected value
                            config = load_config()
                            config["services"][name]["managed_port"] = detected_port
                            save_config(config)
                        else:
                            return redirect(
                                url_for(
                                    "index",
                                    action="edit",
                                    service=name,
                                    status="error",
                                    message=message,
                                )
                            )
                    else:
                        success, message = set_port_management_mode(name, "auto_detect")
                        if not success:
                            return redirect(
                                url_for(
                                    "index",
                                    action="edit",
                                    service=name,
                                    status="error",
                                    message=message,
                                )
                            )

                # Initialize environment variables if not present
                if "env" not in service:
                    service["env"] = {}

                # Process environment variables
                if env_vars:
                    # Clear existing env vars (except PORT)
                    current_port = service["env"].get("PORT")
                    service["env"] = {}
                    if current_port:
                        service["env"]["PORT"] = current_port

                    # Add new env vars
                    for line in env_vars.split("\n"):
                        line = line.strip()
                        if line and "=" in line:
                            key, value = line.split("=", 1)
                            service["env"][key.strip()] = value.strip()

                # Always update PORT in environment
                if "port" in service:
                    service["env"]["PORT"] = str(service["port"])

                # Save updated configuration
                save_config(config)

                return redirect(
                    url_for("index", action="edit", service=name, status="success")
                )

            except Exception as e:
                return redirect(
                    url_for(
                        "index",
                        action="edit",
                        service=name,
                        status="error",
                        message=f"Failed to update service: {str(e)}",
                    )
                )

        # GET request - show edit form
        # Add service name and port status to the service dict for template compatibility
        service_with_name = service.copy()
        service_with_name["name"] = name

        # Get port status information
        port_status = get_service_port_status(name)
        service_with_name["port_status"] = port_status

        return render_template("edit_service.html", service=service_with_name)

    @app.route("/api/services/<name>/detect-port")
    def api_detect_port(name):
        """API endpoint to detect port for a service"""
        try:
            detected_port = detect_service_port(name)
            if detected_port:
                return jsonify({"success": True, "port": detected_port})
            else:
                return jsonify({"success": False, "error": "No port detected"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/api/services/<name>/port-details")
    def api_port_details(name):
        """API endpoint to get detailed port information for a service"""
        try:
            detection_result = detect_service_ports(name)
            detected_ports = detection_result.get("detected_ports", {})
            main_pid = detection_result.get("main_pid")
            container_info = detection_result.get("container_info")

            # Generate HTML for port details
            html = _generate_port_details_html(detected_ports, main_pid, container_info)
            return jsonify({"success": True, "html": html})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})


def _generate_port_details_html(detected_ports, main_pid, container_info):
    """Generate HTML for detailed port information"""
    if not detected_ports and not container_info:
        return '<span class="text-muted">No port information available</span>'

    html_parts = []

    # Container information
    if container_info:
        runtime = container_info.get("runtime", "unknown")
        container_id = container_info.get("container_id", "unknown")
        container_name = container_info.get("container_name", "unknown")
        network_mode = container_info.get("network_mode", "unknown")

        html_parts.append('<div class="mb-2">')
        html_parts.append(f"<strong>Container:</strong> {runtime.title()}<br>")
        html_parts.append(f"<strong>Name:</strong> {container_name}<br>")
        html_parts.append(
            f"<strong>ID:</strong> <code>{container_id[:12]}...</code><br>"
        )
        html_parts.append(f"<strong>Network:</strong> {network_mode}")
        html_parts.append("</div>")

        # Port mappings
        port_mappings = container_info.get("port_mappings", {})
        if port_mappings:
            html_parts.append('<div class="mb-2">')
            html_parts.append("<strong>Port Mappings:</strong><br>")
            for internal_port, external_port in port_mappings.items():
                if network_mode == "host":
                    html_parts.append(
                        f"<small>• {internal_port} → {external_port} (host network)</small><br>"
                    )
                else:
                    html_parts.append(
                        f"<small>• Container {internal_port} → Host {external_port}</small><br>"
                    )
            html_parts.append("</div>")

    # Process information
    if detected_ports:
        html_parts.append('<div class="mb-2">')
        html_parts.append("<strong>Process Details:</strong><br>")

        if main_pid and main_pid in detected_ports:
            port = detected_ports[main_pid]
            html_parts.append(
                f"<small>• Main Process (PID {main_pid}) → Port {port}</small><br>"
            )

            # Child processes
            child_pids = [pid for pid in detected_ports.keys() if pid != main_pid]
            for pid in child_pids:
                port = detected_ports[pid]
                html_parts.append(
                    f"<small>• Child Process (PID {pid}) → Port {port}</small><br>"
                )
        else:
            # No main PID or main PID doesn't have port
            for pid, port in detected_ports.items():
                html_parts.append(
                    f"<small>• Process (PID {pid}) → Port {port}</small><br>"
                )
        html_parts.append("</div>")

    # Port selection analysis
    if detected_ports or container_info:
        html_parts.append("<div>")
        html_parts.append("<strong>Port Selection:</strong><br>")

        if container_info:
            external_ports = container_info.get("external_ports", [])
            if external_ports:
                primary_port = external_ports[0]
                html_parts.append(
                    f"<small>Primary: {primary_port} (first external port)</small>"
                )
            else:
                html_parts.append("<small>No external ports available</small>")
        else:
            all_ports = list(detected_ports.values())
            if main_pid and main_pid in detected_ports:
                main_port = detected_ports[main_pid]
                html_parts.append(
                    f"<small>Primary: {main_port} (SystemD main process)</small>"
                )
            elif all_ports:
                # Apply simple web heuristics
                web_ports = [p for p in all_ports if _is_web_port_simple(p)]
                if web_ports:
                    primary = min(web_ports)
                    html_parts.append(
                        f"<small>Primary: {primary} (web port heuristic)</small>"
                    )
                else:
                    primary = min(all_ports)
                    html_parts.append(
                        f"<small>Primary: {primary} (lowest port)</small>"
                    )
        html_parts.append("</div>")

    return "".join(html_parts)


def _is_web_port_simple(port):
    """Simple web port detection for HTML generation"""
    web_ranges = [
        (80, 80),
        (443, 443),  # Standard HTTP/HTTPS
        (3000, 3010),  # Development servers
        (5000, 5010),  # Flask, etc.
        (8000, 8090),  # Django, web servers
        (11430, 11440),  # Ollama range
    ]

    return any(start <= port <= end for start, end in web_ranges)
