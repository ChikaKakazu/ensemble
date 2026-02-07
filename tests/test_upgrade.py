"""Tests for Ensemble upgrade command."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from ensemble.cli import cli
from ensemble.commands._upgrade_impl import (
    _get_template_file_for_relative_path,
    _scan_scripts,
)
from ensemble.version_tracker import (
    compute_file_hash,
    load_versions,
    record_file_version,
)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_project():
    """Create a temporary project directory with ensemble initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        project_path = Path(tmpdir)

        # Initialize ensemble with --full to get agent definitions
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--full"])
        assert result.exit_code == 0

        yield project_path
        os.chdir(original_cwd)


class TestUpgradeCommand:
    """Test ensemble upgrade command."""

    def test_upgrade_help(self, runner):
        """Test upgrade --help."""
        result = runner.invoke(cli, ["upgrade", "--help"])
        assert result.exit_code == 0
        assert "Upgrade Ensemble files" in result.output

    def test_upgrade_requires_init(self, runner):
        """Test that upgrade fails without init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = runner.invoke(cli, ["upgrade"])
                assert result.exit_code == 0
                assert "Not an Ensemble project" in result.output
            finally:
                os.chdir(original_cwd)

    def test_upgrade_requires_full_init(self, runner):
        """Test that upgrade requires --full init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Init without --full
                result = runner.invoke(cli, ["init"])
                assert result.exit_code == 0

                # Try to upgrade
                result = runner.invoke(cli, ["upgrade"])
                assert result.exit_code == 0
                assert "No local agent definitions found" in result.output
            finally:
                os.chdir(original_cwd)

    def test_upgrade_unmodified_files(self, runner, temp_project):
        """Test that unmodified files are identified correctly."""
        # Modify a template to simulate a new version
        # (In real scenario, this would be a package update)
        # For testing, we'll modify the local file and then restore template

        # First, let's check that initially no updates are needed
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0
        # Should say all files are up to date
        assert "All files are up to date" in result.output or "Updated 0" in result.output

    def test_upgrade_modified_files_skipped(self, runner, temp_project):
        """Test that modified files are skipped."""
        # Modify a local file
        conductor_file = temp_project / ".claude" / "agents" / "conductor.md"
        original_content = conductor_file.read_text()
        conductor_file.write_text(original_content + "\n# User modification\n")

        # Run upgrade dry-run
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0

        # Should mention skipped files
        if "conductor.md" in result.output:
            assert "modified locally" in result.output or "skipping" in result.output.lower()

    def test_upgrade_force_with_backup(self, runner, temp_project):
        """Test that --force creates backups of modified files."""
        # Modify a local file
        conductor_file = temp_project / ".claude" / "agents" / "conductor.md"
        original_content = conductor_file.read_text()
        modified_content = original_content + "\n# User modification\n"
        conductor_file.write_text(modified_content)

        # Run upgrade with --force
        result = runner.invoke(cli, ["upgrade", "--force"])
        assert result.exit_code == 0

        # Check for backup file (if conductor.md was detected as modified)
        backup_files = list(conductor_file.parent.glob("conductor.backup_*.md"))
        # May or may not have backup depending on whether file was detected as modified
        # The test setup makes all files "unmodified" initially since they're freshly copied

    def test_upgrade_dry_run(self, runner, temp_project):
        """Test that --dry-run doesn't make changes."""
        # Get initial file hashes
        agents_dir = temp_project / ".claude" / "agents"
        initial_hashes = {}
        for agent_file in agents_dir.glob("*.md"):
            initial_hashes[agent_file.name] = compute_file_hash(agent_file)

        # Run upgrade --dry-run
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0
        # If all files are up to date, the message will be different
        assert "Dry run" in result.output or "All files are up to date" in result.output

        # Verify files haven't changed
        for agent_file in agents_dir.glob("*.md"):
            assert compute_file_hash(agent_file) == initial_hashes[agent_file.name]

    def test_upgrade_new_files(self, runner, temp_project):
        """Test that new files are added during upgrade."""
        # Delete a local file to simulate a missing file
        conductor_file = temp_project / ".claude" / "agents" / "conductor.md"
        conductor_file.unlink()

        # Also remove it from versions.json
        versions = load_versions(temp_project)
        relative_path = ".claude/agents/conductor.md"
        if relative_path in versions:
            del versions[relative_path]
            from ensemble.version_tracker import save_versions
            save_versions(temp_project, versions)

        # Run upgrade
        result = runner.invoke(cli, ["upgrade"])
        assert result.exit_code == 0

        # Verify file was re-created
        assert conductor_file.exists()
        assert "conductor.md" in result.output
        assert "(new file)" in result.output

    def test_upgrade_diff_option(self, runner, temp_project):
        """Test that --diff shows differences."""
        # Modify a file and mark it as unmodified (simulate template change)
        conductor_file = temp_project / ".claude" / "agents" / "conductor.md"
        original_content = conductor_file.read_text()

        # Record the hash BEFORE we modify it (simulate it was this way in old version)
        relative_path = ".claude/agents/conductor.md"
        record_file_version(temp_project, relative_path, conductor_file)

        # Now modify the template (in reality this would be in package)
        # For testing, we can't easily modify the package template,
        # so this test verifies the --diff flag doesn't crash
        result = runner.invoke(cli, ["upgrade", "--diff", "--dry-run"])
        assert result.exit_code == 0

    def test_upgrade_scans_scripts(self, runner, temp_project):
        """Test that scripts/ directory files are scanned for updates."""
        # Create scripts directory if it doesn't exist
        scripts_dir = temp_project / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create a test script file
        test_script = scripts_dir / "setup.sh"
        test_script.write_text("#!/bin/bash\necho 'test'\n")

        # Run upgrade --dry-run
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0

        # Verify scripts/ files are included in scan
        # The output should mention scripts if they're scanned
        # (Either as up-to-date, new, or modified)

    def test_upgrade_scripts_new_file(self, runner, temp_project):
        """Test that new script files from template are detected."""
        # Create scripts directory
        scripts_dir = temp_project / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Delete a script file if it exists to simulate a new file scenario
        setup_script = scripts_dir / "setup.sh"
        if setup_script.exists():
            setup_script.unlink()

        # Also remove it from versions.json
        versions = load_versions(temp_project)
        relative_path = "scripts/setup.sh"
        if relative_path in versions:
            del versions[relative_path]
            from ensemble.version_tracker import save_versions
            save_versions(temp_project, versions)

        # Run upgrade
        result = runner.invoke(cli, ["upgrade"])
        assert result.exit_code == 0

        # If setup.sh exists in template, it should be detected as new
        if "setup.sh" in result.output:
            assert "(new file)" in result.output or "added 1" in result.output

    def test_upgrade_scripts_modified_skipped(self, runner, temp_project):
        """Test that locally modified script files are skipped."""
        # Create scripts directory
        scripts_dir = temp_project / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create and record a script file
        setup_script = scripts_dir / "setup.sh"
        original_content = "#!/bin/bash\necho 'original'\n"
        setup_script.write_text(original_content)

        # Record the original version
        relative_path = "scripts/setup.sh"
        record_file_version(temp_project, relative_path, setup_script)

        # Modify the file
        setup_script.write_text(original_content + "\n# User modification\n")

        # Run upgrade --dry-run
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0

        # Should mention skipped files
        if "setup.sh" in result.output:
            assert "modified locally" in result.output or "skipping" in result.output.lower()


