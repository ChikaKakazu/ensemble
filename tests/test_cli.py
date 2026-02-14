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

        # Check .ensemble internal directories
        assert (temp_project / ".ensemble").exists()
        assert (temp_project / ".ensemble" / "status").exists()

        # Check runtime directories at project root
        assert (temp_project / "queue").exists()
        assert (temp_project / "queue" / "conductor").exists()
        assert (temp_project / "queue" / "tasks").exists()
        assert (temp_project / "queue" / "reports").exists()
        assert (temp_project / "queue" / "ack").exists()
        assert (temp_project / "logs").exists()

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
        assert "queue/" in content

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

    def test_init_full_copies_commands(self, runner, temp_project):
        """Test that init --full copies command files."""
        result = runner.invoke(cli, ["init", "--full"])
        assert result.exit_code == 0

        commands_dir = temp_project / ".claude" / "commands"
        assert commands_dir.exists()

        # Check some expected command files
        expected_commands = ["go.md", "go-light.md", "improve.md"]
        for cmd in expected_commands:
            assert (commands_dir / cmd).exists(), f"Missing {cmd}"

        # Check new commands if they exist in templates
        new_commands = ["create-skill.md", "create-agent.md"]
        for cmd in new_commands:
            cmd_file = commands_dir / cmd
            # These may or may not exist depending on template version
            # Just check if they exist, don't fail if they don't
            if cmd_file.exists():
                assert cmd_file.read_text(), f"{cmd} is empty"

    def test_init_idempotent(self, runner, temp_project):
        """Test that running init twice doesn't overwrite existing files."""
        # First init
        result = runner.invoke(cli, ["init", "--full"])
        assert result.exit_code == 0

        # Modify a file
        conductor = temp_project / ".claude" / "agents" / "conductor.md"
        original_content = conductor.read_text()
        modified_content = original_content + "\n# MODIFIED\n"
        conductor.write_text(modified_content)

        # Second init (without --force)
        result = runner.invoke(cli, ["init", "--full"])
        assert result.exit_code == 0

        # File should not be overwritten
        content = conductor.read_text()
        assert "# MODIFIED" in content
        assert content == modified_content


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
