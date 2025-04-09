#!/usr/bin/env python3

import os
import json
import time
import click
import subprocess
import webbrowser
import argparse
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for

from control_panel.utils.config import load_config, save_config, create_env_file
from control_panel.utils.service import register_service, unregister_service, get_service_status, control_service

# Get the package directory
PACKAGE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, 
           template_folder=str(PACKAGE_DIR / 'templates' / 'web'),
           static_folder=str(PACKAGE_DIR / 'static'))

@app.route('/')
def index():
    config = load_config()
    services = []
    
    for name, service in config["services"].items():
        try:
            status, enabled = get_service_status(name)
            services.append({
                'name': name,
                'port': service['port'],
                'command': service['command'],
                'status': status,
                'enabled': enabled
            })
        except Exception as e:
            # Handle errors gracefully
            services.append({
                'name': name,
                'port': service['port'],
                'command': service['command'],
                'status': 'error',
                'enabled': False
            })
    
    # Sort by name
    services.sort(key=lambda x: x['name'])
    
    # Get port ranges
    port_ranges = config.get("port_ranges", {})
    
    return render_template('index.html', services=services, port_ranges=port_ranges)

@app.route('/services/control/<name>/<action>')
def service_control(name, action):
    if action in ['start', 'stop', 'restart']:
        success, error = control_service(name, action)
        if not success:
            return jsonify({'status': 'error', 'message': error})
    elif action == 'enable':
        config = load_config()
        if name not in config["services"]:
            return jsonify({'status': 'error', 'message': f"Service '{name}' not found"})
        
        subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
        config["services"][name]["enabled"] = True
        save_config(config)
    elif action == 'disable':
        config = load_config()
        if name not in config["services"]:
            return jsonify({'status': 'error', 'message': f"Service '{name}' not found"})
        
        subprocess.run(["systemctl", "--user", "disable", f"control-panel@{name}.service"])
        config["services"][name]["enabled"] = False
        save_config(config)
    else:
        return jsonify({'status': 'error', 'message': f"Unknown action: {action}"})
    
    return redirect(url_for('index'))

@app.route('/services/edit/<name>', methods=['GET', 'POST'])
def edit_service(name):
    config = load_config()
    
    if name not in config["services"]:
        return jsonify({'status': 'error', 'message': f"Service '{name}' not found"})
    
    service = config["services"][name]
    
    if request.method == 'POST':
        # Get form data
        command = request.form.get('command')
        port = request.form.get('port')
        directory = request.form.get('directory', '')
        env_vars = request.form.get('env_vars', '').splitlines()
        
        # Try to detect port if not provided
        if not port and request.form.get('detect_port', False):
            try:
                # Get process ID
                result = subprocess.run(
                    ["systemctl", "--user", "show", f"control-panel@{name}.service", "-p", "MainPID", "--value"],
                    capture_output=True, text=True, check=True
                )
                pid = result.stdout.strip()
                
                if pid and pid != "0":
                    # Get listening ports for this PID
                    result = subprocess.run(
                        ["lsof", "-i", "-P", "-n", "-a", "-p", pid],
                        capture_output=True, text=True
                    )
                    
                    # Parse output to find listening port
                    for line in result.stdout.splitlines():
                        if "LISTEN" in line:
                            parts = line.split()
                            if len(parts) >= 9:
                                addr_port = parts[8].split(":")
                                if len(addr_port) >= 2:
                                    port = int(addr_port[-1])
            except Exception as e:
                print(f"Error detecting port: {e}")
        else:
            try:
                port = int(port) if port else service["port"]
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Port must be a number'})
        
        # Update service configuration
        service["command"] = command
        service["port"] = port
        service["working_dir"] = directory
        
        # Process environment variables
        service_env = {}
        for env_var in env_vars:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                service_env[key] = value
        
        # Always add PORT to environment
        service_env["PORT"] = str(port)
        service["env"] = service_env
        
        # Save updated configuration
        save_config(config)
        
        # Update environment file
        create_env_file(name, service)
        
        # Restart service if it was already running
        status, _ = get_service_status(name)
        if status == 'active':
            control_service(name, 'restart')
        
        return redirect(url_for('index'))
    
    # GET request - show form
    return render_template('edit_service.html', service=service)

@app.route('/services/add', methods=['GET', 'POST'])
def add_service():
    if request.method == 'POST':
        name = request.form.get('name')
        command = request.form.get('command')
        port = request.form.get('port')
        directory = request.form.get('directory', '')
        range_name = request.form.get('range', 'default')
        env_vars = request.form.get('env_vars', '').splitlines()
        
        if port:
            try:
                port = int(port)
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Port must be a number'})
        else:
            port = None
        
        success, result = register_service(name, command, port, directory, range_name, env_vars)
        
        if not success:
            return jsonify({'status': 'error', 'message': result})
        
        return redirect(url_for('index'))
    
    # GET request - show form
    config = load_config()
    port_ranges = config.get("port_ranges", {})
    return render_template('add_service.html', port_ranges=port_ranges)

@app.route('/services/delete/<name>')
def delete_service(name):
    success, error = unregister_service(name)
    if not success:
        return jsonify({'status': 'error', 'message': error})
    
    return redirect(url_for('index'))

@app.route('/ranges/add', methods=['GET', 'POST'])
def add_range():
    if request.method == 'POST':
        range_name = request.form.get('name')
        start = request.form.get('start')
        end = request.form.get('end')
        
        try:
            start = int(start)
            end = int(end)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Start and end must be numbers'})
        
        if end <= start:
            return jsonify({'status': 'error', 'message': 'End port must be greater than start port'})
        
        config = load_config()
        config["port_ranges"][range_name] = {"start": start, "end": end}
        save_config(config)
        
        return redirect(url_for('index'))
    
    # GET request - show form
    return render_template('add_range.html')

@app.route('/logs/<name>')
def view_logs(name):
    config = load_config()
    
    if name not in config["services"]:
        return jsonify({'status': 'error', 'message': f"Service '{name}' not found"})
    
    # Get recent logs
    result = subprocess.run(
        ["journalctl", "--user", "-n", "100", "-u", f"control-panel@{name}.service"],
        capture_output=True, text=True
    )
    
    logs = result.stdout
    
    return render_template('logs.html', name=name, logs=logs)

def start_web_ui(host='127.0.0.1', port=9000, debug=False, open_browser=True):
    """Start the web UI"""
    if open_browser:
        # Open browser in a separate thread after a delay
        def open_browser_delayed():
            time.sleep(1)
            webbrowser.open(f'http://{host}:{port}')
        
        import threading
        threading.Thread(target=open_browser_delayed).start()
    
    app.run(host=host, port=port, debug=debug)

def parse_args():
    parser = argparse.ArgumentParser(description='Control Panel Web UI')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=9000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    start_web_ui(host=args.host, port=args.port, debug=args.debug, open_browser=not args.no_browser)
