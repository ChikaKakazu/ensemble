"""Tests for Autonomous Loop Mode."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from ensemble.autonomous_loop import (
    AutonomousLoopRunner,
    LoopConfig,
    LoopResult,
    LoopStatus,
)
from ensemble.pipeline import EXIT_ERROR, EXIT_SUCCESS


class TestLoopConfig:
    """Test LoopConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LoopConfig()

        assert config.max_iterations == 50
        assert config.task_timeout == 600
        assert config.prompt_file == "AGENT_PROMPT.md"
        assert config.model == "sonnet"
        assert config.commit_each is True
        assert config.log_dir == ".ensemble/logs/loop"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = LoopConfig(
            max_iterations=10,
            task_timeout=300,
            prompt_file="custom-prompt.md",
            model="opus",
            commit_each=False,
            log_dir="custom/logs",
        )

        assert config.max_iterations == 10
        assert config.task_timeout == 300
        assert config.prompt_file == "custom-prompt.md"
        assert config.model == "opus"
        assert config.commit_each is False
        assert config.log_dir == "custom/logs"

    def test_max_iterations_must_be_positive(self):
        """Test that max_iterations must be positive."""
        with pytest.raises(ValueError, match="max_iterations must be positive"):
            LoopConfig(max_iterations=0)

    def test_task_timeout_must_be_positive(self):
        """Test that task_timeout must be positive."""
        with pytest.raises(ValueError, match="task_timeout must be positive"):
            LoopConfig(task_timeout=0)


class TestLoopResult:
    """Test LoopResult dataclass."""

    def test_result_creation(self):
        """Test LoopResult creation."""
        result = LoopResult(
            iterations_completed=5,
            status=LoopStatus.MAX_ITERATIONS,
            commits=[],
            errors=[],
        )

        assert result.iterations_completed == 5
        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.commits == []
        assert result.errors == []

    def test_result_with_data(self):
        """Test LoopResult with commits and errors."""
        result = LoopResult(
            iterations_completed=3,
            status=LoopStatus.COMPLETED,
            commits=["abc1234", "def5678", "ghi9012"],
            errors=["Warning: minor issue"],
        )

        assert result.iterations_completed == 3
        assert len(result.commits) == 3
        assert len(result.errors) == 1


