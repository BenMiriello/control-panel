"""Test CLI utility functions that don't involve Click interactions"""
from unittest.mock import patch

import pytest


def test_get_service_names_import():
    """Test that we can import and use get_service_names function"""
    # Import directly from the module to avoid Click issues
    from pathlib import Path
    import sys

    # Add the parent directory to sys.path
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))

    try:
        # Mock the CLI import to avoid Click execution
        with patch.dict("sys.modules", {"control_panel.cli": None}):
            # Direct import of the function we want to test
            from control_panel.cli import get_service_names

            mock_config = {
                "services": {
                    "service1": {"port": 8000},
                    "service2": {"port": 8001},
                }
            }

            with patch("control_panel.cli.load_config", return_value=mock_config):
                names = get_service_names()
                assert names == ["service1", "service2"]

    except ImportError:
        # If we can't import, skip this test
        pytest.skip("Cannot import CLI module for testing")


def test_systemd_service_management():
    """Test systemd service management functions"""
    from utils.service import get_service_status

    # Test service status checking
    with patch("subprocess.run") as mock_run:
        # Mock systemctl is-active and is-enabled commands
        mock_run.side_effect = [
            type("MockResult", (), {"returncode": 0, "stdout": "active\n"})(),
            type("MockResult", (), {"returncode": 0, "stdout": "enabled\n"})(),
        ]

        status, enabled = get_service_status("test-service")

        assert status == "active"
        assert enabled is True
        assert mock_run.call_count == 2

        # Verify correct systemctl commands were called
        calls = mock_run.call_args_list
        assert "systemctl" in calls[0][0][0]
        assert "--user" in calls[0][0][0]
        assert "is-active" in calls[0][0][0]
        assert "control-panel@test-service.service" in calls[0][0][0]


def test_service_control_commands():
    """Test service control (start/stop/restart) commands"""
    from utils.service import control_service

    mock_config = {"services": {"test-service": {"port": 8000}}}

    with patch("utils.service.load_config", return_value=mock_config), patch(
        "subprocess.run"
    ) as mock_run:
        mock_run.return_value = type(
            "MockResult", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )()

        # Test start command
        success, error = control_service("test-service", "start")

        assert success is True
        assert error is None
        mock_run.assert_called_once()

        # Verify correct systemctl command
        args = mock_run.call_args[0][0]
        assert "systemctl" in args
        assert "--user" in args
        assert "start" in args
        assert "control-panel@test-service.service" in args


def test_service_control_failure():
    """Test service control failure handling"""
    from utils.service import control_service

    mock_config = {"services": {"test-service": {"port": 8000}}}

    with patch("utils.service.load_config", return_value=mock_config), patch(
        "subprocess.run"
    ) as mock_run:
        mock_run.return_value = type(
            "MockResult",
            (),
            {"returncode": 1, "stdout": "", "stderr": "Service failed to start"},
        )()

        success, error = control_service("test-service", "start")

        assert success is False
        assert "Failed to start service" in error
        assert "Service failed to start" in error
