import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from utils.config import find_available_port, load_config, save_config


def test_load_config_creates_default_when_missing():
    """Test that load_config creates default config when file doesn't exist"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("utils.config.CONFIG_DIR", Path(temp_dir)), patch(
            "utils.config.CONFIG_FILE", Path(temp_dir) / "services.json"
        ):
            config = load_config()

            assert "services" in config
            assert "port_ranges" in config
            assert config["port_ranges"]["default"]["start"] == 8000
            assert config["port_ranges"]["default"]["end"] == 9000


def test_load_config_reads_existing_file(temp_config_dir, mock_config_file):
    """Test that load_config reads existing config file"""
    with patch("utils.config.CONFIG_DIR", temp_config_dir), patch(
        "utils.config.CONFIG_FILE", mock_config_file
    ):
        config = load_config()

        assert config["services"]["test-service"]["port"] == 8000
        assert config["port_ranges"]["web"]["start"] == 8000


def test_save_config_writes_file(temp_config_dir):
    """Test that save_config writes config to file"""
    test_config = {"services": {}, "port_ranges": {}}
    config_file = temp_config_dir / "services.json"

    with patch("utils.config.CONFIG_DIR", temp_config_dir), patch(
        "utils.config.CONFIG_FILE", config_file
    ):
        save_config(test_config)

        assert config_file.exists()

        with open(config_file) as f:
            saved_config = json.load(f)

        assert saved_config == test_config


def test_find_available_port_returns_first_available():
    """Test that find_available_port returns first available port"""
    port_range = {"start": 8000, "end": 8010}

    with patch("utils.config.load_config") as mock_load:
        mock_load.return_value = {"services": {}}

        port = find_available_port(port_range)
        assert port == 8000


def test_find_available_port_skips_used_ports():
    """Test that find_available_port skips ports already in use"""
    port_range = {"start": 8000, "end": 8010}

    with patch("utils.config.load_config") as mock_load:
        mock_load.return_value = {
            "services": {
                "service1": {"port": 8000},
                "service2": {"port": 8001},
            }
        }

        port = find_available_port(port_range)
        assert port == 8002


def test_find_available_port_raises_when_no_ports_available():
    """Test that find_available_port raises when no ports are available"""
    port_range = {"start": 8000, "end": 8001}

    with patch("utils.config.load_config") as mock_load:
        mock_load.return_value = {
            "services": {
                "service1": {"port": 8000},
                "service2": {"port": 8001},
            }
        }

        with pytest.raises(ValueError, match="No available ports"):
            find_available_port(port_range)
