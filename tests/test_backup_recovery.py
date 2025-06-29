import json
from unittest.mock import Mock, patch

from utils.config import backup_config, load_config, recover_config, save_config


def test_backup_config_creates_backup(isolated_config, mock_config):
    """Test that backup_config creates a timestamped backup"""
    config_file = isolated_config / "services.json"

    # Create initial config
    with open(config_file, "w") as f:
        json.dump(mock_config, f)

    # Create backup
    backup_file = backup_config()

    assert backup_file is not None
    assert backup_file.exists()
    assert "auto-backup-" in backup_file.name
    assert backup_file.suffix == ".json"

    # Verify backup content matches original
    with open(backup_file) as f:
        backup_data = json.load(f)
    assert backup_data == mock_config


def test_backup_config_no_file_returns_none(isolated_config):
    """Test that backup_config returns None when no config file exists"""
    backup_file = backup_config()
    assert backup_file is None


def test_save_config_creates_backup_automatically(isolated_config, mock_config):
    """Test that save_config automatically creates backup before overwriting"""
    config_file = isolated_config / "services.json"

    # Create initial config with services
    with open(config_file, "w") as f:
        json.dump(mock_config, f)

    # Modify and save config
    new_config = {"services": {"new-service": {"port": 9000}}, "port_ranges": {}}
    save_config(new_config)

    # Check that backup was created
    backup_files = list((isolated_config / "backups").glob("auto-backup-*.json"))
    assert len(backup_files) == 1

    # Verify backup contains original config
    with open(backup_files[0]) as f:
        backup_data = json.load(f)
    assert backup_data == mock_config

    # Verify new config was saved
    current_config = load_config()
    assert current_config == new_config


def test_recover_from_env_files(isolated_config):
    """Test recovery from environment files"""
    env_dir = isolated_config / "env"

    # Create mock environment files
    with open(env_dir / "test-service.env", "w") as f:
        f.write("COMMAND=python app.py\n")
        f.write("WORKING_DIR=/app\n")
        f.write("PORT=8080\n")
        f.write("DEBUG=true\n")

    with open(env_dir / "web-service.env", "w") as f:
        f.write("COMMAND=node server.js\n")
        f.write("PORT=3000\n")

    # Mock systemctl calls to simulate running services
    # Order: test-service is-active, test-service is-enabled, web-service is-active, web-service is-enabled
    with patch("subprocess.run") as mock_run:

        def mock_systemctl(cmd, **kwargs):
            if "is-active" in cmd and "test-service" in cmd[-1]:
                return Mock(returncode=0)  # test-service is active
            elif "is-enabled" in cmd and "test-service" in cmd[-1]:
                return Mock(returncode=0)  # test-service is enabled
            elif "is-active" in cmd and "web-service" in cmd[-1]:
                return Mock(returncode=0)  # web-service is active
            elif "is-enabled" in cmd and "web-service" in cmd[-1]:
                return Mock(returncode=1)  # web-service is disabled
            return Mock(returncode=1)  # default to inactive/disabled

        mock_run.side_effect = mock_systemctl

        recovered_count = recover_config()

    assert recovered_count == 2

    # Verify recovered config
    config = load_config()
    assert "test-service" in config["services"]
    assert "web-service" in config["services"]

    test_service = config["services"]["test-service"]
    assert test_service["command"] == "python app.py"
    assert test_service["port"] == 8080
    assert test_service["working_dir"] == "/app"
    assert test_service["enabled"] is True
    assert test_service["env"]["DEBUG"] == "true"

    web_service = config["services"]["web-service"]
    assert web_service["command"] == "node server.js"
    assert web_service["port"] == 3000
    assert web_service["enabled"] is False


def test_recover_config_skips_inactive_services(isolated_config):
    """Test that recovery skips services that aren't running"""
    env_dir = isolated_config / "env"

    # Create environment file for inactive service
    with open(env_dir / "inactive-service.env", "w") as f:
        f.write("COMMAND=python inactive.py\n")
        f.write("PORT=8080\n")

    # Mock systemctl to return inactive
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1)  # Service inactive

        recovered_count = recover_config()

    assert recovered_count == 0

    # Verify no services in config
    config = load_config()
    assert len(config["services"]) == 0


def test_data_loss_prevention_workflow(isolated_config, mock_config):
    """Test the complete data loss prevention workflow"""
    config_file = isolated_config / "services.json"

    # 1. Create initial config with services
    with open(config_file, "w") as f:
        json.dump(mock_config, f)

    # 2. Simulate accidental overwrite with empty config
    empty_config = {"services": {}, "port_ranges": {}}
    save_config(empty_config)

    # 3. Verify backup was created
    backup_files = list((isolated_config / "backups").glob("auto-backup-*.json"))
    assert len(backup_files) == 1

    # 4. Verify we can restore from backup
    with open(backup_files[0]) as f:
        restored_config = json.load(f)
    assert restored_config == mock_config

    # 5. Or recover from environment files if they exist
    env_dir = isolated_config / "env"
    with open(env_dir / "test-service.env", "w") as f:
        f.write("COMMAND=python -m http.server\n")
        f.write("PORT=8000\n")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(returncode=0),  # is-active
            Mock(returncode=1),  # is-enabled (disabled)
        ]

        recovered_count = recover_config()

    assert recovered_count == 1
    final_config = load_config()
    assert "test-service" in final_config["services"]
