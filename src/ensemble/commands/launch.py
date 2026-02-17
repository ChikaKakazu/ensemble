"""Ensemble launch command - Start the Ensemble tmux session."""

import click


@click.command()
@click.option(
    "--session",
    "-s",
    default=None,
    help="Name of the tmux session to create. Defaults to current directory name.",
)
@click.option(
    "--attach/--no-attach",
    default=True,
    help="Attach to the session after creation.",
)
@click.pass_context
def launch(ctx: click.Context, session: str, attach: bool) -> None:
    """Launch the Ensemble tmux session.

    This command creates a tmux session with the Conductor, Dispatch,
    and Dashboard panes configured and ready for orchestration.

    The session will use configuration from (in priority order):
    1. ./.ensemble/agents/*.md (local project customization)
    2. ~/.config/ensemble/agents/*.md (global customization)
    3. Package bundled templates (defaults)
    """
    from ensemble.commands._launch_impl import run_launch

    run_launch(session=session, attach=attach)
