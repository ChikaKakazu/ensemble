"""Ensemble CLI - AI Orchestration Tool for Claude Code."""

import click

from ensemble import __version__
from ensemble.commands.init import init
from ensemble.commands.issue import issue
from ensemble.commands.launch import launch


@click.group()
@click.version_option(version=__version__, prog_name="ensemble")
def cli() -> None:
    """Ensemble - AI Orchestration Tool for Claude Code.

    Ensemble provides multi-agent orchestration for complex development tasks,
    enabling parallel execution, automatic code review, and self-improvement.
    """
    pass


cli.add_command(init)
cli.add_command(issue)
cli.add_command(launch)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
