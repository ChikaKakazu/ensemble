"""GitHub issue provider using gh CLI."""

import json
import shutil
import subprocess
from typing import Any

from ensemble.issue_provider import Issue, IssueProvider


class GitHubProvider(IssueProvider):
    """Issue provider for GitHub using the gh CLI."""

    def is_available(self) -> bool:
        """Check if gh CLI is installed.

        Returns:
            True if gh is available in PATH.
        """
        return shutil.which("gh") is not None

    def list_issues(self, state: str = "open") -> list[Issue]:
        """List issues using gh CLI.

        Args:
            state: Filter by issue state ('open', 'closed', 'all').

        Returns:
            List of Issue objects.

        Raises:
            RuntimeError: If gh command fails.
        """
        cmd = [
            "gh", "issue", "list",
            "--state", state,
            "--json", "number,title,body,url,state,labels",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to list issues: {result.stderr}")

        data = json.loads(result.stdout)
        return [self._parse_issue(item) for item in data]

    def get_issue(self, identifier: str) -> Issue:
        """Get a specific issue by number or URL.

        Args:
            identifier: Issue number (as string) or full URL.

        Returns:
            Issue object.

        Raises:
            ValueError: If the issue is not found.
            RuntimeError: If gh command fails.
        """
        cmd = [
            "gh", "issue", "view", identifier,
            "--json", "number,title,body,url,state,labels",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            if "not found" in result.stderr.lower() or "could not find" in result.stderr.lower():
                raise ValueError(f"Issue not found: {identifier}")
            raise RuntimeError(f"Failed to get issue: {result.stderr}")

        data = json.loads(result.stdout)
        return self._parse_issue(data)

    def _parse_issue(self, data: dict[str, Any]) -> Issue:
        """Parse issue data from gh JSON output.

        Args:
            data: Dictionary from gh JSON output.

        Returns:
            Issue object.
        """
        # Labels come as list of dicts with 'name' key
        labels = [label["name"] for label in data.get("labels", [])]

        return Issue(
            number=data["number"],
            title=data["title"],
            body=data.get("body", ""),
            url=data["url"],
            state=data["state"].lower(),
            labels=labels,
        )
