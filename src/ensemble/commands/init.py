"""Ensemble init command - Initialize a project for Ensemble."""

from pathlib import Path

import click


@click.command()
@click.option(
    "--full",
    is_flag=True,
    help="Copy all agent definitions to local project for customization.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing configuration files.",
)
@click.pass_context
def init(ctx: click.Context, full: bool, force: bool) -> None:
    """Initialize the current project for Ensemble.

    This command sets up the necessary directory structure and configuration
    files for using Ensemble in your project.

    Creates:
    - .ensemble/ directory with queue/ and status/ subdirectories
    - Adds Ensemble section to CLAUDE.md (creates if not exists)
    - Updates .gitignore to exclude queue files

    Use --full to copy all agent definitions locally for customization.
    """
    from ensemble.commands._init_impl import run_init

    run_init(full=full, force=force)
