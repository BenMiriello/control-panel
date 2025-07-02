"""Test CLI auto-completion functionality"""
import sys
from unittest.mock import patch

import click
from click.shell_completion import CompletionItem

# Clear sys.argv before importing CLI to avoid Click parsing pytest args
original_argv = sys.argv
sys.argv = ["test"]

try:
    from control_panel.cli import (
        PORT_RANGE,
        SERVICE_NAME,
        SMART_PORT,
        CompletePortRanges,
        CompleteServiceNames,
        CompleteSmartPorts,
    )
finally:
    sys.argv = original_argv


def test_complete_services_returns_matching_services():
    """Test that CompleteServiceNames returns services matching incomplete input"""
    mock_config = {
        "services": {
            "web-server": {"port": 8000},
            "web-api": {"port": 8001},
            "database": {"port": 5432},
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteServiceNames()

        # Create mock context
        ctx = click.Context(click.Command("test"))
        param = click.Argument(["name"])

        # Test completion with prefix
        result = completer.shell_complete(ctx, param, "web")
        service_names = [item.value for item in result]

        assert "web-server" in service_names
        assert "web-api" in service_names
        assert "database" not in service_names


def test_complete_services_returns_all_when_no_prefix():
    """Test that CompleteServiceNames returns all services when no prefix given"""
    mock_config = {
        "services": {
            "service1": {"port": 8000},
            "service2": {"port": 8001},
        }
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteServiceNames()

        # Create mock context
        ctx = click.Context(click.Command("test"))
        param = click.Argument(["name"])

        result = completer.shell_complete(ctx, param, "")
        service_names = [item.value for item in result]

        assert "service1" in service_names
        assert "service2" in service_names
        assert len(service_names) == 2


def test_complete_port_ranges_returns_available_ranges():
    """Test that CompletePortRanges returns available port ranges"""
    mock_config = {
        "services": {},
        "port_ranges": {
            "web": {"start": 8000, "end": 8999},
            "api": {"start": 9000, "end": 9999},
            "database": {"start": 5000, "end": 5999},
        },
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompletePortRanges()

        # Test completion with prefix
        result = completer.shell_complete(None, None, "web")
        range_names = [item.value for item in result]

        assert "web" in range_names
        assert "api" not in range_names
        assert "database" not in range_names


def test_complete_smart_ports_suggests_available_ports():
    """Test that CompleteSmartPorts suggests available ports based on ranges"""
    mock_config = {
        "services": {
            "existing-service": {"port": 8000},  # Port 8000 is taken
        },
        "port_ranges": {
            "web": {"start": 8000, "end": 8999},
        },
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteSmartPorts()

        result = completer.shell_complete(None, None, "80")
        port_suggestions = [item.value for item in result]

        # Should suggest 8010 (8000 + 10) since 8000 is taken
        assert "8010" in port_suggestions
        # Should not suggest 8000 since it's already used
        assert "8000" not in port_suggestions


def test_complete_smart_ports_handles_multiple_ranges():
    """Test that CompleteSmartPorts handles multiple port ranges"""
    mock_config = {
        "services": {},
        "port_ranges": {
            "web": {"start": 8000, "end": 8999},
            "api": {"start": 9000, "end": 9999},
        },
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteSmartPorts()

        result = completer.shell_complete(None, None, "")
        port_suggestions = [item.value for item in result]

        # Should suggest base ports from both ranges
        assert "8000" in port_suggestions  # From web range
        assert "9000" in port_suggestions  # From api range


def test_complete_smart_ports_handles_exceptions_gracefully():
    """Test that CompleteSmartPorts doesn't crash on config errors"""
    with patch("control_panel.cli.load_config", side_effect=Exception("Config error")):
        completer = CompleteSmartPorts()

        result = completer.shell_complete(None, None, "80")

        # Should return empty list on error, not crash
        assert result == []


def test_complete_port_ranges_handles_exceptions_gracefully():
    """Test that CompletePortRanges doesn't crash on config errors"""
    with patch("control_panel.cli.load_config", side_effect=Exception("Config error")):
        completer = CompletePortRanges()

        result = completer.shell_complete(None, None, "web")

        # Should return empty list on error, not crash
        assert result == []


def test_service_name_type_instance():
    """Test that SERVICE_NAME is properly instantiated"""
    assert isinstance(SERVICE_NAME, CompleteServiceNames)
    assert SERVICE_NAME.name == "service_name"


def test_port_range_type_instance():
    """Test that PORT_RANGE is properly instantiated"""
    assert isinstance(PORT_RANGE, CompletePortRanges)
    assert PORT_RANGE.name == "port_range"


def test_smart_port_type_instance():
    """Test that SMART_PORT is properly instantiated"""
    assert isinstance(SMART_PORT, CompleteSmartPorts)
    assert SMART_PORT.name == "port"


def test_completion_item_structure():
    """Test that completion items have correct structure"""
    mock_config = {"services": {"test-service": {"port": 8000}}}

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteServiceNames()

        # Create mock context
        ctx = click.Context(click.Command("test"))
        param = click.Argument(["name"])

        result = completer.shell_complete(ctx, param, "test")

        assert len(result) == 1
        item = result[0]
        assert isinstance(item, CompletionItem)
        assert item.value == "test-service"


def test_complete_service_names_handles_exceptions_gracefully():
    """Test that CompleteServiceNames doesn't crash on config errors"""
    with patch("control_panel.cli.load_config", side_effect=Exception("Config error")):
        completer = CompleteServiceNames()

        # Create mock context
        ctx = click.Context(click.Command("test"))
        param = click.Argument(["name"])

        result = completer.shell_complete(ctx, param, "test")

        # Should return empty list on error, not crash
        assert result == []


def test_smart_ports_incremental_logic():
    """Test the incremental port suggestion logic"""
    mock_config = {
        "services": {
            "service1": {"port": 8000},  # 8000 taken
            "service2": {"port": 8010},  # 8010 taken
        },
        "port_ranges": {
            "web": {"start": 8000, "end": 8999},
        },
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteSmartPorts()

        result = completer.shell_complete(None, None, "80")
        port_suggestions = [item.value for item in result]

        # Should skip 8000 and 8010 (taken), suggest 8020
        assert "8020" in port_suggestions
        assert "8000" not in port_suggestions
        assert "8010" not in port_suggestions


def test_smart_ports_fallback_to_increments_of_5():
    """Test that smart ports falls back to increments of 5 when 10s are taken"""
    # Create scenario where all increments of 10 are taken
    taken_ports = {8000 + i * 10 for i in range(10)}  # 8000, 8010, 8020, ... 8090
    mock_services = {
        f"service{i}": {"port": port} for i, port in enumerate(taken_ports)
    }

    mock_config = {
        "services": mock_services,
        "port_ranges": {
            "web": {"start": 8000, "end": 8999},
        },
    }

    with patch("control_panel.cli.load_config", return_value=mock_config):
        completer = CompleteSmartPorts()

        result = completer.shell_complete(None, None, "80")
        port_suggestions = [item.value for item in result]

        # Should suggest 8005 (increment of 5) since increments of 10 are taken
        assert "8005" in port_suggestions
