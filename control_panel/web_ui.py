#!/usr/bin/env python3

import os
import json
import time
import click
import subprocess
import webbrowser
import threading
import importlib.resources
import pkg_resources
import shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Try to use package-relative imports, but fall back to local imports if necessary
try:
    from control_panel.utils.config import load_config, save_config
    from control_panel.utils.service import register_service, unregister_service, get_service_status, control_service
    from control_panel.utils.system_metrics import get_all_metrics
    # We're running as an installed package
    PACKAGE_MODE = True
except ImportError:
    # We're running from the local directory
    from utils.config import load_config, save_config
    from utils.service import register_service, unregister_service, get_service_status, control_service
    from utils.system_metrics import get_all_metrics
    PACKAGE_MODE = False

# Handle template and static paths correctly whether running from package or local directory
def create_app():
    """Create and configure the Flask app"""
    if PACKAGE_MODE:
        # In package mode, we need to locate the templates and static files within the package
        try:
            # First try to find the templates and static folders at repo root
            template_dir = Path(__file__).resolve().parent.parent / 'templates' / 'web'
            static_dir = Path(__file__).resolve().parent.parent / 'static'
            
            # If they exist at repo root, copy them to the package directory
            if template_dir.exists() and static_dir.exists():
                package_template_dir = Path(__file__).resolve().parent / 'templates' / 'web'
                package_static_dir = Path(__file__).resolve().parent / 'static'
                
                # Create target directories if they don't exist
                package_template_dir.parent.mkdir(exist_ok=True)
                package_template_dir.mkdir(exist_ok=True)
                package_static_dir.mkdir(exist_ok=True)
                package_static_dir.joinpath('css').mkdir(exist_ok=True)
                package_static_dir.joinpath('js').mkdir(exist_ok=True)
                
                # Copy all files from repo templates to package templates
                for template_file in template_dir.glob('*.html'):
                    shutil.copy2(template_file, package_template_dir)
                
                # Copy CSS files
                for css_file in (static_dir / 'css').glob('*.css'):
                    shutil.copy2(css_file, package_static_dir / 'css')
                
                # Copy JS files
                for js_file in (static_dir / 'js').glob('*.js'):
                    shutil.copy2(js_file, package_static_dir / 'js')
                
                template_folder = str(package_template_dir)
                static_folder = str(package_static_dir)
                print(f"Copied templates to {template_folder}")
                print(f"Copied static files to {static_folder}")
            else:
                # Use package directories
                template_folder = str(Path(__file__).resolve().parent / 'templates' / 'web')
                static_folder = str(Path(__file__).resolve().parent / 'static')
                
            if not os.path.exists(template_folder):
                template_folder = str(Path.cwd() / 'templates' / 'web')
                static_folder = str(Path.cwd() / 'static')
                print(f"Using templates from current directory: {template_folder}")
                
            app = Flask(__name__, 
                       template_folder=template_folder,
                       static_folder=static_folder)
        except Exception as e:
            # If all else fails, use the template and static folders relative to the current directory
            template_folder = str(Path.cwd() / 'templates' / 'web')
            static_folder = str(Path.cwd() / 'static')
            app = Flask(__name__, 
                       template_folder=template_folder,
                       static_folder=static_folder)
            print(f"Warning: Using templates and static files from current directory due to error: {e}")
    else:
        # In local mode, we need to use the local file paths
        template_folder = str(Path(__file__).resolve().parent.parent / 'templates' / 'web')
        static_folder = str(Path(__file__).resolve().parent.parent / 'static')
        app = Flask(__name__, 
                   template_folder=template_folder,
                   static_folder=static_folder)
    
    return app

app = create_app()

@app.route('/')
def index():
    config = load_config()
    services = []
    
    for name, service in config["services"].items():
        status, enabled = get_service_status(name)
        services.append({
            'name': name,
            'port': service['port'],
            'command': service['command'],
            'status': status,
            'enabled': enabled
        })
    
    # Sort by name
    services.sort(key=lambda x: x['name'])
    
    # Get port ranges
    port_ranges = config.get("port_ranges", {})
    
    return render_template('index.html', services=services, port_ranges=port_ranges)

@app.route('/api/metrics')
def get_metrics():
    """API endpoint to get current system metrics"""
    return jsonify(get_all_metrics())

@app.route('/services/control/<n>/<action>')
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

def start_web_ui(host='0.0.0.0', port=9000, debug=False, open_browser=True):
    """Start the web UI"""
    if open_browser:
        # Open browser in a separate thread after a delay
        def open_browser_delayed():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{port}')
        
        threading.Thread(target=open_browser_delayed).start()
    
    print(f"Starting Control Panel web UI at http://{host}:{port}")
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    app.run(host=host, port=port, debug=debug)

@click.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=9000, type=int, help='Port to listen on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
def main(host, port, no_browser):
    """Start the web UI for Control Panel"""
    start_web_ui(host=host, port=port, debug=False, open_browser=not no_browser)

if __name__ == '__main__':
    main()
