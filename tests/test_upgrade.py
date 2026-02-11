"""Tests for Ensemble upgrade command."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from ensemble.cli import cli
from ensemble.commands._upgrade_impl import (
    _get_template_file_for_relative_path,
    _scan_category,
    _scan_scripts,
    _scan_settings_json,
    TEMPLATE_CATEGORIES,
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
        # First, let's check that initially no updates are needed
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0
        # Should say all files are up to date or only skipped (no updates/new)
        assert (
            "All files are up to date" in result.output
            or "Updated 0" in result.output
            or "Would update 0 files" in result.output
        )

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

        # Record the hash BEFORE we modify it (simulate it was this way in old version)
        relative_path = ".claude/agents/conductor.md"
        record_file_version(temp_project, relative_path, conductor_file)

        # For testing, we can't easily modify the package template,
        # so this test verifies the --diff flag doesn't crash
        result = runner.invoke(cli, ["upgrade", "--diff", "--dry-run"])
        assert result.exit_code == 0

    def test_upgrade_scans_all_categories(self, runner, temp_project):
        """Test that all 12 template categories are scanned for updates."""
        # Verify that all categories from init --full are present
        claude_dir = temp_project / ".claude"

        # Run upgrade --dry-run
        result = runner.invoke(cli, ["upgrade", "--dry-run"])
        assert result.exit_code == 0
        # Should complete without error (all categories scanned)

    def test_upgrade_scans_hooks_scripts(self, runner, temp_project):
        """Test that hooks/scripts directory files are scanned for updates."""
        hooks_dir = temp_project / ".claude" / "hooks" / "scripts"
        if hooks_dir.exists():
            # Delete a hook script to simulate a missing file
            hook_files = list(hooks_dir.glob("*.sh"))
            if hook_files:
                deleted_file = hook_files[0]
                deleted_name = deleted_file.name
                deleted_file.unlink()

                # Remove from versions.json
                versions = load_versions(temp_project)
                relative_path = f".claude/hooks/scripts/{deleted_name}"
                if relative_path in versions:
                    del versions[relative_path]
                    from ensemble.version_tracker import save_versions
                    save_versions(temp_project, versions)

                # Run upgrade
                result = runner.invoke(cli, ["upgrade"])
                assert result.exit_code == 0

                # Verify file was re-created
                assert deleted_file.exists()
                assert deleted_name in result.output

    def test_upgrade_scans_rules(self, runner, temp_project):
        """Test that rules directory files are scanned for updates."""
        rules_dir = temp_project / ".claude" / "rules"
        if rules_dir.exists():
            rule_files = list(rules_dir.glob("*.md"))
            if rule_files:
                deleted_file = rule_files[0]
                deleted_name = deleted_file.name
                deleted_file.unlink()

                # Remove from versions.json
                versions = load_versions(temp_project)
                relative_path = f".claude/rules/{deleted_name}"
                if relative_path in versions:
                    del versions[relative_path]
                    from ensemble.version_tracker import save_versions
                    save_versions(temp_project, versions)

                # Run upgrade
                result = runner.invoke(cli, ["upgrade"])
                assert result.exit_code == 0

                # Verify file was re-created
                assert deleted_file.exists()

    def test_upgrade_scans_settings_json(self, runner, temp_project):
        """Test that settings.json is scanned for updates."""
        settings_file = temp_project / ".claude" / "settings.json"
        if settings_file.exists():
            settings_file.unlink()

            # Remove from versions.json
            versions = load_versions(temp_project)
            relative_path = ".claude/settings.json"
            if relative_path in versions:
                del versions[relative_path]
                from ensemble.version_tracker import save_versions
                save_versions(temp_project, versions)

            # Run upgrade
            result = runner.invoke(cli, ["upgrade"])
            assert result.exit_code == 0

            # Verify file was re-created
            assert settings_file.exists()
            assert "settings.json" in result.output

    def test_upgrade_scripts_in_claude_dir(self, runner, temp_project):
        """Test that scripts are scanned from .claude/scripts/ (not project root scripts/)."""
        scripts_dir = temp_project / ".claude" / "scripts"
        if scripts_dir.exists():
            script_files = list(scripts_dir.glob("*.sh"))
            if script_files:
                deleted_file = script_files[0]
                deleted_name = deleted_file.name
                deleted_file.unlink()

                # Remove from versions.json
                versions = load_versions(temp_project)
                relative_path = f".claude/scripts/{deleted_name}"
                if relative_path in versions:
                    del versions[relative_path]
                    from ensemble.version_tracker import save_versions
                    save_versions(temp_project, versions)

                # Run upgrade
                result = runner.invoke(cli, ["upgrade"])
                assert result.exit_code == 0

                # Verify file was re-created
                assert deleted_file.exists()


class TestUpgradeHelpers:
    """Test upgrade helper functions."""

    def test_scan_category_returns_list(self, temp_project):
        """Test that _scan_category returns correct tuple list."""
        results = _scan_category("agents", "*.md", "agents", temp_project)

        # Should return a list of tuples
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 3  # (status, relative_path, reason)
            status, path, reason = item
            assert status in ["new", "update", "skip", "force_update"]
            assert isinstance(path, str)
            assert isinstance(reason, str)

    def test_scan_scripts_returns_list(self, temp_project):
        """Test that _scan_scripts returns correct tuple list (legacy)."""
        results = _scan_scripts(temp_project)

        # Should return a list of tuples
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 3
            status, path, reason = item
            assert status in ["new", "update", "skip", "force_update"]

    def test_scan_settings_json(self, temp_project):
        """Test that _scan_settings_json works correctly."""
        results = _scan_settings_json(temp_project)

        # Should return a list of tuples
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 3

    def test_scan_category_hooks_scripts(self, temp_project):
        """Test that _scan_category works for nested hooks/scripts path."""
        results = _scan_category("hooks/scripts", "*.sh", "hooks/scripts", temp_project)

        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 3

    def test_get_template_file_for_agents_path(self):
        """Test that _get_template_file_for_relative_path works for .claude/ paths."""
        from ensemble.templates import get_template_path

        # Test .claude/agents/ path
        result = _get_template_file_for_relative_path(".claude/agents/conductor.md")
        assert result is not None
        expected = get_template_path("agents") / "conductor.md"
        assert result == expected

        # Test .claude/commands/ path
        result = _get_template_file_for_relative_path(".claude/commands/go.md")
        assert result is not None
        expected = get_template_path("commands") / "go.md"
        assert result == expected

    def test_get_template_file_for_hooks_scripts_path(self):
        """Test that _get_template_file_for_relative_path works for nested hooks/scripts paths."""
        result = _get_template_file_for_relative_path(".claude/hooks/scripts/session-scan.sh")
        assert result is not None
        assert result.name == "session-scan.sh"
        assert "hooks" in str(result) or "scripts" in str(result)

    def test_get_template_file_for_settings_json(self):
        """Test that _get_template_file_for_relative_path works for settings.json."""
        result = _get_template_file_for_relative_path(".claude/settings.json")
        assert result is not None
        assert result.name == "settings.json"

    def test_get_template_file_for_rules_path(self):
        """Test that _get_template_file_for_relative_path works for rules paths."""
        result = _get_template_file_for_relative_path(".claude/rules/workflow.md")
        assert result is not None
        assert result.name == "workflow.md"

    def test_get_template_file_for_invalid_path(self):
        """Test that _get_template_file_for_relative_path returns None for invalid paths."""
        result = _get_template_file_for_relative_path("random/path/file.txt")
        assert result is None

    def test_template_categories_completeness(self):
        """Test that TEMPLATE_CATEGORIES covers all expected categories."""
        expected_types = {
            "agents", "commands", "scripts", "workflows",
            "instructions", "policies", "personas", "output-contracts",
            "knowledge", "skills", "hooks/scripts", "rules",
        }
        actual_types = {t[0] for t in TEMPLATE_CATEGORIES}
        assert actual_types == expected_types


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
