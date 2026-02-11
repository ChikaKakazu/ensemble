"""Tests for TaskInvestigator (ensemble investigate command)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ensemble.investigator import (
    InvestigationResult,
    InvestigationStrategy,
    TaskInvestigator,
)
from ensemble.scanner import ScanResult, TaskCandidate, TaskPriority


class TestInvestigationStrategy:
    """Test InvestigationStrategy enum."""

    def test_strategy_values(self):
        assert InvestigationStrategy.AGENT_TEAMS.value == "agent_teams"
        assert InvestigationStrategy.SUBPROCESS.value == "subprocess"
        assert InvestigationStrategy.INLINE.value == "inline"


class TestInvestigationResult:
    """Test InvestigationResult dataclass."""

    def test_creation(self):
        result = InvestigationResult(
            task_title="Fix auth bug",
            findings="Auth module needs refactoring",
            recommendation="refactor",
            estimated_effort="medium",
            priority_adjustment=None,
        )

        assert result.task_title == "Fix auth bug"
        assert result.findings == "Auth module needs refactoring"
        assert result.recommendation == "refactor"
        assert result.estimated_effort == "medium"
        assert result.priority_adjustment is None

    def test_creation_with_priority_adjustment(self):
        result = InvestigationResult(
            task_title="Security fix",
            findings="Critical vulnerability",
            recommendation="fix immediately",
            estimated_effort="small",
            priority_adjustment="high",
        )

        assert result.priority_adjustment == "high"


class TestTaskInvestigator:
    """Test TaskInvestigator."""

    def test_init(self, tmp_path):
        investigator = TaskInvestigator(root_dir=tmp_path)
        assert investigator.root_dir == tmp_path

    def test_detect_strategy_agent_teams(self, tmp_path, monkeypatch):
        """Test strategy detection when Agent Teams is available."""
        monkeypatch.setenv("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "1")
        investigator = TaskInvestigator(root_dir=tmp_path)
        strategy = investigator.detect_strategy()
        assert strategy == InvestigationStrategy.AGENT_TEAMS

    def test_detect_strategy_subprocess(self, tmp_path, monkeypatch):
        """Test strategy detection when Agent Teams not available."""
        monkeypatch.delenv("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", raising=False)
        investigator = TaskInvestigator(root_dir=tmp_path)
        strategy = investigator.detect_strategy()
        assert strategy == InvestigationStrategy.SUBPROCESS

    def test_detect_strategy_force(self, tmp_path):
        """Test forced strategy."""
        investigator = TaskInvestigator(
            root_dir=tmp_path,
            force_strategy=InvestigationStrategy.INLINE,
        )
        strategy = investigator.detect_strategy()
        assert strategy == InvestigationStrategy.INLINE

    def test_build_investigation_prompt(self, tmp_path):
        """Test building investigation prompt for a task candidate."""
        task = TaskCandidate(
            source="todo",
            title="FIXME: memory leak in connection pool",
            file_path="src/db.py",
            line_number=42,
            priority=TaskPriority.HIGH,
        )

        investigator = TaskInvestigator(root_dir=tmp_path)
        prompt = investigator.build_investigation_prompt(task)

        assert "memory leak" in prompt
        assert "src/db.py" in prompt
        assert "42" in prompt

    def test_build_investigation_prompt_no_file(self, tmp_path):
        """Test prompt for tasks without file location."""
        task = TaskCandidate(
            source="github-issue",
            title="#42 Login bug",
            priority=TaskPriority.HIGH,
        )

        investigator = TaskInvestigator(root_dir=tmp_path)
        prompt = investigator.build_investigation_prompt(task)

        assert "#42" in prompt
        assert "Login bug" in prompt

    @patch("ensemble.investigator.subprocess.run")
    def test_investigate_single_subprocess(self, mock_run, tmp_path):
        """Test investigating a single task via subprocess."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "findings": "The connection pool doesn't close connections properly.",
                "recommendation": "Add connection cleanup in __del__",
                "estimated_effort": "small",
                "priority_adjustment": "high",
            }),
        )

        task = TaskCandidate(
            source="todo",
            title="FIXME: memory leak",
            file_path="src/db.py",
            line_number=42,
            priority=TaskPriority.HIGH,
        )

        investigator = TaskInvestigator(
            root_dir=tmp_path,
            force_strategy=InvestigationStrategy.SUBPROCESS,
        )
        result = investigator.investigate_single(task)

        assert result is not None
        assert result.task_title == "FIXME: memory leak"
        mock_run.assert_called_once()

    @patch("ensemble.investigator.subprocess.run")
    def test_investigate_single_timeout(self, mock_run, tmp_path):
        """Test timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)

        task = TaskCandidate(
            source="todo",
            title="FIXME: test",
            priority=TaskPriority.MEDIUM,
        )

        investigator = TaskInvestigator(
            root_dir=tmp_path,
            force_strategy=InvestigationStrategy.SUBPROCESS,
        )
        result = investigator.investigate_single(task)

        assert result is None

    @patch("ensemble.investigator.subprocess.run")
    def test_investigate_single_claude_not_found(self, mock_run, tmp_path):
        """Test when claude CLI not found."""
        mock_run.side_effect = FileNotFoundError()

        task = TaskCandidate(
            source="todo",
            title="FIXME: test",
            priority=TaskPriority.MEDIUM,
        )

        investigator = TaskInvestigator(
            root_dir=tmp_path,
            force_strategy=InvestigationStrategy.SUBPROCESS,
        )
        result = investigator.investigate_single(task)

        assert result is None

    @patch("ensemble.investigator.subprocess.run")
    def test_investigate_batch(self, mock_run, tmp_path):
        """Test batch investigation."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "findings": "Issue found",
                "recommendation": "Fix it",
                "estimated_effort": "small",
            }),
        )

        tasks = [
            TaskCandidate(source="todo", title="Fix 1", priority=TaskPriority.HIGH),
            TaskCandidate(source="todo", title="Fix 2", priority=TaskPriority.MEDIUM),
        ]

        investigator = TaskInvestigator(
            root_dir=tmp_path,
            force_strategy=InvestigationStrategy.SUBPROCESS,
        )
        results = investigator.investigate_batch(tasks, max_tasks=5)

        assert len(results) == 2

    @patch("ensemble.investigator.subprocess.run")
    def test_investigate_batch_respects_limit(self, mock_run, tmp_path):
        """Test that batch respects max_tasks limit."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "findings": "Found",
                "recommendation": "Fix",
                "estimated_effort": "small",
            }),
        )

        tasks = [
            TaskCandidate(source="todo", title=f"Fix {i}", priority=TaskPriority.MEDIUM)
            for i in range(10)
        ]

        investigator = TaskInvestigator(
            root_dir=tmp_path,
            force_strategy=InvestigationStrategy.SUBPROCESS,
        )
        results = investigator.investigate_batch(tasks, max_tasks=3)

        assert len(results) == 3
        assert mock_run.call_count == 3

    def test_generate_agent_teams_script(self, tmp_path):
        """Test generating Agent Teams investigation script."""
        tasks = [
            TaskCandidate(source="todo", title="Fix auth", file_path="src/auth.py", priority=TaskPriority.HIGH),
            TaskCandidate(source="issue", title="#5 Add cache", priority=TaskPriority.MEDIUM),
        ]

        investigator = TaskInvestigator(root_dir=tmp_path)
        script = investigator.generate_agent_teams_script(tasks)

        assert "agent team" in script.lower() or "teammate" in script.lower()
        assert "Fix auth" in script
        assert "#5 Add cache" in script

    def test_format_results(self, tmp_path):
        """Test formatting investigation results."""
        results = [
            InvestigationResult(
                task_title="Fix auth",
                findings="Auth needs update",
                recommendation="Refactor",
                estimated_effort="medium",
            ),
            InvestigationResult(
                task_title="Add cache",
                findings="Cache improves perf",
                recommendation="Implement",
                estimated_effort="large",
                priority_adjustment="low",
            ),
        ]

        investigator = TaskInvestigator(root_dir=tmp_path)
        text = investigator.format_results(results)

        assert "Fix auth" in text
        assert "Add cache" in text
        assert "medium" in text
        assert "large" in text


class TestScannerExcludeTests:
    """Test scanner's test file exclusion."""

    def test_scan_todos_exclude_tests(self, tmp_path):
        """Test that test files can be excluded."""
        # Create test file with TODO
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_foo.py").write_text("# TODO: fix test\n")

        # Create source file with TODO
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# TODO: fix real issue\n")

        from ensemble.scanner import CodebaseScanner

        scanner = CodebaseScanner(root_dir=tmp_path, exclude_tests=True)
        tasks = scanner.scan_todos()

        assert len(tasks) == 1
        assert "real issue" in tasks[0].title

    def test_scan_todos_include_tests(self, tmp_path):
        """Test that test files are included by default."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_foo.py").write_text("# TODO: fix test\n")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# TODO: fix real issue\n")

        from ensemble.scanner import CodebaseScanner

        scanner = CodebaseScanner(root_dir=tmp_path, exclude_tests=False)
        tasks = scanner.scan_todos()

        assert len(tasks) == 2


class TestCLIInvestigateCommand:
    """Test CLI investigate command."""

    def test_investigate_command_exists(self):
        """Test that CLI has investigate command."""
        from ensemble.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["investigate", "--help"])

        assert result.exit_code == 0
        assert "--strategy" in result.output
        assert "--max-tasks" in result.output

    def test_scan_exclude_tests_option(self):
        """Test that scan command has --exclude-tests option."""
        from ensemble.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--help"])

        assert result.exit_code == 0
        assert "--exclude-tests" in result.output
