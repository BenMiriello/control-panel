#!/bin/bash

echo "Fixing template files for control-panel..."

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Create directories for templates and static files in the package
echo "Creating package directories..."
mkdir -p control_panel/templates/web
mkdir -p control_panel/static/css
mkdir -p control_panel/static/js

# Copy templates and static files to package directory
echo "Copying templates and static files..."
cp -f templates/web/*.html control_panel/templates/web/ 2>/dev/null || true
cp -f static/css/*.css control_panel/static/css/ 2>/dev/null || true
cp -f static/js/*.js control_panel/static/js/ 2>/dev/null || true

echo "Template files have been copied to the package directories."
echo "You can now run 'panel web' to start the web UI."
