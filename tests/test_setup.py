"""Tests for setup.sh script"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for testing setup.sh"""
    temp_dir = tempfile.mkdtemp()
    # Copy setup.sh to temp dir
    scripts_dir = Path(temp_dir) / "scripts"
    scripts_dir.mkdir()

    # Get the real setup.sh path
    real_setup = Path(__file__).parent.parent / "scripts" / "setup.sh"
    if real_setup.exists():
        shutil.copy(real_setup, scripts_dir / "setup.sh")

    yield temp_dir
    shutil.rmtree(temp_dir)


class TestSetupScript:
    """Test cases for setup.sh"""

    def test_setup_creates_claude_directory(self, temp_project_dir):
        """setup.sh should create .claude/ directory structure"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        result = subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Setup failed: {result.stderr}"
        assert (Path(temp_project_dir) / ".claude" / "agents").is_dir()
        assert (Path(temp_project_dir) / ".claude" / "commands").is_dir()
        assert (Path(temp_project_dir) / ".claude" / "skills").is_dir()

    def test_setup_creates_queue_directory(self, temp_project_dir):
        """setup.sh should create queue/ directory for file-based communication"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True
        )

        assert (Path(temp_project_dir) / "queue" / "tasks").is_dir()
        assert (Path(temp_project_dir) / "queue" / "reports").is_dir()
        assert (Path(temp_project_dir) / "queue" / "ack").is_dir()

    def test_setup_creates_status_directory(self, temp_project_dir):
        """setup.sh should create status/ directory with dashboard.md"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True
        )

        assert (Path(temp_project_dir) / "status").is_dir()
        assert (Path(temp_project_dir) / "status" / "dashboard.md").is_file()

    def test_setup_creates_claude_md(self, temp_project_dir):
        """setup.sh should create CLAUDE.md with compaction recovery protocol"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True
        )

        claude_md = Path(temp_project_dir) / "CLAUDE.md"
        assert claude_md.is_file()

        content = claude_md.read_text()
        # Check for compaction recovery protocol
        assert "コンパクション復帰プロトコル" in content
        assert "tmux display-message" in content

    def test_setup_does_not_overwrite_existing_claude_md(self, temp_project_dir):
        """setup.sh should not overwrite existing CLAUDE.md"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        # Create existing CLAUDE.md
        existing_content = "# Existing Project Rules\n\nDo not overwrite this."
        claude_md = Path(temp_project_dir) / "CLAUDE.md"
        claude_md.write_text(existing_content)

        subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True
        )

        # Should preserve existing content
        assert claude_md.read_text() == existing_content

    def test_setup_creates_notes_directory(self, temp_project_dir):
        """setup.sh should create notes/ directory for learning records"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True
        )

        assert (Path(temp_project_dir) / "notes").is_dir()

    def test_setup_creates_workflows_directory(self, temp_project_dir):
        """setup.sh should create workflows/ directory"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True
        )

        assert (Path(temp_project_dir) / "workflows").is_dir()

    def test_setup_is_idempotent(self, temp_project_dir):
        """setup.sh should be safe to run multiple times"""
        setup_script = Path(temp_project_dir) / "scripts" / "setup.sh"
        if not setup_script.exists():
            pytest.skip("setup.sh not yet implemented")

        # Run twice
        result1 = subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )
        result2 = subprocess.run(
            ["bash", str(setup_script)],
            cwd=temp_project_dir,
            capture_output=True,
            text=True
        )

        assert result1.returncode == 0
        assert result2.returncode == 0
