"""Tests for CI/CD Pipeline Mode."""

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
