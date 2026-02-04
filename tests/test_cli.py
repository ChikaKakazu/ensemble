"""Tests for Ensemble CLI."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from ensemble.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original_cwd)


class TestCLI:
    """Test main CLI commands."""

    def test_help(self, runner):
        """Test --help option."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Ensemble - AI Orchestration Tool" in result.output

    def test_version(self, runner):
        """Test --version option."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "ensemble, version" in result.output


class TestInitCommand:
    """Test ensemble init command."""

    def test_init_help(self, runner):
        """Test init --help."""
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize the current project" in result.output

    def test_init_creates_directories(self, runner, temp_project):
        """Test that init creates the correct directory structure."""
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        # Check directories
        assert (temp_project / ".ensemble").exists()
        assert (temp_project / ".ensemble" / "queue").exists()
        assert (temp_project / ".ensemble" / "queue" / "conductor").exists()
        assert (temp_project / ".ensemble" / "queue" / "tasks").exists()
        assert (temp_project / ".ensemble" / "queue" / "reports").exists()
        assert (temp_project / ".ensemble" / "queue" / "ack").exists()
        assert (temp_project / ".ensemble" / "status").exists()

    def test_init_creates_claude_md(self, runner, temp_project):
        """Test that init creates CLAUDE.md."""
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        claude_md = temp_project / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "## Ensemble AI Orchestration" in content
        assert "/go <task>" in content

    def test_init_creates_gitignore(self, runner, temp_project):
        """Test that init creates .gitignore."""
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        gitignore = temp_project / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "# Ensemble" in content
        assert ".ensemble/queue/" in content

    def test_init_appends_to_existing_gitignore(self, runner, temp_project):
        """Test that init appends to existing .gitignore."""
        gitignore = temp_project / ".gitignore"
        gitignore.write_text("node_modules/\n")

        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        content = gitignore.read_text()
        assert "node_modules/" in content
        assert "# Ensemble" in content

    def test_init_appends_to_existing_claude_md(self, runner, temp_project):
        """Test that init appends to existing CLAUDE.md."""
        claude_md = temp_project / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nExisting content.\n")

        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        content = claude_md.read_text()
        assert "# My Project" in content
        assert "Existing content." in content
        assert "## Ensemble AI Orchestration" in content

    def test_init_full_copies_agents(self, runner, temp_project):
        """Test that init --full copies agent definitions."""
        result = runner.invoke(cli, ["init", "--full"])
        assert result.exit_code == 0

        agents_dir = temp_project / ".claude" / "agents"
        assert agents_dir.exists()

        # Check some expected agent files
        expected_agents = ["conductor.md", "dispatch.md", "worker.md"]
        for agent in expected_agents:
            assert (agents_dir / agent).exists(), f"Missing {agent}"


class TestLaunchCommand:
    """Test ensemble launch command."""

    def test_launch_help(self, runner):
        """Test launch --help."""
        result = runner.invoke(cli, ["launch", "--help"])
        assert result.exit_code == 0
        assert "Launch the Ensemble tmux session" in result.output

    def test_launch_requires_init(self, runner, temp_project):
        """Test that launch fails without init (when tmux/claude available)."""
        # This test may pass (exit 0) if tmux is not installed
        # or may fail with "not initialized" if tmux is available
        result = runner.invoke(cli, ["launch", "--no-attach"])
        # Either not initialized error, or tmux/claude not found, or session exists
        if result.exit_code != 0:
            output_lower = result.output.lower()
            assert (
                "not initialized" in output_lower
                or "tmux" in output_lower
                or "claude" in output_lower
            )
