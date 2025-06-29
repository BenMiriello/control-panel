#!/usr/bin/env python3

import click
import json
import subprocess
from pathlib import Path

# Import from package-relative paths
try:
    from control_panel.utils.config import load_config, save_config
except ImportError:
    # Fallback to local imports if package is not fully installed
    from utils.config import load_config, save_config

@click.command()
@click.argument('range_name')
@click.argument('start', type=int)
@click.argument('end', type=int)
def add_range(range_name, start, end):
    """Add a new port range"""
    if end <= start:
        click.echo("Error: End port must be greater than start port")
        return
    
    config = load_config()
    config["port_ranges"][range_name] = {"start": start, "end": end}
    save_config(config)
    
    click.echo(f"Port range '{range_name}' added: {start}-{end}")

@click.command()
@click.argument('backup_file')
def restore(backup_file):
    """Restore configuration from a backup file"""
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"Error reading backup file: {e}")
        return
    
    # Validate backup structure
    if not isinstance(backup_data, dict) or "services" not in backup_data:
        click.echo("Invalid backup file format")
        return
    
    # Create backup of current config
    config = load_config()
    timestamp = subprocess.check_output(["date", "+%Y%m%d-%H%M%S"]).decode().strip()
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"control-panel-backup-{timestamp}.json"
    
    with open(backup_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"Current configuration backed up to {backup_path}")
    
    # Restore from backup
    save_config(backup_data)
    click.echo(f"Configuration restored from {backup_file}")

@click.command()
@click.option('--output', '-o', help='Backup file path (default: control-panel-backup-TIMESTAMP.json)')
def backup(output):
    """Create a backup of the current configuration"""
    config = load_config()
    
    if not output:
        timestamp = subprocess.check_output(["date", "+%Y%m%d-%H%M%S"]).decode().strip()
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        output = backup_dir / f"control-panel-backup-{timestamp}.json"
    
    with open(output, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"Configuration backed up to {output}")

@click.command()
@click.argument('config_file')
def import_config(config_file):
    """Import services from another configuration file"""
    try:
        with open(config_file, 'r') as f:
            import_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"Error reading configuration file: {e}")
        return
    
    # Validate import structure
    if not isinstance(import_data, dict) or "services" not in import_data:
        click.echo("Invalid configuration file format")
        return
    
    config = load_config()
    imported_count = 0
    
    # Import services that don't already exist
    for service_name, service_config in import_data["services"].items():
        if service_name not in config["services"]:
            config["services"][service_name] = service_config
            imported_count += 1
            click.echo(f"Imported service: {service_name}")
        else:
            click.echo(f"Skipped existing service: {service_name}")
    
    # Import port ranges that don't already exist
    if "port_ranges" in import_data:
        for range_name, range_config in import_data["port_ranges"].items():
            if range_name not in config["port_ranges"]:
                config["port_ranges"][range_name] = range_config
                click.echo(f"Imported port range: {range_name}")
            else:
                click.echo(f"Skipped existing port range: {range_name}")
    
    save_config(config)
    click.echo(f"Import completed. {imported_count} services imported.")