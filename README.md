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
- Command completion for service names

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
panel register --name service-name --command "full-command-to-start-service" [--port 8080] [--dir /working/directory] [--env KEY=VALUE]
```

When registering a service, make sure to:
- Use the full command needed to start your service, not just the path
- Include any arguments or options your command needs
- Wrap the command in quotes if it contains spaces or special characters
- Specify a working directory if needed
- Add environment variables as needed using `--env`

Examples:

```bash
# Node.js application
panel register --name my-node-app --command "node /path/to/app.js" --port 3000

# Python web application
panel register --name flask-app --command "python /path/to/app.py" --env FLASK_ENV=production

# Java application
panel register --name spring-app --command "java -jar /path/to/app.jar" --port 8080

# Custom shell script
panel register --name my-service --command "/path/to/start.sh" --dir /path/to/working/dir
```

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

Port ranges are used for automatic port assignment when registering services. If you don't specify a port when registering a service, Control Panel will automatically assign one from the default port range.

Port ranges are useful for grouping similar services together. For example, you might want to use:
- 8000-8099 for web applications
- 9000-9099 for APIs
- 3000-3099 for development servers

```bash
# Add a new port range
panel add_range range-name start-port end-port

# Example:
panel add_range web 8000 8099
panel add_range api 9000 9099

# Register a service using a specific port range
panel register --name my-service --command "node server.js" --range web
```

## Tab Completion

Control Panel includes command completion for Bash and Zsh. This allows you to press TAB to complete service names and commands.

To enable tab completion for your shell:

```bash
# For Bash
panel --install-completion=bash

# For Zsh
panel --install-completion=zsh

# Restart your shell or source your profile
source ~/.bashrc  # or ~/.zshrc for Zsh
```

Once enabled, you can use tab completion for service names:

```bash
panel start <TAB>       # Lists all services
panel stop my-<TAB>     # Completes service names starting with "my-"
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

### Services managed by other systems

If you're migrating from another service manager like PM2, make sure to stop and remove the service from that system first:

```bash
# For PM2
pm2 stop service-name
pm2 delete service-name
```

Then register it with Control Panel. Trying to manage the same service with multiple systems can cause conflicts.

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
