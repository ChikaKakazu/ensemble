"""Tests for the ensemble issue CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ensemble.cli import cli
from ensemble.issue_provider import Issue


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_issues():
    """Sample issues for testing."""
    return [
        Issue(
            number=1,
            title="Fix login bug",
            body="Users cannot login",
            url="https://github.com/owner/repo/issues/1",
            state="open",
            labels=["bug"],
        ),
        Issue(
            number=2,
            title="Add dark mode",
            body="Implement dark mode support",
            url="https://github.com/owner/repo/issues/2",
            state="open",
            labels=["feature", "ui"],
        ),
    ]


class TestIssueCommand:
    """Tests for issue command."""

    def test_issue_help(self, runner):
        """Test issue command shows help."""
        result = runner.invoke(cli, ["issue", "--help"])
        assert result.exit_code == 0
        assert "List issues or view a specific issue" in result.output

    @patch("ensemble.commands._issue_impl.GitHubProvider")
    def test_list_issues(self, mock_provider_class, runner, mock_issues):
        """Test listing issues."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.list_issues.return_value = mock_issues
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(cli, ["issue"])

        assert result.exit_code == 0
        assert "#1" in result.output
        assert "Fix login bug" in result.output
        assert "#2" in result.output
        assert "Add dark mode" in result.output

    @patch("ensemble.commands._issue_impl.GitHubProvider")
    def test_list_issues_empty(self, mock_provider_class, runner):
        """Test listing issues when none exist."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.list_issues.return_value = []
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(cli, ["issue"])

        assert result.exit_code == 0
        assert "No open issues found" in result.output

    @patch("ensemble.commands._issue_impl.GitHubProvider")
    def test_view_specific_issue(self, mock_provider_class, runner, mock_issues):
        """Test viewing a specific issue."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.get_issue.return_value = mock_issues[0]
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(cli, ["issue", "1"])

        assert result.exit_code == 0
        assert "Issue #1" in result.output
        assert "Fix login bug" in result.output
        assert "Users cannot login" in result.output

    @patch("ensemble.commands._issue_impl.GitHubProvider")
    def test_issue_not_found(self, mock_provider_class, runner):
        """Test viewing a non-existent issue."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.get_issue.side_effect = ValueError("Issue not found: 999")
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(cli, ["issue", "999"])

        assert result.exit_code != 0
        assert "Issue not found" in result.output

    @patch("ensemble.commands._issue_impl.GitHubProvider")
    def test_gh_not_available(self, mock_provider_class, runner):
        """Test error when gh is not installed."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(cli, ["issue"])

        assert result.exit_code != 0
        assert "gh" in result.output.lower() or "github" in result.output.lower()

    @patch("ensemble.commands._issue_impl.GitHubProvider")
    def test_list_with_state_filter(self, mock_provider_class, runner, mock_issues):
        """Test listing issues with state filter."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.list_issues.return_value = mock_issues
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(cli, ["issue", "--state", "closed"])

        assert result.exit_code == 0
        mock_provider.list_issues.assert_called_once_with(state="closed")

    def test_gitlab_provider_not_implemented(self, runner):
        """Test error for unimplemented GitLab provider."""
        result = runner.invoke(cli, ["issue", "--provider", "gitlab"])

        assert result.exit_code != 0
        assert "not yet implemented" in result.output.lower() or "coming soon" in result.output.lower()
