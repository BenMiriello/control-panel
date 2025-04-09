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

# Run the installation script
./install.sh

# Register a new service
panel register --name my-service --command '/path/to/service' --port 8080

# List all services
panel list

# Start a service
panel start my-service

# Start the web UI
panel web
```

## Features

- Central configuration file for all services
- Automatic port assignment and management
- Systemd integration for service auto-start
- Live log viewing
- Service status monitoring
- Web-based management interface
- Global `panel` command for easy access

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
panel web
```

This will start the web interface on http://localhost:9000 by default.

## CLI Usage

### Registering a Service

```bash
panel register --name service-name --command '/path/to/start-script.sh' [--port 8080] [--dir /working/directory] [--env KEY=VALUE]
```

When registering a service, make sure to:
- Use the full path to your command/script
- Specify a working directory if needed
- Add environment variables as needed using `--env`
- Your command should reference the `PORT` environment variable if it needs to know which port to listen on

### Managing Services

```bash
# List all services
panel list

# Start a service
panel start service-name

# Stop a service
panel stop service-name

# Restart a service
panel restart service-name

# Enable automatic startup
panel enable service-name

# Disable automatic startup
panel disable service-name

# View service logs
panel logs service-name

# Unregister a service
panel unregister service-name
```

### Managing Port Ranges

```bash
# Add a new port range
panel add_range range-name 8000 9000
```

## Configuration

All service configurations are stored in `~/.config/control-panel/services.json`.

## Systemd Integration

Control Panel uses systemd to manage service startup. Each registered service gets a systemd user service that can be managed through the Control Panel interface.

## Installation Options

### Using the install script

The simplest way to install is using the provided script:

```bash
./install.sh
```

This will:
1. Create a virtual environment
2. Install the package in development mode
3. Set up necessary directories and configuration
4. Make the `panel` command available

### Manual installation

If you prefer to install manually:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package
pip install -e .

# Set up systemd service template
mkdir -p ~/.config/systemd/user/
cp ./control_panel/templates/service-template.service ~/.config/systemd/user/control-panel@.service
systemctl --user daemon-reload
```

## Troubleshooting

### Service appears to be running but isn't accessible

If a service shows as "active" but isn't actually running, make sure:
1. Your command is using the `PORT` environment variable correctly
2. There are no other processes already using the allocated port
3. The service logs (`panel logs service-name`) may provide more details

### The list command shows an error

If you see an error when running `panel list`, ensure you've installed the package correctly and have all dependencies installed:

```bash
pip install -e .
```

### The web UI doesn't open

Make sure Flask is installed and the port you're using (default 9000) isn't already in use:

```bash
pip install flask
```
