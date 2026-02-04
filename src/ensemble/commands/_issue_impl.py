"""Implementation of the ensemble issue command."""

import click

from ensemble.issue_provider import Issue, IssueProvider
from ensemble.providers.github import GitHubProvider


def get_provider(provider_name: str) -> IssueProvider:
    """Get the issue provider by name.

    Args:
        provider_name: Name of the provider ('github', 'gitlab').

    Returns:
        IssueProvider instance.

    Raises:
        click.ClickException: If provider is not available.
    """
    if provider_name == "github":
        provider = GitHubProvider()
        if not provider.is_available():
            raise click.ClickException(
                "GitHub CLI (gh) is not installed. "
                "Install it from: https://cli.github.com/"
            )
        return provider
    elif provider_name == "gitlab":
        raise click.ClickException(
            "GitLab provider is not yet implemented. Coming soon!"
        )
    else:
        raise click.ClickException(f"Unknown provider: {provider_name}")


def run_issue(
    identifier: str | None,
    state: str,
    provider: str,
) -> None:
    """Run the issue command implementation.

    Args:
        identifier: Issue number or URL (None to list issues).
        state: Filter state for listing ('open', 'closed', 'all').
        provider: Provider name ('github', 'gitlab').
    """
    issue_provider = get_provider(provider)

    if identifier:
        # View specific issue
        _view_issue(issue_provider, identifier)
    else:
        # List issues
        _list_issues(issue_provider, state)


def _view_issue(provider: IssueProvider, identifier: str) -> None:
    """View a specific issue.

    Args:
        provider: Issue provider instance.
        identifier: Issue number or URL.
    """
    try:
        issue = provider.get_issue(identifier)
        _print_issue_detail(issue)
    except ValueError as e:
        raise click.ClickException(str(e))
    except RuntimeError as e:
        raise click.ClickException(str(e))


def _list_issues(provider: IssueProvider, state: str) -> None:
    """List issues.

    Args:
        provider: Issue provider instance.
        state: Filter state.
    """
    try:
        issues = provider.list_issues(state=state)

        if not issues:
            click.echo(f"No {state} issues found.")
            return

        click.echo(f"\n{click.style(f'{len(issues)} {state} issue(s):', bold=True)}\n")

        for issue in issues:
            _print_issue_summary(issue)

        click.echo("")

    except RuntimeError as e:
        raise click.ClickException(str(e))


def _print_issue_summary(issue: Issue) -> None:
    """Print a one-line summary of an issue.

    Args:
        issue: Issue to print.
    """
    # Format: #123 [bug, urgent] Issue title
    number = click.style(f"#{issue.number}", fg="cyan", bold=True)
    labels = ""
    if issue.labels:
        label_str = ", ".join(issue.labels[:3])  # Max 3 labels
        if len(issue.labels) > 3:
            label_str += ", ..."
        labels = click.style(f" [{label_str}]", fg="yellow")

    # Truncate title if too long
    title = issue.title
    if len(title) > 60:
        title = title[:57] + "..."

    click.echo(f"  {number}{labels} {title}")


def _print_issue_detail(issue: Issue) -> None:
    """Print detailed view of an issue.

    Args:
        issue: Issue to print.
    """
    click.echo("")
    click.echo(click.style(f"Issue #{issue.number}", fg="cyan", bold=True))
    click.echo(click.style("=" * 60, dim=True))
    click.echo("")
    click.echo(f"{click.style('Title:', bold=True)} {issue.title}")
    click.echo(f"{click.style('State:', bold=True)} {issue.state}")

    if issue.labels:
        labels = ", ".join(issue.labels)
        click.echo(f"{click.style('Labels:', bold=True)} {labels}")

    click.echo(f"{click.style('URL:', bold=True)} {issue.url}")
    click.echo("")

    if issue.body:
        click.echo(click.style("Description:", bold=True))
        click.echo(click.style("-" * 40, dim=True))
        click.echo(issue.body)
    else:
        click.echo(click.style("(No description)", dim=True))

    click.echo("")
