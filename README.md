# Control Panel

A central management system for services, ports, and startup configurations on Linux.

## Overview

This tool helps you manage multiple services running on your Linux machine with features for:

- Centralized port management
- Automatic service startup via systemd
- Service registration and configuration
- Simple CLI interface to control all services

## Quick Start

```bash
# Clone the repository
git clone https://github.com/BenMiriello/control-panel.git
cd control-panel

# Install dependencies
pip install -r requirements.txt

# Setup the control panel
sudo ./setup.sh

# Register a new service
./control.py register --name my-service --command '/path/to/service' --port 8080

# List all services
./control.py list

# Start a service
./control.py start my-service
```

## Features

- Central configuration file for all services
- Automatic port assignment and management
- Systemd integration for service auto-start
- Live log viewing
- Service status monitoring

## Configuration

All service configurations are stored in `~/.config/control-panel/services.json`.
