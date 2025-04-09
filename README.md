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

# Start the web UI (in the background)
panel web --background
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
- Backup and restore functionality
- Simple update mechanism

## Web UI

Control Panel includes a web-based user interface that makes it easy to:

- View all registered services and their status
- Start, stop, and restart services
- Enable/disable services for automatic startup
- View service logs in real-time
- Add new services and port ranges
- Monitor service status

### Running the Web UI

You can run the web UI in two ways:

#### Foreground Mode (Interactive)

```bash
# Start the web UI in foreground mode
panel web

# Specify a different port
panel web --port 8090

# Don't open browser automatically
panel web --no-browser
```

This will run the web UI in your terminal. Press Ctrl+C to stop it.

#### Background Mode (As a Service)

```bash
# Start the web UI as a background service
panel web --background

# With custom host and port
panel web --background --host 0.0.0.0 --port 8090
```

When run in background mode, the web UI is registered as a regular service named `control-panel-web` and can be managed like any other service:

```bash
# Check status
panel list

# Stop the web UI
panel stop control-panel-web

# Start it again
panel start control-panel-web

# View logs
panel logs control-panel-web
```

### Network Access

By default, the web UI binds to `0.0.0.0` (all network interfaces) when run with `--background`, which allows you to access it from other devices on your network.

If you're having trouble accessing the web UI from other devices:

1. Make sure your firewall allows the port:
   ```bash
   sudo ufw allow 9000/tcp
   ```

2. Check that the web UI is binding to the correct interface:
   ```bash
   # When starting, use:
   panel web --host 0.0.0.0
   ```

3. Verify the service is running and listening on all interfaces:
   ```bash
   sudo netstat -tuln | grep 9000
   ```
   You should see `0.0.0.0:9000` in the output.

4. Try accessing using your machine's IP address:
   ```bash
   # Find your IP
   ip addr show
   
   # Then access via http://YOUR_IP:9000
   ```

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

### Backup, Restore, and Update

Control Panel provides commands to backup and restore your configuration, making it easy to migrate settings or recover from issues:

```bash
# Create a backup of your services configuration
panel backup
# Or specify a custom output file
panel backup -o my-backup.json

# Import configuration from a backup file
panel import_config backup-file.json

# Restore settings from an automatic backup (created during uninstall)
panel restore

# Update the Control Panel software
panel update
```

## Tab Completion

Control Panel includes command completion for Bash and Zsh. This allows you to press TAB to complete service names and commands.

To enable tab completion for your shell:

```bash
# For Bash
panel completion --shell bash

# For Zsh
panel completion --shell zsh

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

## Installation, Update, and Uninstallation

### Installation

The simplest way to install is using the provided script:

```bash
./install.sh
```

This will:
1. Create a virtual environment
2. Install the package in development mode
3. Set up necessary directories and configuration
4. Make the `panel` command available
5. Install shell completion

### Updating

You can easily update Control Panel with the built-in update command:

```bash
# Update Control Panel to the latest version
panel update
```

This will:
1. Pull the latest code if running from a git repository
2. Run the installation script
3. Update all dependencies

### Uninstallation

To completely remove Control Panel from your system while preserving your configuration:

```bash
# Run the uninstall command with default backup
panel uninstall
```

This will:
1. Create a backup of your configuration
2. Stop and disable all registered services
3. Remove service templates from systemd
4. Preserve your service configurations for future reinstalls

To completely remove everything including configurations:

```bash
# Force complete removal
panel uninstall --no-backup
```

To restore your settings after reinstalling:

```bash
# After reinstalling, restore settings from backup
panel restore
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

Make sure Flask is installed with compatible versions:

```bash
pip install 'flask>=2.0.0,<2.2.0' 'werkzeug>=2.0.0,<2.1.0'
```

Some newer versions of Flask/Werkzeug have compatibility issues that can prevent the web UI from starting.

### Cannot access web UI from other devices

If you're having trouble accessing the web UI from other devices on your network:

1. Make sure the web UI is running in background mode or with the correct host:
   ```bash
   panel web --background  # This will bind to 0.0.0.0 by default
   # OR
   panel web --host 0.0.0.0  # Explicitly binding to all interfaces
   ```

2. Check your firewall settings:
   ```bash
   # Allow the port through UFW
   sudo ufw allow 9000/tcp
   sudo ufw reload
   ```

3. Verify the service is properly listening:
   ```bash
   sudo ss -tulnp | grep 9000
   ```
