#!/bin/bash

# Stop any running services
echo "Stopping any running panel-related services..."
panel list 2>/dev/null | grep -E 'running|active' | awk '{print $1}' | xargs -I{} panel stop {}

# Uninstall the current package
echo "Uninstalling current package..."
pip uninstall -y control-panel

# Clean up any leftover files
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
find . -name "*.egg-info" -type d -exec rm -rf {} +
rm -rf build dist

# Install the package in development mode with the copy_files command
echo "Installing package..."
python setup.py copy_files develop

echo ""
echo "Installation complete!"
echo "Try running 'panel list' to check the CLI"
echo "Try running 'panel-web' to start the web UI"
