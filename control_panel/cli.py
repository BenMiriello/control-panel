
@cli.command()
@click.option('--force', is_flag=True, help='Update even if no repository is found')
@click.option('--version', help='Specific branch, tag, or commit SHA to checkout')
def update(force, version):
    """Update the Control Panel software"""
    repo_dir = Path(__file__).resolve().parent.parent
    git_dir = repo_dir / ".git"
    
    if not git_dir.exists() and not force:
        click.echo("Error: Could not find repository. Are you running from an installed version?")
        click.echo("If you want to update anyway, use --force")
        return
    
    if git_dir.exists():
        # Update repository
        click.echo("Updating from repository...")
        try:
            original_dir = os.getcwd()
            os.chdir(repo_dir)
            
            if version:
                # Fetch all and checkout specific version
                click.echo(f"Fetching updates and checking out {version}...")
                subprocess.run(["git", "fetch", "--all"], check=True)
                subprocess.run(["git", "checkout", version], check=True)
            else:
                # Pull latest from master/main branch
                click.echo("Pulling latest changes from master/main branch...")
                
                # Determine if main or master is used
                result = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True)
                if "origin/main" in result.stdout:
                    default_branch = "main"
                else:
                    default_branch = "master"
                
                click.echo(f"Using {default_branch} as default branch")
                subprocess.run(["git", "checkout", default_branch], check=True)
                subprocess.run(["git", "pull", "origin", default_branch], check=True)
            
            os.chdir(original_dir)
        except Exception as e:
            click.echo(f"Error during git update: {e}")
            return
    
    # Run the install script if it exists
    install_script = repo_dir / "install.sh"
    if install_script.exists():
        click.echo("Running install script...")
        try:
            subprocess.run(["bash", str(install_script)], check=True)
        except Exception as e:
            click.echo(f"Error during installation: {e}")
            return
    else:
        # Fallback to reinstalling package
        click.echo("Reinstalling package...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repo_dir)], check=True)
        except Exception as e:
            click.echo(f"Error during package installation: {e}")
            return
    
    click.echo("Control Panel updated successfully!")
