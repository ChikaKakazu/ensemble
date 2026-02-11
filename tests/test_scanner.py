"""Tests for CodebaseScanner (ensemble scan command)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ensemble.scanner import (
    CodebaseScanner,
    ScanResult,
    TaskCandidate,
    TaskPriority,
)


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_priority_values(self):
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"

    def test_priority_ordering(self):
        """High < Medium < Low in sort order."""
        priorities = [TaskPriority.LOW, TaskPriority.HIGH, TaskPriority.MEDIUM]
        sorted_p = sorted(priorities, key=lambda p: ["high", "medium", "low"].index(p.value))
        assert sorted_p == [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]


class TestTaskCandidate:
    """Test TaskCandidate dataclass."""

    def test_creation(self):
        task = TaskCandidate(
            source="todo",
            title="Fix authentication bug",
            description="TODO: fix auth in login.py:42",
            file_path="src/login.py",
            line_number=42,
            priority=TaskPriority.MEDIUM,
        )

        assert task.source == "todo"
        assert task.title == "Fix authentication bug"
        assert task.file_path == "src/login.py"
        assert task.line_number == 42
        assert task.priority == TaskPriority.MEDIUM

    def test_creation_minimal(self):
        task = TaskCandidate(
            source="issue",
            title="Add dark mode",
            priority=TaskPriority.LOW,
        )

        assert task.source == "issue"
        assert task.description is None
        assert task.file_path is None
        assert task.line_number is None


class TestScanResult:
    """Test ScanResult dataclass."""

    def test_empty_result(self):
        result = ScanResult(tasks=[], scan_errors=[])
        assert len(result.tasks) == 0
        assert result.total == 0

    def test_result_with_tasks(self):
        tasks = [
            TaskCandidate(source="todo", title="Fix bug", priority=TaskPriority.HIGH),
            TaskCandidate(source="issue", title="Add feature", priority=TaskPriority.LOW),
        ]
        result = ScanResult(tasks=tasks, scan_errors=[])
        assert result.total == 2

    def test_result_by_source(self):
        tasks = [
            TaskCandidate(source="todo", title="Fix 1", priority=TaskPriority.HIGH),
            TaskCandidate(source="todo", title="Fix 2", priority=TaskPriority.MEDIUM),
            TaskCandidate(source="issue", title="Feature 1", priority=TaskPriority.LOW),
        ]
        result = ScanResult(tasks=tasks, scan_errors=[])
        by_source = result.by_source()
        assert len(by_source["todo"]) == 2
        assert len(by_source["issue"]) == 1

    def test_result_sorted_by_priority(self):
        tasks = [
            TaskCandidate(source="todo", title="Low", priority=TaskPriority.LOW),
            TaskCandidate(source="todo", title="High", priority=TaskPriority.HIGH),
            TaskCandidate(source="todo", title="Medium", priority=TaskPriority.MEDIUM),
        ]
        result = ScanResult(tasks=tasks, scan_errors=[])
        sorted_tasks = result.sorted_by_priority()
        assert sorted_tasks[0].title == "High"
        assert sorted_tasks[1].title == "Medium"
        assert sorted_tasks[2].title == "Low"


class TestCodebaseScannerTodos:
    """Test TODO/FIXME/HACK scanning."""

    def test_scan_todos_basic(self, tmp_path):
        """Test scanning TODO comments."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text(
            "def login():\n"
            "    # TODO: implement proper auth\n"
            "    pass\n"
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        assert len(tasks) == 1
        assert tasks[0].source == "todo"
        assert "TODO" in tasks[0].title or "auth" in tasks[0].title
        assert tasks[0].line_number == 2

    def test_scan_fixme(self, tmp_path):
        """Test scanning FIXME comments."""
        (tmp_path / "app.py").write_text(
            "# FIXME: memory leak in connection pool\n"
            "def connect(): pass\n"
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        assert len(tasks) >= 1
        assert any("FIXME" in t.title for t in tasks)

    def test_scan_hack(self, tmp_path):
        """Test scanning HACK comments."""
        (tmp_path / "util.py").write_text(
            "# HACK: workaround for API bug\n"
            "def workaround(): pass\n"
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        assert len(tasks) >= 1
        assert any("HACK" in t.title for t in tasks)

    def test_scan_todos_priority(self, tmp_path):
        """Test that FIXME is higher priority than TODO."""
        (tmp_path / "code.py").write_text(
            "# TODO: add logging\n"
            "# FIXME: critical bug\n"
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        fixme_tasks = [t for t in tasks if "FIXME" in t.title]
        todo_tasks = [t for t in tasks if "TODO" in t.title]
        assert fixme_tasks[0].priority == TaskPriority.HIGH
        assert todo_tasks[0].priority == TaskPriority.MEDIUM

    def test_scan_no_todos(self, tmp_path):
        """Test scanning with no TODOs."""
        (tmp_path / "clean.py").write_text("def clean(): pass\n")

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        assert len(tasks) == 0

    def test_scan_ignores_binary_files(self, tmp_path):
        """Test that binary files are skipped."""
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        (tmp_path / "code.py").write_text("# TODO: fix this\n")

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        assert len(tasks) == 1  # Only from code.py

    def test_scan_respects_exclude_dirs(self, tmp_path):
        """Test that excluded directories are skipped."""
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "lib.js").write_text("// TODO: fix upstream\n")
        (tmp_path / "app.py").write_text("# TODO: our fix\n")

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_todos()

        assert len(tasks) == 1
        assert "our fix" in tasks[0].title


class TestCodebaseScannerIssues:
    """Test GitHub Issue scanning."""

    @patch("ensemble.scanner.subprocess.run")
    def test_scan_github_issues(self, mock_run, tmp_path):
        """Test fetching GitHub issues."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"number":42,"title":"Login bug","labels":[{"name":"bug"}]},{"number":38,"title":"Add dark mode","labels":[{"name":"feature"}]}]',
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_github_issues()

        assert len(tasks) == 2
        assert tasks[0].source == "github-issue"
        assert "#42" in tasks[0].title or "Login bug" in tasks[0].title

    @patch("ensemble.scanner.subprocess.run")
    def test_scan_github_issues_gh_not_found(self, mock_run, tmp_path):
        """Test when gh CLI is not available."""
        mock_run.side_effect = FileNotFoundError("gh not found")

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_github_issues()

        assert len(tasks) == 0

    @patch("ensemble.scanner.subprocess.run")
    def test_scan_github_issues_error(self, mock_run, tmp_path):
        """Test when gh command fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not a git repo")

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_github_issues()

        assert len(tasks) == 0

    @patch("ensemble.scanner.subprocess.run")
    def test_bug_label_is_high_priority(self, mock_run, tmp_path):
        """Test that bug-labeled issues get high priority."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"number":1,"title":"Critical bug","labels":[{"name":"bug"}]}]',
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_github_issues()

        assert tasks[0].priority == TaskPriority.HIGH


class TestCodebaseScannerProgress:
    """Test PROGRESS.md/PLAN.md scanning."""

    def test_scan_progress_md(self, tmp_path):
        """Test scanning PROGRESS.md for unchecked items."""
        (tmp_path / "PROGRESS.md").write_text(
            "# Progress\n"
            "- [x] Setup project\n"
            "- [ ] Implement auth\n"
            "- [ ] Add tests\n"
            "- [x] Create CI pipeline\n"
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_progress_files()

        assert len(tasks) == 2
        assert any("Implement auth" in t.title for t in tasks)
        assert any("Add tests" in t.title for t in tasks)

    def test_scan_plan_md(self, tmp_path):
        """Test scanning PLAN.md."""
        (tmp_path / "PLAN.md").write_text(
            "# Plan\n"
            "- [ ] Design API\n"
            "- [x] Setup database\n"
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_progress_files()

        assert len(tasks) == 1
        assert "Design API" in tasks[0].title

    def test_scan_no_progress_files(self, tmp_path):
        """Test when no progress files exist."""
        scanner = CodebaseScanner(root_dir=tmp_path)
        tasks = scanner.scan_progress_files()

        assert len(tasks) == 0


class TestCodebaseScannerFull:
    """Test full scan integration."""

    @patch("ensemble.scanner.subprocess.run")
    def test_full_scan(self, mock_run, tmp_path):
        """Test full scan combines all sources."""
        # Create TODO
        (tmp_path / "app.py").write_text("# TODO: add validation\n")

        # Create PROGRESS.md
        (tmp_path / "PROGRESS.md").write_text("- [ ] Deploy to staging\n")

        # Mock GitHub issues
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"number":1,"title":"Fix bug","labels":[]}]',
        )

        scanner = CodebaseScanner(root_dir=tmp_path)
        result = scanner.scan()

        assert result.total >= 3  # At least 1 TODO + 1 progress + 1 issue
        sources = {t.source for t in result.tasks}
        assert "todo" in sources
        assert "progress" in sources
        assert "github-issue" in sources

    def test_full_scan_empty_project(self, tmp_path):
        """Test scan on empty project."""
        scanner = CodebaseScanner(root_dir=tmp_path)
        result = scanner.scan()

        # Should not crash, may have 0 tasks
        assert isinstance(result, ScanResult)

    @patch("ensemble.scanner.subprocess.run")
    def test_scan_result_format(self, mock_run, tmp_path):
        """Test that scan result can be formatted as text."""
        (tmp_path / "code.py").write_text("# FIXME: critical issue\n")
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")

        scanner = CodebaseScanner(root_dir=tmp_path)
        result = scanner.scan()

        text = result.format_text()
        assert isinstance(text, str)
        assert len(text) > 0


class TestCLIScanCommand:
    """Test CLI scan command."""

    def test_scan_command_exists(self):
        """Test that CLI has scan command."""
        from ensemble.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--help"])

        assert result.exit_code == 0
        assert "--format" in result.output
        assert "--include" in result.output

    @patch("ensemble.scanner.subprocess.run")
    def test_scan_command_runs(self, mock_run, tmp_path, monkeypatch):
        """Test scan command execution."""
        from ensemble.cli import cli

        monkeypatch.chdir(tmp_path)
        (tmp_path / "code.py").write_text("# TODO: test scan\n")
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")

        runner = CliRunner()
        result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
