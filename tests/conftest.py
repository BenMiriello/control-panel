import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".config" / "control-panel"
        config_dir.mkdir(parents=True)
        # Create backup and env directories
        (config_dir / "backups").mkdir()
        (config_dir / "env").mkdir()
        yield config_dir


@pytest.fixture
def isolated_config(temp_config_dir):
    """Completely isolate tests from real config files"""
    with patch("utils.config.CONFIG_DIR", temp_config_dir), patch(
        "utils.config.CONFIG_FILE", temp_config_dir / "services.json"
    ), patch("utils.config.ENV_DIR", temp_config_dir / "env"), patch(
        "utils.config.BACKUP_DIR", temp_config_dir / "backups"
    ):
        yield temp_config_dir


@pytest.fixture
def mock_config():
    """Mock configuration data"""
    return {
        "services": {
            "test-service": {
                "command": "python -m http.server",
                "port": 8000,
                "working_dir": "/home/user/app",
                "enabled": False,
                "env": {"PORT": "8000"},
            }
        },
        "port_ranges": {"web": {"start": 8000, "end": 8999}},
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def mock_config_file(temp_config_dir, mock_config):
    """Create a mock config file"""
    config_file = temp_config_dir / "services.json"
    with open(config_file, "w") as f:
        json.dump(mock_config, f)
    return config_file
