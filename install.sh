#!/bin/bash

set -e

echo "Installing Control Panel..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Uninstall problematic packages first
echo "Cleaning up any existing packages..."
pip uninstall -y flask werkzeug || true

# Install the package in development mode
echo "Installing package..."
pip install -e .

# Merge CLI parts and Web UI parts if they exist
if [ -f "control_panel/cli_part2.py" ] || [ -f "control_panel/cli_part3.py" ]; then
    echo "Merging CLI parts..."
    python -m control_panel.merge_cli_parts
fi

if [ -f "control_panel/web_ui_part2.py" ] || [ -f "control_panel/web_ui_part3.py" ]; then
    echo "Merging Web UI parts..."
    python -m control_panel.merge_web_ui_parts
fi

# Create configuration directory
mkdir -p ~/.config/control-panel/env

# Initialize empty services configuration if it doesn't exist
if [ ! -f ~/.config/control-panel/services.json ]; then
    echo '{"services": {}, "port_ranges": {"default": {"start": 8000, "end": 9000}}}' > ~/.config/control-panel/services.json
    echo "Created default configuration file"
fi

# Create systemd user directory if it doesn't exist
mkdir -p ~/.config/systemd/user/

# Copy service template to systemd user directory
cp ./control_panel/templates/service-template.service ~/.config/systemd/user/control-panel@.service

# Create Control Panel service for auto-start
cat > ~/.config/systemd/user/control-panel.service << EOL
[Unit]
Description=Control Panel Web UI
After=network.target

[Service]
Type=simple
ExecStart=${HOME}/.local/bin/panel web --background
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOL

# Reload systemd user configuration
systemctl --user daemon-reload

# Enable the Control Panel service for auto-start
systemctl --user enable control-panel.service

# Detect shell and install shell completion
SHELL_TYPE=""
if [ -n "$BASH_VERSION" ]; then
    SHELL_TYPE="bash"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_TYPE="zsh"
elif [ -n "$FISH_VERSION" ]; then
    SHELL_TYPE="fish"
fi

if [ -n "$SHELL_TYPE" ]; then
    echo "Detected $SHELL_TYPE shell, installing shell completion..."
    panel completion --shell $SHELL_TYPE
    
    echo "Shell completion installed. To enable it immediately, run:"
    case $SHELL_TYPE in
        bash)
            echo "  source ~/.bash_completion"
            ;;
        zsh)
            echo "  source ~/.zshrc"
            ;;
        fish)
            echo "  source ~/.config/fish/completions/panel.fish"
            ;;
    esac
else
    echo "Could not detect shell type. To install shell completion manually, run:"
    echo "  panel completion"
fi

echo "Control Panel installation complete!"
echo ""
echo "Control Panel will now auto-start at system boot."
echo "To start the Control Panel web interface immediately, run:"
echo "  systemctl --user start control-panel.service"
echo ""
echo "You can now use the 'panel' command to manage your services:"
echo "  panel list                    - List all services"
echo "  panel register --help         - Get help with registering a service"
echo "  panel web                     - Start the web UI in foreground mode"
echo ""
echo "Example - register a Node.js service:"
echo "  panel register --name node-app --command 'cd /path/to/app && /usr/bin/npm start' --path /path/to/app --auto"
echo ""
echo "To uninstall Control Panel:"
echo "  panel uninstall"
echo ""
