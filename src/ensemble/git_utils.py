"""Git utilities for branch and PR management."""

import re
import subprocess


def get_current_branch() -> str:
    """Get the name of the current git branch.

    Returns:
        Current branch name.
    """
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def is_working_tree_clean() -> bool:
    """Check if the git working tree is clean.

    Returns:
        True if there are no uncommitted changes.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == ""


def ensure_main_updated(base_branch: str = "main") -> None:
    """Checkout the main branch and pull latest changes.

    Args:
        base_branch: Name of the base branch (default: main).

    Raises:
        RuntimeError: If checkout or pull fails.
    """
    # Checkout base branch
    result = subprocess.run(
        ["git", "checkout", base_branch],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to checkout {base_branch}: {result.stderr}")

    # Pull latest
    result = subprocess.run(
        ["git", "pull", "origin", base_branch],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Pull might fail if remote doesn't exist, which is OK for local repos
        pass


def create_issue_branch(issue_number: int, title: str) -> str:
    """Create a new branch for working on an issue.

    Format: issue/<number>-<slugified-title>

    Args:
        issue_number: Issue number.
        title: Issue title (will be slugified).

    Returns:
        Name of the created branch.

    Raises:
        RuntimeError: If branch creation fails.
    """
    # Slugify title
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")

    # Truncate if too long
    if len(slug) > 40:
        slug = slug[:40].rsplit("-", 1)[0]

    branch_name = f"issue/{issue_number}-{slug}"

    # Try to create new branch
    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Branch might already exist, try to checkout
        if "already exists" in result.stderr:
            result = subprocess.run(
                ["git", "checkout", branch_name],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to checkout branch {branch_name}: {result.stderr}")
        else:
            raise RuntimeError(f"Failed to create branch {branch_name}: {result.stderr}")

    return branch_name


def create_pull_request(
    title: str,
    body: str,
    issue_number: int | None = None,
) -> str:
    """Create a pull request using gh CLI.

    Args:
        title: PR title.
        body: PR body/description.
        issue_number: Optional issue number to link.

    Returns:
        URL of the created PR.

    Raises:
        RuntimeError: If PR creation fails.
    """
    # Build body with issue reference if provided
    full_body = body
    if issue_number:
        if f"#{issue_number}" not in body and f"Closes #{issue_number}" not in body:
            full_body = f"{body}\n\nCloses #{issue_number}"

    cmd = [
        "gh", "pr", "create",
        "--title", title,
        "--body", full_body,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create pull request: {result.stderr}")

    return result.stdout.strip()
