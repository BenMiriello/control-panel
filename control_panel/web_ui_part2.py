#!/usr/bin/env python3

import subprocess
from flask import request, jsonify, redirect, url_for, render_template

from control_panel.utils.config import load_config, save_config
from control_panel.utils.service import register_service, unregister_service, control_service

# Import Flask app from the main web_ui module
from control_panel.web_ui import app

@app.route('/services/add', methods=['GET', 'POST'])
def add_service():
    if request.method == 'POST':
        name = request.form.get('name')
        command = request.form.get('command')
        port = request.form.get('port')
        path = request.form.get('path', request.form.get('directory', ''))  # Support both names
        range_name = request.form.get('range', 'default')
        env_vars = request.form.get('env_vars', '').splitlines()
        auto_start = request.form.get('auto_start') == 'on'
        start_now = request.form.get('start_now') == 'on'
        
        if port:
            try:
                port = int(port)
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Port must be a number'})
        else:
            port = None
        
        success, result = register_service(name, command, port, path, range_name, env_vars)
        
        if not success:
            return jsonify({'status': 'error', 'message': result})
        
        # Handle auto-start if requested
        if auto_start:
            config = load_config()
            if name in config["services"]:
                config["services"][name]["enabled"] = True
                save_config(config)
                subprocess.run(["systemctl", "--user", "enable", f"control-panel@{name}.service"])
        
        # Start service immediately if requested
        if start_now or auto_start:  # Auto implies start
            control_service(name, "start")
        
        return redirect(url_for('index'))
    
    # GET request - show form
    config = load_config()
    port_ranges = config.get("port_ranges", {})
    return render_template('add_service.html', port_ranges=port_ranges)

@app.route('/services/delete/<n>')
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

@app.route('/logs/<n>')
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
