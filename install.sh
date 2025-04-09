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

# Reload systemd user configuration
systemctl --user daemon-reload

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
    panel install_completion --shell $SHELL_TYPE
    
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
    echo "  panel install_completion"
fi

echo "Control Panel installation complete!"
echo ""
echo "You can now use the 'panel' command to manage your services:"
echo "  panel list                    - List all services"
echo "  panel register --help         - Get help with registering a service"
echo "  panel web                     - Start the web UI"
echo ""
echo "Example - register a service:"
echo "  panel register --name my-service --command '/path/to/start-script.sh' --port 8080"
echo ""
