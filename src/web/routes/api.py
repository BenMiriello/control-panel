#!/usr/bin/env python3

from flask import jsonify

from core.config import load_config
from core.service import detect_service_port
from core.system_metrics import get_all_metrics


def register_api_routes(app):
    """Register API routes with the Flask app"""

    @app.route("/api/metrics")
    def get_metrics():
        """API endpoint to get current system metrics"""
        return jsonify(get_all_metrics())

    @app.route("/api/services/<name>/detect-port")
    def detect_service_port_api(name):
        """API endpoint to detect port for a service"""
        config = load_config()
        if name not in config["services"]:
            return jsonify({"error": "Service not found"}), 404

        detected_port = detect_service_port(name)
        if detected_port:
            return jsonify({"port": detected_port, "success": True})
        else:
            return jsonify({"error": "No port detected", "success": False}), 404
