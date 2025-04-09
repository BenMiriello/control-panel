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
EOL
    echo "Created requirements.txt file"
fi

# Make scripts executable
chmod +x ./control.py

# Reload systemd user configuration
systemctl --user daemon-reload

echo "Control Panel setup complete!"
echo "Use './control.py --help' to see available commands"
echo "You can now register and manage your services"
