"""Abstract base class for issue providers (GitHub, GitLab, etc.)."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Issue:
    """Represents an issue from a code hosting platform."""

    number: int
    title: str
    body: str
    url: str
    state: str
    labels: list[str]

    def branch_slug(self, max_length: int = 50) -> str:
        """Generate a git branch name slug from the issue.

        Format: issue/<number>-<slugified-title>

        Args:
            max_length: Maximum length of the slug portion (excluding prefix).

        Returns:
            A valid git branch name.
        """
        # Convert title to lowercase
        slug = self.title.lower()

        # Replace special characters with spaces
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)

        # Replace whitespace with hyphens
        slug = re.sub(r"\s+", "-", slug)

        # Remove consecutive hyphens
        slug = re.sub(r"-+", "-", slug)

        # Trim hyphens from ends
        slug = slug.strip("-")

        # Truncate to max length
        if len(slug) > max_length:
            # Try to cut at a word boundary
            slug = slug[:max_length].rsplit("-", 1)[0]

        return f"issue/{self.number}-{slug}"


class IssueProvider(ABC):
    """Abstract base class for issue providers.

    Implementations should handle specific platforms like GitHub, GitLab, etc.
    """

    @abstractmethod
    def list_issues(self, state: str = "open") -> list[Issue]:
        """List issues in the repository.

        Args:
            state: Filter by issue state ('open', 'closed', 'all').

        Returns:
            List of Issue objects.

        Raises:
            RuntimeError: If the operation fails.
        """
        pass

    @abstractmethod
    def get_issue(self, identifier: str) -> Issue:
        """Get a specific issue by number or URL.

        Args:
            identifier: Issue number (as string) or full URL.

        Returns:
            Issue object.

        Raises:
            ValueError: If the issue is not found.
            RuntimeError: If the operation fails.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider's CLI tool is available.

        Returns:
            True if the CLI tool is installed and accessible.
        """
        pass
