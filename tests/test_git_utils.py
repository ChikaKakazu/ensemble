"""Tests for git utilities."""

import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

from ensemble.git_utils import (
    create_issue_branch,
    ensure_main_updated,
    create_pull_request,
    get_current_branch,
    is_working_tree_clean,
)


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_returns_current_branch(self):
        """Test returns the current branch name."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="feature/my-branch\n",
            )

            branch = get_current_branch()

            assert branch == "feature/my-branch"
            mock_run.assert_called_once()

    def test_strips_whitespace(self):
        """Test strips whitespace from branch name."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="  main  \n",
            )

            branch = get_current_branch()

            assert branch == "main"


class TestIsWorkingTreeClean:
    """Tests for is_working_tree_clean function."""

    def test_returns_true_when_clean(self):
        """Test returns True when working tree is clean."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
            )

            assert is_working_tree_clean() is True

    def test_returns_false_when_dirty(self):
        """Test returns False when there are uncommitted changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=" M src/file.py\n",
            )

            assert is_working_tree_clean() is False


class TestEnsureMainUpdated:
    """Tests for ensure_main_updated function."""

    def test_switches_to_main_and_pulls(self):
        """Test switches to main branch and pulls latest."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            ensure_main_updated()

            # Should call git checkout main and git pull
            calls = mock_run.call_args_list
            assert len(calls) >= 2

            # Check checkout main was called
            checkout_call = calls[0][0][0]
            assert "checkout" in checkout_call
            assert "main" in checkout_call

            # Check pull was called
            pull_call = calls[1][0][0]
            assert "pull" in pull_call

    def test_handles_checkout_failure(self):
        """Test raises error when checkout fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="error: Your local changes would be overwritten",
            )

            with pytest.raises(RuntimeError, match="Failed to checkout main"):
                ensure_main_updated()

    def test_uses_custom_base_branch(self):
        """Test can use a different base branch."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            ensure_main_updated(base_branch="develop")

            checkout_call = mock_run.call_args_list[0][0][0]
            assert "develop" in checkout_call


class TestCreateIssueBranch:
    """Tests for create_issue_branch function."""

    def test_creates_branch_with_issue_number_and_slug(self):
        """Test creates branch with correct naming."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            branch = create_issue_branch(123, "Fix login bug")

            assert branch == "issue/123-fix-login-bug"

            # Verify git checkout -b was called
            call_args = mock_run.call_args[0][0]
            assert "checkout" in call_args
            assert "-b" in call_args
            assert "issue/123-fix-login-bug" in call_args

    def test_sanitizes_branch_name(self):
        """Test sanitizes special characters in branch name."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            branch = create_issue_branch(1, "Fix: [API] bug!")

            # Should not contain special chars
            assert ":" not in branch
            assert "[" not in branch
            assert "]" not in branch
            assert "!" not in branch

    def test_handles_branch_exists(self):
        """Test handles case when branch already exists."""
        with patch("subprocess.run") as mock_run:
            # First call (checkout -b) fails, second (checkout) succeeds
            mock_run.side_effect = [
                MagicMock(returncode=1, stderr="already exists"),
                MagicMock(returncode=0),
            ]

            branch = create_issue_branch(42, "Existing branch")

            # Should try to checkout existing branch
            assert mock_run.call_count == 2


class TestCreatePullRequest:
    """Tests for create_pull_request function."""

    def test_creates_pr_with_gh(self):
        """Test creates PR using gh CLI."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/pull/1\n",
            )

            url = create_pull_request(
                title="Fix login bug",
                body="Closes #123",
            )

            assert url == "https://github.com/owner/repo/pull/1"

            call_args = mock_run.call_args[0][0]
            assert "gh" in call_args
            assert "pr" in call_args
            assert "create" in call_args

    def test_includes_title_and_body(self):
        """Test PR creation includes title and body."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/pull/1\n",
            )

            create_pull_request(
                title="My PR title",
                body="My PR body",
            )

            call_args = mock_run.call_args[0][0]
            assert "--title" in call_args
            assert "--body" in call_args

    def test_handles_pr_creation_failure(self):
        """Test raises error when PR creation fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="pull request already exists",
            )

            with pytest.raises(RuntimeError, match="Failed to create pull request"):
                create_pull_request("Title", "Body")

    def test_links_to_issue(self):
        """Test PR body can reference issue."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/pull/1\n",
            )

            create_pull_request(
                title="Fix bug",
                body="Closes #42",
                issue_number=42,
            )

            # Body should contain reference to issue
            call_args = mock_run.call_args
            # Find the body argument
            args_list = call_args[0][0]
            body_idx = args_list.index("--body") + 1
            body = args_list[body_idx]
            assert "#42" in body or "Closes" in body
