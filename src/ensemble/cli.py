"""Ensemble CLI - AI Orchestration Tool for Claude Code."""

import sys

import click

from ensemble import __version__
from ensemble.commands.init import init
from ensemble.commands.issue import issue
from ensemble.commands.launch import launch
from ensemble.commands.upgrade import upgrade
from ensemble.pipeline import PipelineRunner


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
cli.add_command(upgrade)


@cli.command()
@click.option(
    "--task",
    "-t",
    required=True,
    help="Task description",
)
@click.option(
    "--workflow",
    "-w",
    default="default",
    type=click.Choice(["simple", "default", "heavy"]),
    help="Workflow type (default: default)",
)
@click.option(
    "--auto-pr",
    is_flag=True,
    help="Automatically create PR after execution",
)
@click.option(
    "--branch",
    "-b",
    default=None,
    help="Branch name (auto-generated if not specified)",
)
def pipeline(task: str, workflow: str, auto_pr: bool, branch: str | None) -> None:
    """Run pipeline mode for CI/CD environments.

    Execute tasks in non-interactive mode without tmux.
    Outputs NDJSON logs to stdout and returns exit code.

    Exit codes:
      0 - Success
      1 - Execution error
      2 - Review needs_fix
      3 - Loop detected

    Example:
      ensemble pipeline --task "Fix authentication bug" --auto-pr
    """
    runner = PipelineRunner(task=task, workflow=workflow, auto_pr=auto_pr, branch=branch)
    exit_code = runner.run()
    sys.exit(exit_code)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
