#!/usr/bin/env python3

import json
import os

# Clear sys.argv before importing to avoid Click parsing pytest args
import sys
import tempfile
from unittest.mock import patch

import pytest

original_argv = sys.argv
sys.argv = ["test"]

try:
    from control_panel.utils.config import load_config, save_config
except ImportError:
    # Fallback for local development
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from control_panel.utils.config import load_config, save_config
finally:
    sys.argv = original_argv


@pytest.fixture
def app():
    """Create test Flask app"""
    # Import the already configured app with routes
    from control_panel.web_ui import app

    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def temp_config():
    """Create temporary config for testing"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        # Use secure temp directory instead of /tmp/test
        secure_temp = tempfile.mkdtemp()
        config = {
            "services": {
                "test-service": {
                    "command": "python app.py",
                    "port": 8080,
                    "working_dir": secure_temp,
                    "enabled": True,
                    "env": {"PORT": "8080", "DEBUG": "1"},
                }
            },
            "port_ranges": {"default": {"start": 8000, "end": 9000}},
        }
        json.dump(config, f)
        temp_path = f.name

    # Mock the config file path
    from pathlib import Path

    with patch("control_panel.utils.config.CONFIG_FILE", Path(temp_path)):
        with patch("utils.config.CONFIG_FILE", Path(temp_path)):
            yield temp_path

    # Cleanup
    os.unlink(temp_path)
    import shutil

    shutil.rmtree(secure_temp, ignore_errors=True)


class TestEditService:
    """Test service editing functionality"""

    def test_edit_service_get_existing(self, client, temp_config):
        """Test GET request for existing service"""
        response = client.get("/services/edit/test-service")
        assert response.status_code == 200
        assert b"Edit Service: test-service" in response.data
        assert b"python app.py" in response.data
        assert b"8080" in response.data
        # Check for working directory field exists (path will be secure temp dir)
        assert b'name="path"' in response.data
        assert b"DEBUG=1" in response.data

    def test_edit_service_get_nonexistent(self, client, temp_config):
        """Test GET request for non-existent service"""
        response = client.get("/services/edit/nonexistent")
        assert response.status_code == 302  # Redirect
        assert "/?" in response.location
        assert "status=error" in response.location
        assert "not+found" in response.location

    def test_edit_service_post_command_update(self, client, temp_config):
        """Test POST request to update command"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python new_app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302  # Redirect
        assert "/?" in response.location
        assert "status=success" in response.location

        # Verify config was updated
        config = load_config()
        assert config["services"]["test-service"]["command"] == "python new_app.py"

    def test_edit_service_post_port_update(self, client, temp_config):
        """Test POST request to update port"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "port": "9090",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302

        # Verify config was updated
        config = load_config()
        assert config["services"]["test-service"]["port"] == 9090
        assert config["services"]["test-service"]["env"]["PORT"] == "9090"

    def test_edit_service_post_invalid_port(self, client, temp_config):
        """Test POST request with invalid port"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "port": "99999",  # Invalid port
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302
        assert "status=error" in response.location
        assert "Invalid+port" in response.location

    def test_edit_service_post_working_dir_update(self, client, temp_config):
        """Test POST request to update working directory"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "port": "8080",
                "path": "/new/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302

        # Verify config was updated
        config = load_config()
        assert config["services"]["test-service"]["working_dir"] == "/new/path"

    def test_edit_service_post_env_vars_update(self, client, temp_config):
        """Test POST request to update environment variables"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=0\nNEW_VAR=test_value\nANOTHER=123",
            },
        )

        assert response.status_code == 302

        # Verify config was updated
        config = load_config()
        env_vars = config["services"]["test-service"]["env"]
        assert env_vars["DEBUG"] == "0"
        assert env_vars["NEW_VAR"] == "test_value"
        assert env_vars["ANOTHER"] == "123"
        assert env_vars["PORT"] == "8080"  # Should be preserved

    @patch("control_panel.utils.service.detect_service_port")
    def test_edit_service_post_detect_port_success(
        self, mock_detect, client, temp_config
    ):
        """Test POST request with port detection - success"""
        mock_detect.return_value = 9000

        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
                "detect_port": "on",
            },
        )

        assert response.status_code == 302

        # Verify config was updated
        config = load_config()
        assert config["services"]["test-service"]["port"] == 9000
        assert config["services"]["test-service"]["env"]["PORT"] == "9000"

    @patch("control_panel.utils.service.detect_service_port")
    def test_edit_service_post_detect_port_failure(
        self, mock_detect, client, temp_config
    ):
        """Test POST request with port detection - failure"""
        mock_detect.return_value = None

        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
                "detect_port": "on",
            },
        )

        assert response.status_code == 302
        assert "status=error" in response.location
        assert "not+running" in response.location

    def test_edit_service_post_nonexistent(self, client, temp_config):
        """Test POST request for non-existent service"""
        response = client.post(
            "/services/edit/nonexistent",
            data={"command": "python app.py", "port": "8080"},
        )

        assert response.status_code == 302
        assert "status=error" in response.location
        assert "not+found" in response.location

    def test_edit_service_post_empty_command(self, client, temp_config):
        """Test POST request with empty command"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "",  # Empty command
                "port": "8080",
                "path": "/secure/temp/path",
            },
        )

        assert response.status_code == 302

        # Verify command wasn't changed
        config = load_config()
        assert config["services"]["test-service"]["command"] == "python app.py"

    def test_edit_service_malformed_env_vars(self, client, temp_config):
        """Test POST request with malformed environment variables"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "command": "python app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "INVALID_LINE\nVALID=test\nANOTHER_INVALID",
            },
        )

        assert response.status_code == 302

        # Verify only valid env vars were set
        config = load_config()
        env_vars = config["services"]["test-service"]["env"]
        assert "VALID" in env_vars
        assert env_vars["VALID"] == "test"
        assert "INVALID_LINE" not in env_vars
        assert "ANOTHER_INVALID" not in env_vars

    def test_edit_service_name_change_success(self, client, temp_config):
        """Test successful service name change"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "name": "renamed-service",
                "command": "python app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302

        # Verify service was renamed in config
        config = load_config()
        assert "test-service" not in config["services"]
        assert "renamed-service" in config["services"]
        assert config["services"]["renamed-service"]["command"] == "python app.py"

    def test_edit_service_name_change_invalid_name(self, client, temp_config):
        """Test service name change with invalid characters"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "name": "invalid@name!",
                "command": "python app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302
        assert "status=error" in response.location

        # Verify service was not renamed
        config = load_config()
        assert "test-service" in config["services"]
        assert "invalid@name!" not in config["services"]

    def test_edit_service_name_change_duplicate_name(self, client, temp_config):
        """Test service name change to existing service name"""
        # Add another service to config
        config = load_config()
        config["services"]["existing-service"] = {
            "command": "python other.py",
            "port": 9090,
            "working_dir": "/secure/temp/path",
            "enabled": False,
            "env": {"PORT": "9090"},
        }
        save_config(config)

        response = client.post(
            "/services/edit/test-service",
            data={
                "name": "existing-service",
                "command": "python app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302
        assert "status=error" in response.location

        # Verify service was not renamed
        config = load_config()
        assert "test-service" in config["services"]
        assert len(config["services"]) == 2  # Both services still exist

    def test_edit_service_name_no_change(self, client, temp_config):
        """Test editing service with same name (no rename needed)"""
        response = client.post(
            "/services/edit/test-service",
            data={
                "name": "test-service",  # Same name
                "command": "python new_app.py",
                "port": "8080",
                "path": "/secure/temp/path",
                "env_vars": "DEBUG=1",
            },
        )

        assert response.status_code == 302

        # Verify service still exists with updated command
        config = load_config()
        assert "test-service" in config["services"]
        assert config["services"]["test-service"]["command"] == "python new_app.py"


if __name__ == "__main__":
    pytest.main([__file__])
