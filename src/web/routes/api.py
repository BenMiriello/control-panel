#!/usr/bin/env python3

from flask import jsonify, request

from core.config import load_config
from core.gpu import get_gpu_overview
from core.gpu.broker import clear_lease, get_lease_state, set_enabled
from core.service import detect_service_port
from core.services.listing import build_service_list
from core.system_metrics import get_all_metrics


def register_api_routes(app):
    """Register API routes with the Flask app"""

    @app.route("/api/metrics")
    def get_metrics():
        """API endpoint to get current system metrics"""
        return jsonify(get_all_metrics())

    @app.route("/api/gpu")
    def get_gpu():
        """GPU processes + broker lease snapshot"""
        return jsonify(get_gpu_overview())

    @app.route("/api/gpu/clear", methods=["POST"])
    def clear_gpu_lease():
        """Force-clear a stuck GPU broker lease"""
        state = get_lease_state()
        if not state.get("reachable"):
            return jsonify({"success": False, "error": "Redis not reachable"}), 503
        if not state.get("held"):
            return jsonify({"success": True, "message": "No lease held"})
        if clear_lease():
            return jsonify({"success": True, "message": "Lease cleared"})
        return jsonify({"success": False, "error": "Clear failed"}), 500

    @app.route("/api/gpu/set-enabled", methods=["POST"])
    def set_gpu_consumer_enabled():
        """Enable/disable an app's GPU access via the shared broker"""
        data = request.get_json(silent=True) or {}
        consumer = data.get("consumer")
        enabled = data.get("enabled")
        if not consumer or enabled is None:
            return (
                jsonify({"success": False, "error": "consumer and enabled required"}),
                400,
            )
        if set_enabled(consumer, bool(enabled)):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "broker unreachable"}), 503

    @app.route("/api/services")
    def get_services():
        """API endpoint to get the sorted, detailed service list"""
        return jsonify({"services": build_service_list()})

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