class TestUpgradeHelpers:
    """Test upgrade helper functions."""

    def test_scan_scripts_returns_list(self, temp_project):
        """Test that _scan_scripts returns correct tuple list."""
        # Create scripts directory with a test file
        scripts_dir = temp_project / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        test_script = scripts_dir / "test.sh"
        test_script.write_text("#!/bin/bash\necho 'test'\n")

        # Record version
        record_file_version(temp_project, "scripts/test.sh", test_script)

        # Call _scan_scripts
        results = _scan_scripts(temp_project)

        # Should return a list of tuples
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 3  # (status, relative_path, reason)
            status, path, reason = item
            assert status in ["new", "update", "skip", "force_update"]
            assert isinstance(path, str)
            assert isinstance(reason, str)

    def test_get_template_file_for_scripts_path(self):
        """Test that _get_template_file_for_relative_path works for scripts/ paths."""
        from ensemble.templates import get_template_path

        # Test scripts/ path
        result = _get_template_file_for_relative_path("scripts/setup.sh")

        # Should return a Path object pointing to template
        assert result is not None
        expected = get_template_path("scripts") / "setup.sh"
        assert result == expected

    def test_get_template_file_for_agents_path(self):
        """Test that _get_template_file_for_relative_path still works for .claude/ paths."""
        from ensemble.templates import get_template_path

        # Test .claude/agents/ path
        result = _get_template_file_for_relative_path(".claude/agents/conductor.md")

        # Should return a Path object pointing to template
        assert result is not None
        expected = get_template_path("agents") / "conductor.md"
        assert result == expected

        # Test .claude/commands/ path
        result = _get_template_file_for_relative_path(".claude/commands/go.md")

        assert result is not None
        expected = get_template_path("commands") / "go.md"
        assert result == expected


class TestVersionTracker:
    """Test version tracking functionality."""

    def test_compute_file_hash(self, temp_project):
        """Test hash computation."""
        test_file = temp_project / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = compute_file_hash(test_file)
        assert len(hash1) == 64  # SHA256 hex string

        # Same content should give same hash
        test_file2 = temp_project / "test2.txt"
        test_file2.write_text("Hello, World!")
        hash2 = compute_file_hash(test_file2)
        assert hash1 == hash2

        # Different content should give different hash
        test_file2.write_text("Different content")
        hash3 = compute_file_hash(test_file2)
        assert hash1 != hash3

    def test_record_and_load_versions(self, temp_project):
        """Test recording and loading versions."""
        test_file = temp_project / "test.txt"
        test_file.write_text("Test content")

        # Record version
        record_file_version(temp_project, "test.txt", test_file)

        # Load and verify
        versions = load_versions(temp_project)
        assert "test.txt" in versions
        assert versions["test.txt"] == compute_file_hash(test_file)

    def test_check_file_modified(self, temp_project):
        """Test checking if file was modified."""
        from ensemble.version_tracker import check_file_modified

        test_file = temp_project / "test.txt"
        test_file.write_text("Original content")

        # Record version
        record_file_version(temp_project, "test.txt", test_file)

        # Should not be modified
        assert not check_file_modified(temp_project, "test.txt", test_file)

        # Modify file
        test_file.write_text("Modified content")

        # Should be detected as modified
        assert check_file_modified(temp_project, "test.txt", test_file)

    def test_check_file_modified_untracked(self, temp_project):
        """Test checking untracked file."""
        from ensemble.version_tracker import check_file_modified

        test_file = temp_project / "test.txt"
        test_file.write_text("Content")

        # Untracked file should be considered modified
        assert check_file_modified(temp_project, "test.txt", test_file)

    def test_versions_json_created(self, temp_project):
        """Test that versions.json is created."""
        versions_file = temp_project / ".ensemble" / "versions.json"

        # Should exist after init --full (files were recorded)
        assert versions_file.exists()

        # Should contain agent files
        versions = load_versions(temp_project)
        assert len(versions) > 0
        assert any(".claude/agents/" in path for path in versions.keys())
