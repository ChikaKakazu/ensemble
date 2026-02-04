"""Tests for issue provider abstraction and GitHub implementation."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ensemble.issue_provider import Issue, IssueProvider
from ensemble.providers.github import GitHubProvider


class TestIssueDataclass:
    """Tests for Issue dataclass."""

    def test_issue_creation(self):
        """Test Issue can be created with all fields."""
        issue = Issue(
            number=123,
            title="Fix login bug",
            body="Users cannot login with email",
            url="https://github.com/owner/repo/issues/123",
            state="open",
            labels=["bug", "high-priority"],
        )

        assert issue.number == 123
        assert issue.title == "Fix login bug"
        assert issue.body == "Users cannot login with email"
        assert issue.url == "https://github.com/owner/repo/issues/123"
        assert issue.state == "open"
        assert issue.labels == ["bug", "high-priority"]

    def test_issue_with_empty_labels(self):
        """Test Issue can be created with empty labels."""
        issue = Issue(
            number=1,
            title="Test",
            body="Body",
            url="https://example.com",
            state="open",
            labels=[],
        )

        assert issue.labels == []

    def test_issue_branch_slug(self):
        """Test Issue can generate a branch slug."""
        issue = Issue(
            number=42,
            title="Add user authentication",
            body="",
            url="",
            state="open",
            labels=[],
        )

        slug = issue.branch_slug()
        assert slug == "issue/42-add-user-authentication"

    def test_issue_branch_slug_special_chars(self):
        """Test branch slug handles special characters."""
        issue = Issue(
            number=99,
            title="Fix: Bug in [API] endpoint!",
            body="",
            url="",
            state="open",
            labels=[],
        )

        slug = issue.branch_slug()
        # Special chars should be removed/replaced
        assert ":" not in slug
        assert "[" not in slug
        assert "]" not in slug
        assert "!" not in slug
        assert slug.startswith("issue/99-")

    def test_issue_branch_slug_long_title(self):
        """Test branch slug truncates long titles."""
        issue = Issue(
            number=1,
            title="This is a very long title that should be truncated to a reasonable length for a git branch name",
            body="",
            url="",
            state="open",
            labels=[],
        )

        slug = issue.branch_slug()
        # Branch name should be reasonable length
        assert len(slug) <= 60


class TestGitHubProvider:
    """Tests for GitHub provider implementation."""

    def test_is_available_when_gh_installed(self):
        """Test is_available returns True when gh is installed."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gh"
            provider = GitHubProvider()
            assert provider.is_available() is True
            mock_which.assert_called_with("gh")

    def test_is_available_when_gh_not_installed(self):
        """Test is_available returns False when gh is not installed."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            provider = GitHubProvider()
            assert provider.is_available() is False

    def test_list_issues_returns_issues(self):
        """Test list_issues returns parsed issues."""
        mock_output = json.dumps([
            {
                "number": 1,
                "title": "First issue",
                "body": "Body 1",
                "url": "https://github.com/owner/repo/issues/1",
                "state": "OPEN",
                "labels": [{"name": "bug"}],
            },
            {
                "number": 2,
                "title": "Second issue",
                "body": "Body 2",
                "url": "https://github.com/owner/repo/issues/2",
                "state": "OPEN",
                "labels": [],
            },
        ])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            provider = GitHubProvider()
            issues = provider.list_issues()

            assert len(issues) == 2
            assert issues[0].number == 1
            assert issues[0].title == "First issue"
            assert issues[0].labels == ["bug"]
            assert issues[1].number == 2
            assert issues[1].labels == []

    def test_list_issues_empty_repo(self):
        """Test list_issues returns empty list when no issues."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[]",
            )

            provider = GitHubProvider()
            issues = provider.list_issues()

            assert issues == []

    def test_list_issues_with_state_filter(self):
        """Test list_issues filters by state."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[]",
            )

            provider = GitHubProvider()
            provider.list_issues(state="closed")

            # Verify the command included state filter
            call_args = mock_run.call_args[0][0]
            assert "--state" in call_args
            assert "closed" in call_args

    def test_get_issue_by_number(self):
        """Test get_issue retrieves a specific issue."""
        mock_output = json.dumps({
            "number": 42,
            "title": "Fix the bug",
            "body": "Detailed description",
            "url": "https://github.com/owner/repo/issues/42",
            "state": "OPEN",
            "labels": [{"name": "bug"}, {"name": "urgent"}],
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            provider = GitHubProvider()
            issue = provider.get_issue("42")

            assert issue.number == 42
            assert issue.title == "Fix the bug"
            assert issue.body == "Detailed description"
            assert issue.labels == ["bug", "urgent"]

    def test_get_issue_by_url(self):
        """Test get_issue can handle URL input."""
        mock_output = json.dumps({
            "number": 99,
            "title": "URL issue",
            "body": "Body",
            "url": "https://github.com/owner/repo/issues/99",
            "state": "OPEN",
            "labels": [],
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            provider = GitHubProvider()
            issue = provider.get_issue("https://github.com/owner/repo/issues/99")

            assert issue.number == 99

    def test_get_issue_not_found(self):
        """Test get_issue raises error when issue not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="issue not found",
            )

            provider = GitHubProvider()
            with pytest.raises(ValueError, match="Issue not found"):
                provider.get_issue("999999")

    def test_list_issues_gh_error(self):
        """Test list_issues raises error on gh failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="not a git repository",
            )

            provider = GitHubProvider()
            with pytest.raises(RuntimeError, match="Failed to list issues"):
                provider.list_issues()


class TestIssueProviderInterface:
    """Tests to verify interface contract."""

    def test_github_provider_implements_interface(self):
        """Test GitHubProvider implements IssueProvider interface."""
        provider = GitHubProvider()

        # Should have all required methods
        assert hasattr(provider, "list_issues")
        assert hasattr(provider, "get_issue")
        assert hasattr(provider, "is_available")
        assert callable(provider.list_issues)
        assert callable(provider.get_issue)
        assert callable(provider.is_available)
