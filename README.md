# Control Panel

A simple service manager for Linux to make it easy to run and manage multiple applications from one place.

## But Why?

Instead of juggling multiple terminal windows or remembering different startup commands, register all your services once and then start/stop them with simple commands. Panel centralizes port allocation, allows auto-start and other helpful abstractions. Manage everything through the cli tool and built-in web UI.

## Installation

### Direct install
```bash
pip install git+https://github.com/BenMiriello/control-panel.git
```

### Development install
```bash
git clone https://github.com/BenMiriello/control-panel.git
cd control-panel
./install.sh
```

## Quick start

```bash
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
panel register <name> --command "..." [--port N] [--path /dir] [--auto]
panel start/stop/restart <name>
panel list                    # See all services and their status
panel logs <name>             # View service logs
panel unregister <name>       # Remove a service
panel web                     # Start web interface
panel completion --install   # Set up tab completion
```

### Tab Completion

Enable tab completion for service names and commands:

```bash
# Auto-detect your shell and install
panel completion --install

# Or specify your shell
panel completion --install --shell zsh
panel completion --install --shell bash
panel completion --install --shell fish

# Test if completion is working
panel completion --test

# Remove completion
panel completion --uninstall
```

After installation, restart your shell or run `source ~/.zshrc` (or `~/.bashrc` for bash).

## Web interface

Run `panel web` and visit `http://localhost:9000` to manage everything through a browser. The web interface shows service status, lets you start/stop services, view logs, and add new services.

For remote access: `panel web --host 0.0.0.0`

## Installation notes

The installer sets up:
- The `panel` command globally
- Shell completion (tab to complete service names)
- Systemd integration for auto-startup
- Configuration in `~/.config/control-panel/`

## Tips

### Process and Environment:
- Use absolute paths for executables - systemd has a minimal PATH
- Set working directory with --dir if your app expects to run from its own folder
- Apps that need environment variables should get them explicitly, not from your shell profile
- Services that fork/daemonize themselves can confuse systemd - use foreground mode
- If your app creates files, make sure the service user has write permissions

### Network and Ports:
- If using auto-port assignment, read the PORT env var in your app
- Check if your app has built-in port configuration that conflicts with Control Panel

## Debugging:
- `start` and `restart` commands may succeed initially but still fail after.
- Use panel logs service-name for detailed debugging info.
- Test commands manually first: cd /app/dir && /full/path/to/command


## Requirements

- Linux with systemd
- Python 3.8+
- Your applications should bind to `0.0.0.0:$PORT` for best compatibility

---

Simplify service management and get back to building.
