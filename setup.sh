#!/bin/bash

set -e

echo "Setting up Control Panel..."

# Create configuration directory
mkdir -p ~/.config/control-panel/env

# Initialize empty services configuration if it doesn't exist
if [ ! -f ~/.config/control-panel/services.json ]; then
    echo '{"services": {}, "port_ranges": {"default": {"start": 8000, "end": 9000}}}' > ~/.config/control-panel/services.json
    echo "Created default configuration file"
fi

# Create systemd user directory if it doesn't exist
mkdir -p ~/.config/systemd/user/

# Create service template directory if it doesn't exist
mkdir -p ./templates

# Create service template file
cat > ./templates/service-template.service << 'EOL'
[Unit]
Description=Control Panel managed service: %i
After=network.target

[Service]
Type=simple
EnvironmentFile=%h/.config/control-panel/env/%i.env
ExecStart=/bin/bash -c "${COMMAND}"
Restart=on-failure
WorkingDirectory=%h

[Install]
WantedBy=default.target
EOL

# Copy service template to systemd user directory
cp ./templates/service-template.service ~/.config/systemd/user/control-panel@.service

# Create requirements.txt if it doesn't exist
if [ ! -f requirements.txt ]; then
    cat > requirements.txt << 'EOL'
click==8.1.7
pyyaml==6.0.1
tabulate==0.9.0
flask==2.2.3
EOL
    echo "Created requirements.txt file"
fi

# Create global command script
INSTALL_PATH="/usr/local/bin/panel"
REPO_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing 'panel' command..."

# Create panel command launcher
cat > /tmp/panel << EOL
#!/bin/bash
# Control Panel command launcher
if [ "\$1" = "web" ]; then
    shift
    python3 "${REPO_PATH}/web_ui.py" "\$@"
else
    python3 "${REPO_PATH}/control.py" "\$@"
fi
EOL

# Install command with sudo
if sudo cp /tmp/panel "$INSTALL_PATH" && sudo chmod +x "$INSTALL_PATH"; then
    echo "✅ Installed 'panel' command successfully at $INSTALL_PATH"
    echo "   Usage: panel [command] [options]"
    echo "   For web UI: panel web"
else
    echo "❌ Failed to install 'panel' command. You may need sudo privileges."
    echo "   You can still use the control panel with ./control.py and ./web_ui.py"
fi

# Make scripts executable
chmod +x ./control.py
chmod +x ./web_ui.py
[ -f ./start.sh ] && chmod +x ./start.sh

# Reload systemd user configuration
systemctl --user daemon-reload

echo "Control Panel setup complete!"
echo "Use 'panel --help' to see available commands"
echo "Use 'panel web' to start the web interface"
