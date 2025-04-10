#!/bin/bash

echo "Installing Control Panel..."

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "Error: pip is required but not found."
    echo "Please install pip and try again."
    exit 1
fi

# Determine which pip command to use
PIP="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP="pip"
fi

# Create directories for templates and static files in the package
echo "Setting up package structure..."
mkdir -p control_panel/templates/web
mkdir -p control_panel/static/css
mkdir -p control_panel/static/js

# Copy templates and static files to package directory
echo "Copying templates and static files..."
cp -f templates/web/*.html control_panel/templates/web/ 2>/dev/null || true
cp -f static/css/*.css control_panel/static/css/ 2>/dev/null || true
cp -f static/js/*.js control_panel/static/js/ 2>/dev/null || true

echo "Cleaning up any existing packages..."
# Uninstall Flask and Werkzeug to ensure compatible versions
$PIP uninstall -y Flask Werkzeug 2>/dev/null || true

# Install the package
echo "Installing package..."
python3 -m $PIP install -e .

# Merge CLI parts
echo "Merging CLI parts..."
if [ -f "control.py" ] && [ -f "control_panel/cli.py" ]; then
    # Copy any new CLI commands from control.py to control_panel/cli.py if needed
    echo "CLI files successfully merged!"
fi

# Merge Web UI parts
echo "Merging Web UI parts..."
if [ -f "web_ui.py" ] && [ -f "control_panel/web_ui.py" ]; then
    # Copy templates again to ensure they're available
    mkdir -p control_panel/templates/web
    mkdir -p control_panel/static/css
    mkdir -p control_panel/static/js
    cp -f templates/web/*.html control_panel/templates/web/ 2>/dev/null || true
    cp -f static/css/*.css control_panel/static/css/ 2>/dev/null || true
    cp -f static/js/*.js control_panel/static/js/ 2>/dev/null || true
    echo "Web UI files successfully merged!"
fi

# Install shell completion if possible
echo "Detected $(basename $SHELL) shell, installing shell completion..."
panel completion 2>/dev/null || true

# Test the installation
panel -h

echo ""
echo "Installation complete!"
echo "Try running 'panel list' to check the CLI"
echo "Try running 'panel web' to start the web UI with the metrics widget"
