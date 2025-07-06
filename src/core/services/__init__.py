#!/usr/bin/env python3

# Re-export all service functions for backward compatibility
from .lifecycle import (
    control_service,
    get_service_status,
    register_service,
    unregister_service,
)
from .ports import (
    check_service_running,
    detect_service_port,
    detect_service_ports,
    get_service_port_status,
    select_primary_port,
    set_port_management_mode,
    set_port_mode,
    validate_service_port,
)
from .utils import rename_service

__all__ = [
    # Service lifecycle
    "register_service",
    "unregister_service",
    "control_service",
    "get_service_status",
    # Port management
    "check_service_running",
    "detect_service_ports",
    "select_primary_port",
    "detect_service_port",
    "get_service_port_status",
    "validate_service_port",
    "set_port_management_mode",
    "set_port_mode",
    # Utilities
    "rename_service",
]