class TestLoopStatus:
    """Test LoopStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert LoopStatus.COMPLETED.value == "completed"
        assert LoopStatus.MAX_ITERATIONS.value == "max_iterations"
        assert LoopStatus.ERROR.value == "error"
        assert LoopStatus.QUEUE_EMPTY.value == "queue_empty"
        assert LoopStatus.LOOP_DETECTED.value == "loop_detected"


class TestAutonomousLoopRunner:
    """Test AutonomousLoopRunner."""

    def test_init_default(self, tmp_path):
        """Test initialization with defaults."""
        runner = AutonomousLoopRunner(work_dir=tmp_path)

        assert runner.work_dir == tmp_path
        assert runner.config.max_iterations == 50
        assert runner.iteration == 0

    def test_init_custom_config(self, tmp_path):
        """Test initialization with custom config."""
        config = LoopConfig(max_iterations=10, model="opus")
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)

        assert runner.config.max_iterations == 10
        assert runner.config.model == "opus"

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_single_iteration_success(self, mock_run, tmp_path):
        """Test a single successful iteration."""
        # Setup prompt file
        prompt_file = tmp_path / "AGENT_PROMPT.md"
        prompt_file.write_text("Fix all bugs in the project.")

        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        config = LoopConfig(max_iterations=1, prompt_file="AGENT_PROMPT.md")
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.iterations_completed == 1
        assert result.status == LoopStatus.MAX_ITERATIONS

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_multiple_iterations(self, mock_run, tmp_path):
        """Test multiple iterations."""
        prompt_file = tmp_path / "AGENT_PROMPT.md"
        prompt_file.write_text("Improve the codebase.")

        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        config = LoopConfig(max_iterations=3, prompt_file="AGENT_PROMPT.md", commit_each=False)
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.iterations_completed == 3
        assert result.status == LoopStatus.MAX_ITERATIONS

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_iteration_with_error_continues(self, mock_run, tmp_path):
        """Test that a single iteration error doesn't stop the loop."""
        prompt_file = tmp_path / "AGENT_PROMPT.md"
        prompt_file.write_text("Fix bugs.")

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            cmd = args[0]
            if cmd[0] == "claude" and call_count <= 2:
                # First claude call fails, subsequent succeed
                return MagicMock(returncode=1, stdout="", stderr="Error")
            return MagicMock(returncode=0, stdout="Done", stderr="")

        mock_run.side_effect = side_effect

        config = LoopConfig(max_iterations=3, prompt_file="AGENT_PROMPT.md", commit_each=False)
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.iterations_completed == 3
        assert len(result.errors) >= 1

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_commit_each_iteration(self, mock_run, tmp_path):
        """Test that commits are created when commit_each=True."""
        prompt_file = tmp_path / "AGENT_PROMPT.md"
        prompt_file.write_text("Fix bugs.")

        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "git" and cmd[1] == "rev-parse":
                return MagicMock(returncode=0, stdout="abc1234\n", stderr="")
            if cmd[0] == "git" and cmd[1] == "diff":
                return MagicMock(returncode=0, stdout="some changes\n", stderr="")
            return MagicMock(returncode=0, stdout="Done", stderr="")

        mock_run.side_effect = side_effect

        config = LoopConfig(max_iterations=2, prompt_file="AGENT_PROMPT.md", commit_each=True)
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.iterations_completed == 2
        # git commands should include add and commit
        git_calls = [c for c in mock_run.call_args_list if c[0][0][0] == "git"]
        assert len(git_calls) > 0

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_timeout_handling(self, mock_run, tmp_path):
        """Test timeout handling in iteration."""
        prompt_file = tmp_path / "AGENT_PROMPT.md"
        prompt_file.write_text("Fix bugs.")

        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "claude":
                raise subprocess.TimeoutExpired(cmd="claude", timeout=600)
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        config = LoopConfig(max_iterations=2, prompt_file="AGENT_PROMPT.md", commit_each=False)
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.iterations_completed == 2
        assert len(result.errors) == 2

    def test_missing_prompt_file(self, tmp_path):
        """Test error when prompt file doesn't exist."""
        config = LoopConfig(max_iterations=1, prompt_file="nonexistent.md")
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.status == LoopStatus.ERROR
        assert result.iterations_completed == 0

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_log_files_created(self, mock_run, tmp_path):
        """Test that log files are created for each iteration."""
        prompt_file = tmp_path / "AGENT_PROMPT.md"
        prompt_file.write_text("Fix bugs.")

        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        log_dir = str(tmp_path / "logs")
        config = LoopConfig(
            max_iterations=2,
            prompt_file="AGENT_PROMPT.md",
            commit_each=False,
            log_dir=log_dir,
        )
        runner = AutonomousLoopRunner(work_dir=tmp_path, config=config)
        result = runner.run()

        assert result.iterations_completed == 2
        # Log directory should be created
        assert Path(log_dir).exists()

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_queue_mode(self, mock_run, tmp_path):
        """Test running with task queue."""
        # Create queue directory with a task
        queue_dir = tmp_path / "queue" / "tasks"
        queue_dir.mkdir(parents=True)

        task_file = queue_dir / "task-001.yaml"
        task_file.write_text(
            "task_id: task-001\n"
            "command: Fix authentication bug\n"
            "agent: worker\n"
            "status: pending\n"
        )

        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        config = LoopConfig(max_iterations=5, commit_each=False)
        runner = AutonomousLoopRunner(
            work_dir=tmp_path,
            config=config,
            use_queue=True,
        )
        result = runner.run()

        # Should process the queued task and stop when queue is empty
        assert result.status in (LoopStatus.QUEUE_EMPTY, LoopStatus.MAX_ITERATIONS)

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_queue_empty_stops_loop(self, mock_run, tmp_path):
        """Test that empty queue stops the loop."""
        # Create empty queue directory
        queue_dir = tmp_path / "queue" / "tasks"
        queue_dir.mkdir(parents=True)
        (tmp_path / "queue" / "processing").mkdir(parents=True)
        (tmp_path / "queue" / "reports").mkdir(parents=True)

        config = LoopConfig(max_iterations=10, commit_each=False)
        runner = AutonomousLoopRunner(
            work_dir=tmp_path,
            config=config,
            use_queue=True,
        )
        result = runner.run()

        assert result.status == LoopStatus.QUEUE_EMPTY
        assert result.iterations_completed == 0


class TestCLILoopCommand:
    """Test CLI loop command."""

    def test_loop_command_exists(self):
        """Test that CLI has loop command."""
        from click.testing import CliRunner

        from ensemble.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["loop", "--help"])

        assert result.exit_code == 0
        assert "--max-iterations" in result.output
        assert "--prompt" in result.output
        assert "--model" in result.output
        assert "--timeout" in result.output
        assert "--no-commit" in result.output
        assert "--queue" in result.output
