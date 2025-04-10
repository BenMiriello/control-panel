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
panel register --name my-service --command "/absolute/path/to/executable args" --port 8080 --auto

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
- Global `panel` command with tab completion
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
panel register --name service-name --command "COMMAND" --port PORT [--path DIRECTORY] [--env KEY=VALUE] [--auto] [--start]
```

#### New Options

- `--auto`: Enable the service to auto-start at system boot 
- `--start`: Start the service immediately after registration
- `--path`: Working directory for the service (replaces the old `--dir` option, but both still work)

#### About the Command Parameter

The `--command` parameter must be the exact command you would run in a terminal to start your service:

- Include the full absolute path to executables
- For virtual environment Python applications, use the Python executable from the venv
- Include all required arguments and flags
- Wrap in quotes if it contains spaces

#### Examples:

```bash
# Basic executable with absolute path
panel register --name simple-service --command "/usr/local/bin/myservice" --port 8080

# Node.js application
panel register --name node-api --command "cd /home/user/projects/api && /usr/bin/node /home/user/projects/api/server.js" --path /home/user/projects/api --port 3000 --auto

# Node.js application using npm
panel register --name file-browser --command "cd /home/user/Documents/file-browser && /usr/bin/npm start" --path /home/user/Documents/file-browser --port 3002 --auto

# Python application using virtualenv
panel register --name flask-app --command "/home/user/projects/flask-app/venv/bin/python /home/user/projects/flask-app/app.py" --path "/home/user/projects/flask-app" --port 5000

# Python application with working directory
panel register --name django-app --command "/home/user/projects/django-app/venv/bin/python manage.py runserver 0.0.0.0:8000" --path "/home/user/projects/django-app"

# Java application with arguments
panel register --name spring-app --command "/usr/bin/java -jar /home/user/apps/myapp.jar --server.port=8080" --port 8080

# Applications needing environment variables
panel register --name env-app --command "/home/user/bin/app" --port 8050 --env DEBUG=1 --env LOG_LEVEL=info
```

### Managing Services

```bash
# List all services
panel list

# Start a service
panel start service-name

# Start a service and view its logs
panel start service-name --log

# Stop a service
panel stop service-name

# Restart a service
panel restart service-name

# Enable automatic startup and start the service
panel auto service-name

# Disable automatic startup
panel disable service-name

# View logs for a service
panel logs service-name

# Edit a service's configuration
panel edit service-name --command "new command" --path "new/path" --detect-port

# Unregister a service
panel unregister service-name
```

Tab completion is available for all service names after installing shell completion.

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
panel register --name my-service --command "/path/to/executable" --range web
```

### Backup, Restore, and Update

Control Panel provides commands to backup and restore your configuration, making it easy to migrate settings or recover from issues:

```bash
# Create a backup of your services configuration
panel backup
# The backup will be saved to ~/.config/control-panel/backups/

# Import configuration from a backup file
panel import_config /path/to/backup-file.json

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
panel <TAB>              # Lists all available commands
panel start <TAB>        # Lists all services
panel stop my-<TAB>      # Completes service names starting with "my-"
```

## Configuration

All service configurations are stored in `~/.config/control-panel/services.json`.

## Systemd Integration

Control Panel uses systemd to manage service startup. Each registered service gets a systemd user service that can be managed through the Control Panel interface.

### Auto-start Feature

Control Panel itself can auto-start at system boot. After installation:

1. The Control Panel web UI will automatically start when your system boots
2. All services marked with `--auto` will be started automatically
3. You can disable auto-start for individual services using `panel disable service-name`

## Handling Special Applications

### Node.js Applications

When working with Node.js applications, especially those using npm scripts, use the following approach:

```bash
# Using npm start
panel register --name app-name \
  --command "cd /path/to/app && /usr/bin/npm start" \
  --path "/path/to/app" \
  --port 3000 \
  --auto
```

The important parts are:
1. Include the `cd` command before the npm command to ensure npm runs in the correct directory
2. Use the full path to the npm executable (usually `/usr/bin/npm`)
3. Set the `--path` parameter to the application directory

### Python Applications with Virtual Environments

For Python applications using virtual environments:

```bash
# Using virtualenv
panel register --name flask-app \
  --command "/path/to/venv/bin/python /path/to/app.py" \
  --path "/path/to/app" \
  --port 5000
```

Do not use `source venv/bin/activate` in your command. Instead, directly use the Python executable inside the virtual environment.

## Port Detection

Control Panel can automatically detect the port being used by a service, even if the application chooses its own port:

1. For services that set their own port:
   ```bash
   # After registering, detect the actual port
   panel edit service-name --detect-port
   ```

2. This feature is particularly useful for applications like ComfyUI that have a fixed port (8188)

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

### Using with Virtual Environments

If your service uses a Python virtual environment, **do not** use `source venv/bin/activate` in your command. Instead, use the absolute path to the Python executable in the virtual environment:

```bash
# Instead of:
# source venv/bin/activate && python app.py

# Use:
panel register --name my-app --command "/path/to/venv/bin/python /path/to/app.py" --port 8000
```

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
