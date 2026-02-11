"""Tests for CI/CD Pipeline Mode."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ensemble.cli import cli
from ensemble.pipeline import (
    EXIT_ERROR,
    EXIT_LOOP_DETECTED,
    EXIT_NEEDS_FIX,
    EXIT_SUCCESS,
    PipelineRunner,
)


def test_pipeline_runner_init():
    """Test PipelineRunner initialization."""
    runner = PipelineRunner(
        task="Fix authentication bug",
        workflow="default",
        auto_pr=True,
        branch="feature/fix-auth",
    )

    assert runner.task == "Fix authentication bug"
    assert runner.workflow == "default"
    assert runner.auto_pr is True
    assert runner.branch == "feature/fix-auth"


def test_exit_codes():
    """Test that exit code constants are properly defined."""
    assert EXIT_SUCCESS == 0
    assert EXIT_ERROR == 1
    assert EXIT_NEEDS_FIX == 2
    assert EXIT_LOOP_DETECTED == 3


def test_generate_branch_name():
    """Test branch name auto-generation from task description."""
    runner = PipelineRunner(task="Fix authentication bug", workflow="default")

    # ブランチ名が自動生成される
    assert runner.branch.startswith("feature/")
    assert "fix" in runner.branch.lower() or "authentication" in runner.branch.lower()


def test_generate_branch_name_japanese():
    """Test branch name generation with Japanese characters."""
    runner = PipelineRunner(task="認証バグを修正する", workflow="default")

    # 日本語は除去され、英数字のみのブランチ名になる
    assert runner.branch.startswith("feature/")
    # 日本語がすべて除去された場合、タイムスタンプベースのブランチ名になる
    assert "task-" in runner.branch


def test_generate_branch_name_long():
    """Test branch name generation with long task description."""
    long_task = "Fix a very long authentication bug that occurs when users try to login with special characters in their username" * 3
    runner = PipelineRunner(task=long_task, workflow="default")

    # ブランチ名は最大50文字に切り詰められる（feature/を除く）
    branch_suffix = runner.branch.replace("feature/", "")
    assert len(branch_suffix) <= 50
    assert not branch_suffix.endswith("-")  # 末尾のハイフンは削除される


def test_pipeline_runner_workflow_validation():
    """Test that invalid workflow raises ValueError."""
    with pytest.raises(ValueError, match="Invalid workflow"):
        PipelineRunner(task="Fix bug", workflow="invalid_workflow")


def test_cli_pipeline_command_exists():
    """Test that CLI has pipeline command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["pipeline", "--help"])

    assert result.exit_code == 0
    assert "pipeline" in result.output.lower()
    assert "--task" in result.output
    assert "--workflow" in result.output
    assert "--auto-pr" in result.output
    assert "--branch" in result.output


def test_pipeline_runner_auto_generated_branch():
    """Test that branch is auto-generated when not specified."""
    runner = PipelineRunner(task="Add new feature", workflow="simple")

    # ブランチが自動生成される
    assert runner.branch is not None
    assert runner.branch.startswith("feature/")


def test_pipeline_runner_workflow_types():
    """Test that all workflow types are accepted."""
    workflows = ["simple", "default", "heavy"]

    for workflow in workflows:
        runner = PipelineRunner(task="Test task", workflow=workflow)
        assert runner.workflow == workflow


def test_pipeline_runner_branch_name_cleanup():
    """Test that branch names are properly cleaned up."""
    # スペースはハイフンに変換される
    runner1 = PipelineRunner(task="Fix Auth Bug", workflow="default")
    assert " " not in runner1.branch

    # 特殊文字は除去される
    runner2 = PipelineRunner(task="Fix: Bug #123!", workflow="default")
    assert ":" not in runner2.branch
    assert "#" not in runner2.branch
    assert "!" not in runner2.branch

    # 連続するハイフンは1つに統合される（スペース→ハイフン変換後）
    runner3 = PipelineRunner(task="Fix  multiple  spaces", workflow="default")
    assert "--" not in runner3.branch


# ============================================================
# subprocess系メソッドのテスト（13件追加）
# ============================================================


# _execute_task() のテスト (4件)
@patch("ensemble.pipeline.subprocess.run")
def test_execute_task_success(mock_run):
    """Test _execute_task with successful claude CLI execution."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Task completed", stderr="")

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    result = runner._execute_task()

    assert result == EXIT_SUCCESS
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "claude"
    assert "Fix bug" in args


@patch("ensemble.pipeline.subprocess.run")
def test_execute_task_cli_failure(mock_run):
    """Test _execute_task with claude CLI failure."""
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    result = runner._execute_task()

    assert result == EXIT_ERROR


@patch("ensemble.pipeline.subprocess.run")
def test_execute_task_timeout(mock_run):
    """Test _execute_task with timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=600)

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    result = runner._execute_task()

    assert result == EXIT_ERROR


