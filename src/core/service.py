#!/usr/bin/env python3

# Backward compatibility - re-export all service functions
from .services.lifecycle import *  # noqa: F403, F401
from .services.ports import *  # noqa: F403, F401
from .services.utils import *  # noqa: F403, F401

# This file exists for backward compatibility with existing imports like:
# from core.service import get_service_status
#
# All actual functionality has been moved to:
# - core.services.lifecycle - register, unregister, control, status
# - core.services.ports - port detection, validation, management
# - core.services.utils - rename, utilities
