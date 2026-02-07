"""Tests for _launch_impl.py helper functions."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from ensemble.commands._launch_impl import (
    _check_claude,
    _check_tmux,
    _resolve_agent_paths,
    _session_exists,
)


class TestTmuxCheck:
    """Test tmux availability check."""

    def test_check_tmux(self):
        """Test _check_tmux returns bool based on tmux availability."""
        result = _check_tmux()
        assert isinstance(result, bool)
        # If tmux is in PATH, should return True
        expected = shutil.which("tmux") is not None
        assert result == expected


class TestClaudeCheck:
    """Test claude CLI availability check."""

    def test_check_claude(self):
        """Test _check_claude returns bool based on claude CLI availability."""
        result = _check_claude()
        assert isinstance(result, bool)
        # If claude is in PATH, should return True
        expected = shutil.which("claude") is not None
        assert result == expected


@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not available")
class TestSessionExists:
    """Test tmux session existence check (requires tmux)."""

    def test_session_exists_false(self):
        """Test _session_exists returns False for non-existent session."""
        # Use a session name that is very unlikely to exist
        session_name = "nonexistent-ensemble-test-session-12345"
        result = _session_exists(session_name)
        assert result is False

    def test_session_exists_true(self):
        """Test _session_exists returns True for existing session."""
        # Create a test session
        test_session = "ensemble-test-exists-session"
        try:
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", test_session],
                check=True,
                capture_output=True,
            )
            result = _session_exists(test_session)
            assert result is True
        finally:
            # Clean up test session
            subprocess.run(
                ["tmux", "kill-session", "-t", test_session],
                capture_output=True,
            )


class TestResolveAgentPaths:
    """Test agent path resolution with priority."""

    def test_resolve_agent_paths_local_priority(self):
        """Test that local project paths take priority over templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create local .claude/agents/conductor.md
            local_agents = project_root / ".claude" / "agents"
            local_agents.mkdir(parents=True)
            conductor_local = local_agents / "conductor.md"
            conductor_local.write_text("# Local Conductor")

            # Resolve paths
            paths = _resolve_agent_paths(project_root)

            # Should find conductor locally
            assert "conductor" in paths
            assert paths["conductor"] == conductor_local

    def test_resolve_agent_paths_template_fallback(self):
        """Test that template paths are used when local doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # No local agents directory
            # Resolve paths - should fall back to templates
            paths = _resolve_agent_paths(project_root)

            # Should still resolve conductor (from templates)
            assert "conductor" in paths
            # Template path should exist
            assert paths["conductor"].exists()
            assert "templates" in str(paths["conductor"]) or "ensemble" in str(paths["conductor"])

    def test_resolve_agent_paths_all_agents(self):
        """Test that all expected agents are resolved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            paths = _resolve_agent_paths(project_root)

            # Check that all expected agents are present
            expected_agents = [
                "conductor",
                "dispatch",
                "worker",
                "reviewer",
                "security-reviewer",
                "integrator",
                "learner",
            ]
            for agent in expected_agents:
                assert agent in paths, f"Missing agent: {agent}"
                assert paths[agent].exists(), f"Agent file does not exist: {paths[agent]}"


# Note: _save_pane_ids is tmux-dependent and creates sessions, so we skip it
# in automated tests. It would require a more complex test setup with actual
# tmux sessions running.
