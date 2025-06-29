# CLI Testing Framework

This directory contains comprehensive tests for the Control Panel CLI functionality.

## Test Structure

### `test_config.py`
Tests the configuration management system:
- Loading and saving configuration files
- Default configuration creation
- Port range management and availability checking
- Configuration file validation

### `test_service.py`
Tests the service management system:
- Service registration and unregistration
- Service status checking (systemd integration)
- Service control operations (start/stop/restart)
- Error handling for missing services

### `test_cli_utils.py`
Tests CLI utility functions and systemd integration:
- Service name extraction from configuration
- Systemd service status management
- Service control command execution
- Error handling for failed operations

### `conftest.py`
Provides shared test fixtures:
- Temporary configuration directories
- Mock configuration data
- Mock subprocess calls
- Mock configuration files

## Running Tests

Run all tests:
```bash
python3 -m pytest tests/ -v
```

Run with coverage:
```bash
python3 -m pytest tests/ --cov=control_panel --cov-report=html
```

Run specific test modules:
```bash
python3 -m pytest tests/test_config.py -v
python3 -m pytest tests/test_service.py -v
```

## Coverage Areas

The tests cover:
- ✅ Configuration management (utils/config.py)
- ✅ Service management (utils/service.py)
- ✅ Systemd integration
- ✅ CLI utility functions
- ✅ Error handling and edge cases
- ❌ Web UI (excluded from CLI testing scope)
- ❌ Full Click CLI integration (complex, skipped for now)

## Test Philosophy

These tests focus on:
1. **Unit Testing**: Testing individual functions in isolation
2. **Integration Testing**: Testing systemd command integration  
3. **Error Handling**: Ensuring graceful failure modes
4. **Mocking**: Using mocks to avoid system dependencies
5. **Coverage**: Achieving good test coverage of core functionality

The tests avoid testing the Click CLI framework directly due to its complexity,
instead focusing on the underlying business logic and system integration.
