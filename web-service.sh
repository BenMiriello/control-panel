#!/bin/bash

echo "Setting up Control Panel Web UI as a service..."

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Copy templates and static files
echo "Setting up template files..."
bash fix-templates.sh >/dev/null 2>&1

# Register the web UI as a service
echo "Registering web UI as a service..."
panel web --register

echo ""
echo "Web UI service setup complete!"
echo "You can view the web UI at http://localhost:9000"
echo "View logs with: panel logs control-panel-web"
echo "Restart with: panel restart control-panel-web"
