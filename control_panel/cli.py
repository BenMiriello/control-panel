# Find and modify the backup command in the file
def backup(output):
    """Backup all Control Panel configuration"""
    # Create backup directory if it doesn't exist
    backup_dir = CONFIG_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Default output location
    if not output:
        timestamp = subprocess.check_output(["date", "+%Y%m%d-%H%M%S"]).decode().strip()
        output = backup_dir / f"control-panel-backup-{timestamp}.json"
    
    # Load configuration
    config = load_config()
    
    # Write to backup file
    with open(output, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"Configuration backed up to {output}")
    click.echo(f"To restore: panel import_config {output}")
