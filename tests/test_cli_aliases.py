"""Test CLI alias commands"""
from unittest.mock import patch

from click.testing import CliRunner

from control_panel.cli import cli


def test_ls_alias_invokes_list_command():
    """Test that 'ls' alias correctly invokes the 'list' command"""
    mock_config = {
        "services": {
            "test-service": {"port": 8000, "command": "python -m http.server"},
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config), patch(
        "control_panel.cli.get_service_status", return_value=("active", True)
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["ls"])

        assert result.exit_code == 0
        assert "test-service" in result.output
        assert "8000" in result.output


def test_ps_shows_only_running_services():
    """Test that 'ps' command shows only running services"""
    mock_config = {
        "services": {
            "running-service": {"port": 8000, "command": "python -m http.server"},
            "stopped-service": {"port": 8001, "command": "python -m http.server"},
        }
    }

    def mock_status(name):
        if name == "running-service":
            return ("active", True)
        return ("inactive", False)

    with patch("control_panel.cli.load_config", return_value=mock_config), patch(
        "control_panel.cli.get_service_status", side_effect=mock_status
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["ps"])

        assert result.exit_code == 0
        assert "running-service" in result.output
        assert "stopped-service" not in result.output


def test_ps_with_no_running_services():
    """Test that 'ps' command handles no running services gracefully"""
    mock_config = {
        "services": {
            "stopped-service": {"port": 8000, "command": "python -m http.server"},
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config), patch(
        "control_panel.cli.get_service_status", return_value=("inactive", False)
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["ps"])

        assert result.exit_code == 0
        assert "No services currently running" in result.output


def test_restart_all_restarts_all_services():
    """Test that 'restart-all' command restarts all services"""
    mock_config = {
        "services": {
            "service1": {
                "port": 8000,
                "command": "python -m http.server",
                "enabled": True,
            },
            "service2": {
                "port": 8001,
                "command": "python -m http.server",
                "enabled": False,
            },
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config), patch(
        "control_panel.cli.control_service", return_value=(True, None)
    ) as mock_control, patch("control_panel.cli.kill_process_by_port") as mock_kill:
        runner = CliRunner()
        result = runner.invoke(cli, ["restart-all"])

        assert result.exit_code == 0
        assert "2 service(s)" in result.output
        assert "All 2 services restarted successfully" in result.output

        # Should call control_service for stop and start on both services
        assert mock_control.call_count == 4  # 2 stops + 2 starts
        assert mock_kill.call_count == 2  # Kill processes for both services


def test_restart_all_enabled_only():
    """Test that 'restart-all --enabled-only' restarts only enabled services"""
    mock_config = {
        "services": {
            "enabled-service": {
                "port": 8000,
                "command": "python -m http.server",
                "enabled": True,
            },
            "disabled-service": {
                "port": 8001,
                "command": "python -m http.server",
                "enabled": False,
            },
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config), patch(
        "control_panel.cli.control_service", return_value=(True, None)
    ) as mock_control, patch("control_panel.cli.kill_process_by_port") as mock_kill:
        runner = CliRunner()
        result = runner.invoke(cli, ["restart-all", "--enabled-only"])

        assert result.exit_code == 0
        assert "1 service(s)" in result.output
        assert "enabled-service" in result.output
        assert "disabled-service" not in result.output

        # Should only restart the enabled service
        assert mock_control.call_count == 2  # 1 stop + 1 start
        assert mock_kill.call_count == 1


def test_restart_all_handles_failures():
    """Test that 'restart-all' handles service restart failures gracefully"""
    mock_config = {
        "services": {
            "good-service": {"port": 8000, "command": "python -m http.server"},
            "bad-service": {"port": 8001, "command": "python -m http.server"},
        }
    }

    def mock_control(name, action):
        if name == "bad-service" and action == "start":
            return (False, "Service failed to start")
        return (True, None)

    with patch("control_panel.cli.load_config", return_value=mock_config), patch(
        "control_panel.cli.control_service", side_effect=mock_control
    ), patch("control_panel.cli.kill_process_by_port"):
        runner = CliRunner()
        result = runner.invoke(cli, ["restart-all"])

        assert result.exit_code == 0
        assert "1 services restarted successfully" in result.output
        assert "1 services failed to restart: bad-service" in result.output


def test_restart_all_with_no_services():
    """Test that 'restart-all' handles empty service list"""
    mock_config = {"services": {}}

    with patch("control_panel.cli.load_config", return_value=mock_config):
        runner = CliRunner()
        result = runner.invoke(cli, ["restart-all"])

        assert result.exit_code == 0
        assert "No services registered" in result.output


def test_restart_all_enabled_only_with_no_enabled_services():
    """Test that 'restart-all --enabled-only' handles no enabled services"""
    mock_config = {
        "services": {
            "disabled-service": {
                "port": 8000,
                "command": "python -m http.server",
                "enabled": False,
            },
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        runner = CliRunner()
        result = runner.invoke(cli, ["restart-all", "--enabled-only"])

        assert result.exit_code == 0
        assert "No enabled services to restart" in result.output
