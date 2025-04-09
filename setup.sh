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

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    deactivate
    echo "Virtual environment created and dependencies installed"
else
    echo "Virtual environment already exists"
    source .venv/bin/activate
    pip install -r requirements.txt
    deactivate
fi

# Make scripts executable
chmod +x ./control.py
chmod +x ./web_ui.py
chmod +x ./start.sh

# Create a global command
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

# Create panel command
cat > "$INSTALL_DIR/panel" << EOL
#!/bin/bash
CONTROL_PANEL_DIR="$(pwd)"
source "$CONTROL_PANEL_DIR/.venv/bin/activate"
"$CONTROL_PANEL_DIR/control.py" "\$@"
deactivate
EOL

chmod +x "$INSTALL_DIR/panel"

# Create panel-ui command
cat > "$INSTALL_DIR/panel-ui" << EOL
#!/bin/bash
CONTROL_PANEL_DIR="$(pwd)"
source "$CONTROL_PANEL_DIR/.venv/bin/activate"
"$CONTROL_PANEL_DIR/web_ui.py" "\$@"
deactivate
EOL

chmod +x "$INSTALL_DIR/panel-ui"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "NOTE: $HOME/.local/bin is not in your PATH."
    echo "Add the following line to your shell profile (.bashrc, .zshrc, etc.):"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
    echo ""
    echo "Then run: source ~/.bashrc (or source ~/.zshrc)"
fi

# Reload systemd user configuration
systemctl --user daemon-reload

echo "Control Panel setup complete!"
echo "Use 'panel --help' to see available commands"
echo "Use 'panel-ui' to start the web interface"
echo "You can now register and manage your services"