@patch("ensemble.pipeline.subprocess.run")
def test_execute_task_cli_not_found(mock_run):
    """Test _execute_task with claude CLI not found."""
    mock_run.side_effect = FileNotFoundError("claude CLI not found")

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    result = runner._execute_task()

    assert result == EXIT_ERROR


# _run_review() のテスト (4件)
@patch("ensemble.pipeline.subprocess.run")
def test_run_review_approved(mock_run):
    """Test _run_review with approved result."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Review completed. All checks passed. approved",
        stderr=""
    )

    runner = PipelineRunner(task="Fix bug", workflow="default")
    result = runner._run_review()

    assert result == EXIT_SUCCESS


@patch("ensemble.pipeline.subprocess.run")
def test_run_review_needs_fix(mock_run):
    """Test _run_review with needs_fix result."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Review completed. Found issues. needs_fix: Missing tests",
        stderr=""
    )

    runner = PipelineRunner(task="Fix bug", workflow="default")
    result = runner._run_review()

    assert result == EXIT_NEEDS_FIX


@patch("ensemble.pipeline.subprocess.run")
def test_run_review_cli_failure(mock_run):
    """Test _run_review with claude CLI failure."""
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="CLI error")

    runner = PipelineRunner(task="Fix bug", workflow="default")
    result = runner._run_review()

    assert result == EXIT_ERROR


@patch("ensemble.pipeline.subprocess.run")
def test_run_review_timeout(mock_run):
    """Test _run_review with timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)

    runner = PipelineRunner(task="Fix bug", workflow="default")
    result = runner._run_review()

    assert result == EXIT_ERROR


# run() の統合テスト (2件)
@patch("ensemble.pipeline.subprocess.run")
def test_run_full_pipeline_success(mock_run):
    """Test run() with full pipeline success (simple workflow)."""
    # git checkout -b: 成功
    # claude task execution: 成功
    # git add .: 成功
    # git commit: 成功
    mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

    runner = PipelineRunner(task="Fix bug", workflow="simple", auto_pr=False)
    result = runner.run()

    assert result == EXIT_SUCCESS
    # git checkout -b, claude, git add, git commit の4回呼ばれる
    assert mock_run.call_count >= 4


@patch("ensemble.pipeline.subprocess.run")
def test_run_pipeline_task_failure_stops(mock_run):
    """Test run() stops when task execution fails."""
    def side_effect(*args, **kwargs):
        cmd = args[0]
        if cmd[0] == "git" and cmd[1] == "checkout":
            return MagicMock(returncode=0)
        elif cmd[0] == "claude":
            return MagicMock(returncode=1, stderr="Task failed")
        else:
            return MagicMock(returncode=0)

    mock_run.side_effect = side_effect

    runner = PipelineRunner(task="Fix bug", workflow="simple", auto_pr=False)
    result = runner.run()

    assert result == EXIT_ERROR
    # git checkoutとclaude実行のみ（commitまで到達しない）
    assert mock_run.call_count == 2


# _create_branch() のテスト (1件)
@patch("ensemble.pipeline.subprocess.run")
def test_create_branch(mock_run):
    """Test _create_branch calls git checkout -b."""
    mock_run.return_value = MagicMock(returncode=0)

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    runner._create_branch()

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "git"
    assert args[1] == "checkout"
    assert args[2] == "-b"
    assert runner.branch in args


# _commit_changes() のテスト (1件)
@patch("ensemble.pipeline.subprocess.run")
def test_commit_changes(mock_run):
    """Test _commit_changes calls git add and git commit."""
    mock_run.return_value = MagicMock(returncode=0)

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    runner._commit_changes()

    assert mock_run.call_count == 2
    # First call: git add .
    first_call_args = mock_run.call_args_list[0][0][0]
    assert first_call_args[0] == "git"
    assert first_call_args[1] == "add"
    assert first_call_args[2] == "."

    # Second call: git commit
    second_call_args = mock_run.call_args_list[1][0][0]
    assert second_call_args[0] == "git"
    assert second_call_args[1] == "commit"
    assert second_call_args[2] == "-m"


# _create_pr() のテスト (1件)
@patch("ensemble.pipeline.subprocess.run")
def test_create_pr(mock_run):
    """Test _create_pr calls git push and gh pr create."""
    mock_run.return_value = MagicMock(returncode=0)

    runner = PipelineRunner(task="Fix bug", workflow="simple")
    runner._create_pr()

    assert mock_run.call_count == 2
    # First call: git push
    first_call_args = mock_run.call_args_list[0][0][0]
    assert first_call_args[0] == "git"
    assert first_call_args[1] == "push"
    assert first_call_args[2] == "-u"

    # Second call: gh pr create
    second_call_args = mock_run.call_args_list[1][0][0]
    assert second_call_args[0] == "gh"
    assert second_call_args[1] == "pr"
    assert second_call_args[2] == "create"
