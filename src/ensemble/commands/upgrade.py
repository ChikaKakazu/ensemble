"""Ensemble upgrade command - Update files to latest version."""

import click

from ensemble.commands._upgrade_impl import run_upgrade


@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes.")
@click.option("--force", is_flag=True, help="Force update all files, creating backups of modified files.")
@click.option("--diff", is_flag=True, help="Show diff of changes before applying.")
def upgrade(dry_run: bool, force: bool, diff: bool) -> None:
    """Upgrade Ensemble files to the latest version.

    This command updates agent definitions, commands, and other Ensemble files
    to match the latest version. It intelligently handles user modifications:

    - New files are copied automatically
    - Unmodified files are updated safely
    - Modified files are skipped (unless --force is used)
    - With --force, backups are created before overwriting modified files

    Examples:
        ensemble upgrade              # Safe upgrade, skip modified files
        ensemble upgrade --dry-run    # Preview changes without applying
        ensemble upgrade --force      # Force update all, create backups
        ensemble upgrade --diff       # Show detailed diff before applying
    """
    run_upgrade(dry_run=dry_run, force=force, diff=diff)
