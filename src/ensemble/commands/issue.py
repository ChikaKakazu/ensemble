"""Issue command for listing and viewing issues."""

import click


@click.command()
@click.argument("identifier", required=False)
@click.option(
    "--state",
    type=click.Choice(["open", "closed", "all"]),
    default="open",
    help="Filter issues by state.",
)
@click.option(
    "--provider",
    type=click.Choice(["github", "gitlab"]),
    default="github",
    help="Issue provider to use.",
)
def issue(identifier: str | None, state: str, provider: str) -> None:
    """List issues or view a specific issue.

    Without IDENTIFIER, lists all issues.
    With IDENTIFIER, shows details of that issue (number or URL).

    Examples:

        ensemble issue              # List open issues

        ensemble issue 123          # View issue #123

        ensemble issue --state all  # List all issues
    """
    from ensemble.commands._issue_impl import run_issue

    run_issue(identifier=identifier, state=state, provider=provider)
