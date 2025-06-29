from unittest.mock import Mock, patch

from utils.service import (
    control_service,
    get_service_status,
    register_service,
    unregister_service,
)


def test_register_service_success(mock_subprocess):
    """Test successful service registration"""
    mock_config = {
        "services": {},
        "port_ranges": {"web": {"start": 8000, "end": 8999}},
    }

    with patch("utils.service.load_config", return_value=mock_config), patch(
        "utils.service.save_config"
    ) as mock_save, patch("utils.service.create_env_file"), patch(
        "utils.service.find_available_port", return_value=8000
    ):
        success, port = register_service(
            name="test-service",
            command="python -m http.server",
            port=None,
            working_dir="/home/user/app",
            range_name="web",
            env_vars=["NODE_ENV=production"],
        )

        assert success is True
        assert port == 8000
        mock_save.assert_called_once()


def test_register_service_fails_when_service_exists():
    """Test that registration fails when service already exists"""
    mock_config = {
        "services": {"test-service": {"port": 8000}},
        "port_ranges": {"web": {"start": 8000, "end": 8999}},
    }

    with patch("utils.service.load_config", return_value=mock_config):
        success, message = register_service(
            name="test-service",
            command="python -m http.server",
            port=None,
            working_dir="/home/user/app",
            range_name="web",
            env_vars=[],
        )

        assert success is False
        assert "already exists" in message


def test_register_service_fails_with_invalid_port_range():
    """Test that registration fails with invalid port range"""
    mock_config = {
        "services": {},
        "port_ranges": {},
    }

    with patch("utils.service.load_config", return_value=mock_config):
        success, message = register_service(
            name="test-service",
            command="python -m http.server",
            port=None,
            working_dir="/home/user/app",
            range_name="invalid",
            env_vars=[],
        )

        assert success is False
        assert "not defined" in message


def test_unregister_service_success(mock_subprocess):
    """Test successful service unregistration"""
    mock_config = {
        "services": {"test-service": {"port": 8000}},
        "port_ranges": {},
    }

    with patch("utils.service.load_config", return_value=mock_config), patch(
        "utils.service.save_config"
    ) as mock_save, patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.unlink"
    ) as mock_unlink:
        success, _ = unregister_service("test-service")

        assert success is True
        mock_save.assert_called_once()
        mock_unlink.assert_called_once()
        # Verify systemctl calls were made
        assert mock_subprocess.call_count == 2


def test_unregister_service_fails_when_not_found():
    """Test that unregistration fails when service not found"""
    mock_config = {"services": {}, "port_ranges": {}}

    with patch("utils.service.load_config", return_value=mock_config):
        success, message = unregister_service("nonexistent")

        assert success is False
        assert "not found" in message


def test_get_service_status_active():
    """Test getting status of active service"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(returncode=0, stdout="active\n"),
            Mock(returncode=0, stdout="enabled\n"),
        ]

        status, enabled = get_service_status("test-service")

        assert status == "active"
        assert enabled is True
        assert mock_run.call_count == 2


def test_get_service_status_inactive():
    """Test getting status of inactive service"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(returncode=1, stdout="inactive\n"),
            Mock(returncode=1, stdout="disabled\n"),
        ]

        status, enabled = get_service_status("test-service")

        assert status == "inactive"
        assert enabled is False


def test_control_service_success(mock_subprocess):
    """Test successful service control"""
    mock_config = {"services": {"test-service": {"port": 8000}}}

    with patch("utils.service.load_config", return_value=mock_config):
        success, _ = control_service("test-service", "start")

        assert success is True
        mock_subprocess.assert_called_once()


def test_control_service_fails_when_not_found():
    """Test that control fails when service not found"""
    mock_config = {"services": {}}

    with patch("utils.service.load_config", return_value=mock_config):
        success, message = control_service("nonexistent", "start")

        assert success is False
        assert "not found" in message


def test_control_service_fails_on_subprocess_error():
    """Test that control fails on subprocess error"""
    mock_config = {"services": {"test-service": {"port": 8000}}}

    with patch("utils.service.load_config", return_value=mock_config), patch(
        "subprocess.run"
    ) as mock_run:
        mock_run.return_value = Mock(returncode=1, stderr="Command failed")

        success, message = control_service("test-service", "start")

        assert success is False
        assert "Failed to start" in message
