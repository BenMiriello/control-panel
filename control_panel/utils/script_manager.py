#!/usr/bin/env python3

import stat
from pathlib import Path
from datetime import datetime
from .config import load_config, save_config

SCRIPT_TEMPLATE = """#!/bin/bash
# Control Panel Service Script
# Service: {service_name}
# Port: {port}
# Generated: {timestamp}

cd "{working_dir}"
export PORT="{port}"
{env_vars}
{command}
"""

def create_run_script(service_name, service_config, project_dir):
    """Create a run_panel.sh script for a service"""
    if not project_dir:
        return False, "No project directory specified"
    
    project_path = Path(project_dir)
    if not project_path.exists():
        return False, f"Project directory does not exist: {project_dir}"
    
    script_path = project_path / "run_panel.sh"
    
    # Prepare environment variables
    env_vars = ""
    for key, value in service_config.get("env", {}).items():
        if key != "PORT":  # PORT is already handled separately
            env_vars += f'export {key}="{value}"\n'
    
    # Generate script content
    script_content = SCRIPT_TEMPLATE.format(
        service_name=service_name,
        port=service_config["port"],
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        working_dir=service_config.get("working_dir", str(Path.home())),
        env_vars=env_vars,
        command=service_config["command"]
    )
    
    try:
        # Write the script
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make it executable
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        
        return True, str(script_path)
    except Exception as e:
        return False, f"Failed to create script: {str(e)}"

def read_run_script(project_dir):
    """Read the contents of a run_panel.sh script"""
    if not project_dir:
        return None, "No project directory specified"
    
    script_path = Path(project_dir) / "run_panel.sh"
    if not script_path.exists():
        return None, f"Script not found: {script_path}"
    
    try:
        with open(script_path, 'r') as f:
            return f.read(), None
    except Exception as e:
        return None, f"Failed to read script: {str(e)}"

def script_is_newer(project_dir, service_config):
    """Check if run_panel.sh is newer than the service config"""
    if not project_dir:
        return False
    
    script_path = Path(project_dir) / "run_panel.sh"
    if not script_path.exists():
        return False
    
    # For now, we'll always consider the script authoritative if it exists
    # In the future, we could add timestamp tracking
    return True

def extract_command_from_script(script_content):
    """Extract the actual command from a run_panel.sh script"""
    lines = script_content.strip().split('\n')
    
    # Look for the last non-comment, non-export line
    for line in reversed(lines):
        line = line.strip()
        if (line and 
            not line.startswith('#') and 
            not line.startswith('export ') and
            not line.startswith('cd ')):
            return line
    
    return None

def sync_script_to_config(service_name, project_dir):
    """Sync run_panel.sh content back to services.json"""
    script_content, error = read_run_script(project_dir)
    if error:
        return False, error
    
    command = extract_command_from_script(script_content)
    if not command:
        return False, "Could not extract command from script"
    
    # Update the config
    config = load_config()
    if service_name not in config["services"]:
        return False, f"Service '{service_name}' not found in config"
    
    config["services"][service_name]["command"] = command
    save_config(config)
    
    return True, f"Synced command from script: {command}"

def get_effective_command(service_name, service_config):
    """Get the effective command for a service, checking script first"""
    project_dir = service_config.get("project_dir")
    
    if project_dir and script_is_newer(project_dir, service_config):
        script_content, error = read_run_script(project_dir)
        if not error:
            command = extract_command_from_script(script_content)
            if command:
                # Sync back to config for backup
                config = load_config()
                config["services"][service_name]["command"] = command
                save_config(config)
                return command
    
    # Fallback to config command
    return service_config["command"]