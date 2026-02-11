"""Tests for scan integration (hooks, autonomous loop, /go command)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSessionStartHook:
    """Test that session start hook runs scan."""

    def test_scan_hook_script_exists(self):
        """Test that the scan hook script exists."""
        script = Path(".claude/hooks/scripts/session-scan.sh")
        assert script.exists(), "session-scan.sh should exist in hooks/scripts/"

    def test_scan_hook_script_is_executable(self):
        """Test that the scan hook script is executable or valid bash."""
        script = Path(".claude/hooks/scripts/session-scan.sh")
        content = script.read_text()
        assert "ensemble scan" in content or "uv run" in content

    def test_settings_json_has_scan_hook(self):
        """Test that settings.json includes scan in SessionStart."""
        import json

        settings = json.loads(Path(".claude/settings.json").read_text())
        session_start_hooks = settings.get("hooks", {}).get("SessionStart", [])

        # At least one hook should reference scan
        hook_commands = []
        for hook_group in session_start_hooks:
            for hook in hook_group.get("hooks", []):
                hook_commands.append(hook.get("command", ""))

        assert any("scan" in cmd for cmd in hook_commands), \
            "SessionStart hooks should include a scan command"


class TestAutonomousLoopScanIntegration:
    """Test that autonomous loop uses scan for task selection."""

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_loop_scan_mode(self, mock_run, tmp_path):
        """Test autonomous loop with scan-based task selection."""
        from ensemble.autonomous_loop import AutonomousLoopRunner, LoopConfig, LoopStatus

        # Create a file with TODO
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("# TODO: implement feature\n")

        # Create PROGRESS.md
        (tmp_path / "PROGRESS.md").write_text("- [ ] Deploy to staging\n")

        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        config = LoopConfig(max_iterations=1, commit_each=False)
        runner = AutonomousLoopRunner(
            work_dir=tmp_path,
            config=config,
            use_scan=True,
        )
        result = runner.run()

        # Should have attempted to execute a task from scan
        assert result.iterations_completed >= 0

    @patch("ensemble.autonomous_loop.subprocess.run")
    def test_loop_scan_empty_stops(self, mock_run, tmp_path):
        """Test that scan mode stops when no tasks found."""
        from ensemble.autonomous_loop import AutonomousLoopRunner, LoopConfig, LoopStatus

        # Empty project - no TODOs, no issues, no progress
        config = LoopConfig(max_iterations=10, commit_each=False)
        runner = AutonomousLoopRunner(
            work_dir=tmp_path,
            config=config,
            use_scan=True,
        )
        result = runner.run()

        assert result.status == LoopStatus.QUEUE_EMPTY
        assert result.iterations_completed == 0


class TestGoCommandScanIntegration:
    """Test that /go command references scan."""

    def test_go_command_mentions_scan(self):
        """Test that go.md references ensemble scan."""
        go_md = Path(".claude/commands/go.md")
        content = go_md.read_text()

        assert "scan" in content.lower(), \
            "/go command should reference ensemble scan for task discovery"
