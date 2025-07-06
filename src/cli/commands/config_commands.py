#!/usr/bin/env python3

# Command group metadata
__group__ = "Configuration"

import json
from pathlib import Path
import subprocess

import click

# Import from core business logic
from core.config import load_config, save_config


@click.command()
@click.argument("backup_file")
def restore(backup_file):
    """Restore configuration from a backup file"""
    try:
        with open(backup_file) as f:
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

    with open(backup_path, "w") as f:
        json.dump(config, f, indent=2)

    click.echo(f"Current configuration backed up to {backup_path}")

    # Restore from backup
    save_config(backup_data)
    click.echo(f"Configuration restored from {backup_file}")
