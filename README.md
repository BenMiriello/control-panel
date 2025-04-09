# Control Panel

A central management system for services, ports, and startup configurations on Linux.

## Overview

This tool helps you manage multiple services running on your Linux machine with features for:

- Centralized port management
- Automatic service startup via systemd
- Service registration and configuration
- Simple CLI interface to control all services
- Web-based UI for easier management

## Quick Start

```bash
# Clone the repository
git clone https://github.com/BenMiriello/control-panel.git
cd control-panel

# Install dependencies
pip install -r requirements.txt

# Setup the control panel
./setup.sh

# Register a new service via CLI
./control.py register --name my-service --command '/path/to/service' --port 8080

# List all services
./control.py list

# Start a service
./control.py start my-service

# Start the web UI
./start.sh
```

## Features

- Central configuration file for all services
- Automatic port assignment and management
- Systemd integration for service auto-start
- Live log viewing
- Service status monitoring
- Web-based management interface

## Web UI

Control Panel includes a web-based user interface that makes it easy to:

- View all registered services and their status
- Start, stop, and restart services
- Enable/disable services for automatic startup
- View service logs in real-time
- Add new services and port ranges
- Monitor service status

To start the web UI, simply run:

```bash
./start.sh
```

This will start the web interface on http://localhost:9000 by default.

## CLI Usage

### Registering a Service

```bash
./control.py register --name service-name --command '/path/to/start-script.sh' [--port 8080] [--dir /working/directory] [--env KEY=VALUE]
```

### Managing Services

```bash
# List all services
./control.py list

# Start a service
./control.py start service-name

# Stop a service
./control.py stop service-name

# Restart a service
./control.py restart service-name

# Enable automatic startup
./control.py enable service-name

# Disable automatic startup
./control.py disable service-name

# View service logs
./control.py logs service-name

# Unregister a service
./control.py unregister service-name
```

### Managing Port Ranges

```bash
# Add a new port range
./control.py add_range range-name 8000 9000
```

## Configuration

All service configurations are stored in `~/.config/control-panel/services.json`.

## Systemd Integration

Control Panel uses systemd to manage service startup. Each registered service gets a systemd user service that can be managed through the Control Panel interface.
