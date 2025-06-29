# Control Panel

A simple service manager for Linux that makes it easy to run and manage multiple applications from one place.

## What it does

Instead of juggling multiple terminal windows or remembering different startup commands, Control Panel lets you register all your services once and then start/stop them with simple commands. It handles ports, auto-startup, and gives you both a CLI and web interface.

## Quick start

```bash
git clone https://github.com/BenMiriello/control-panel.git
cd control-panel
./install.sh

# Register a service
panel add my-app --command "/path/to/your/app" --port 8080

# Start it
panel start my-app

# See all services
panel list

# Open web interface
panel web
```

## Common use cases

```bash
# Node.js app
panel add my-api --command "node server.js" --dir /path/to/app --port 3000 --auto

# Python app with virtualenv
panel add flask-app --command "/path/to/venv/bin/python app.py" --port 5000

# Any executable
panel add my-service --command "/usr/local/bin/myservice --port 8080" --auto
```

## Features

- **Simple CLI**: One command to rule them all
- **Web interface**: Point-and-click management at `localhost:9000`
- **Auto-startup**: Services start when your system boots
- **Port management**: Automatic port assignment and conflict detection
- **Real-time logs**: `panel logs service-name`
- **Systemd integration**: Uses your system's service manager under the hood

## All commands

```bash
panel add <name> --command "..." [--port N] [--dir /path] [--auto]
panel start/stop/restart <name>
panel list                    # See all services and their status
panel logs <name>             # View service logs
panel remove <name>           # Unregister a service
panel web                     # Start web interface
```

## Web interface

Run `panel web` and visit `http://localhost:9000` to manage everything through a browser. The web interface shows service status, lets you start/stop services, view logs, and add new services.

For remote access: `panel web --host 0.0.0.0`

## Installation notes

The installer sets up:
- The `panel` command globally
- Shell completion (tab to complete service names)
- Systemd integration for auto-startup
- Configuration in `~/.config/control-panel/`

## Common gotchas

- Use full paths for commands: `/usr/bin/node app.js` not just `node app.js`
- For Python virtualenvs: use `/path/to/venv/bin/python` directly
- For Node apps with npm: `"cd /path && npm start"` works better than npm scripts
- Services need to respect the `PORT` environment variable if you want auto-port assignment

## Requirements

- Linux with systemd
- Python 3.8+
- Your applications should bind to `0.0.0.0:$PORT` for best compatibility

---

Built for developers who want to stop thinking about service management and get back to building.
