"""Tests for Ensemble config module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ensemble.config import (
    get_global_config_dir,
    get_local_config_dir,
    load_config,
    resolve_agent_path,
    resolve_workflow_path,
    _deep_merge,
    ensure_global_config,
    _write_default_config,
    DEFAULT_CONFIG,
)


class TestConfigPaths:
    """Test configuration path functions."""

    def test_global_config_dir(self):
        """Test global config directory path."""
        path = get_global_config_dir()
        assert path == Path.home() / ".config" / "ensemble"

    def test_local_config_dir(self):
        """Test local config directory path."""
        path = get_local_config_dir()
        assert path == Path.cwd() / ".ensemble"


class TestDeepMerge:
    """Test _deep_merge function."""

    def test_simple_merge(self):
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 20, "z": 30}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}

    def test_base_unchanged(self):
        """Test that base dictionary is not modified."""
        base = {"a": 1}
        override = {"a": 2}
        _deep_merge(base, override)
        assert base == {"a": 1}


class TestLoadConfig:
    """Test load_config function."""

    def test_default_config(self):
        """Test that default config is returned when no files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                config = load_config()
                assert "version" in config
                assert "session" in config
                assert "agents" in config

    def test_load_with_global_config(self):
        """Test loading with global config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config
            global_config_path = Path(tmpdir) / "config.yaml"
            global_config_path.write_text(
                "session:\n  name: test-session\nversion: 1.0.0\n"
            )

            with patch("ensemble.config.get_global_config_dir", return_value=Path(tmpdir)):
                with patch.object(Path, "cwd", return_value=Path(tmpdir) / "project"):
                    config = load_config()
                    # Global config overrides defaults
                    assert config["session"]["name"] == "test-session"
                    assert config["version"] == "1.0.0"

    def test_load_with_local_config(self):
        """Test loading with local config file (overrides global)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create local config directory
            local_dir = Path(tmpdir) / ".ensemble"
            local_dir.mkdir()
            local_config_path = local_dir / "config.yaml"
            local_config_path.write_text(
                "session:\n  name: local-session\n"
            )

            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                config = load_config()
                # Local config overrides defaults
                assert config["session"]["name"] == "local-session"

    def test_load_with_both_configs(self):
        """Test loading with both global and local configs (local takes priority)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global config
            global_dir = Path(tmpdir) / "global"
            global_dir.mkdir()
            (global_dir / "config.yaml").write_text(
                "session:\n  name: global-session\n  attach: false\n"
            )

            # Create local config
            local_dir = Path(tmpdir) / "project" / ".ensemble"
            local_dir.mkdir(parents=True)
            (local_dir / "config.yaml").write_text(
                "session:\n  name: local-session\n"
            )

            with patch("ensemble.config.get_global_config_dir", return_value=global_dir):
                with patch.object(Path, "cwd", return_value=Path(tmpdir) / "project"):
                    config = load_config()
                    # Local overrides global for name
                    assert config["session"]["name"] == "local-session"
                    # Global value kept for attach
                    assert config["session"]["attach"] is False


class TestEnsureGlobalConfig:
    """Test ensure_global_config function."""

    def test_ensure_global_config_creates_dir(self):
        """Test that ensure_global_config creates the directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "ensemble"

            with patch("ensemble.config.get_global_config_dir", return_value=target_dir):
                result = ensure_global_config()
                assert result == target_dir
                assert target_dir.exists()

    def test_ensure_global_config_copies_templates(self):
        """Test that templates are copied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "ensemble"

            with patch("ensemble.config.get_global_config_dir", return_value=target_dir):
                ensure_global_config()
                # Config file should be created
                assert (target_dir / "config.yaml").exists()
                # Agents and workflows directories should exist
                assert (target_dir / "agents").exists()
                assert (target_dir / "workflows").exists()

    def test_ensure_global_config_idempotent(self):
        """Test that calling ensure_global_config twice doesn't fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "ensemble"

            with patch("ensemble.config.get_global_config_dir", return_value=target_dir):
                # First call
                ensure_global_config()
                # Second call should not fail
                ensure_global_config()
                assert target_dir.exists()


class TestWriteDefaultConfig:
    """Test _write_default_config function."""

    def test_write_default_config(self):
        """Test that default config is written correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            _write_default_config(config_path)

            assert config_path.exists()
            # Read and verify
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
            assert "version" in config
            assert "session" in config
            assert "agents" in config


class TestResolveAgentPath:
    """Test resolve_agent_path function."""

    def test_resolve_package_agent(self):
        """Test resolving agent from package templates."""
        path = resolve_agent_path("conductor")
        assert path is not None
        assert path.exists()
        assert path.name == "conductor.md"

    def test_resolve_nonexistent_agent(self):
        """Test resolving nonexistent agent returns None."""
        path = resolve_agent_path("nonexistent-agent-xyz")
        assert path is None

    def test_local_takes_priority(self):
        """Test that local agent takes priority over package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Create local agent
                local_agent_dir = Path(tmpdir) / ".claude" / "agents"
                local_agent_dir.mkdir(parents=True)
                local_agent = local_agent_dir / "conductor.md"
                local_agent.write_text("# Custom Conductor")

                path = resolve_agent_path("conductor")
                assert path == local_agent
            finally:
                os.chdir(original_cwd)

    def test_resolve_global_agent(self):
        """Test resolving agent from global config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global agent
            global_dir = Path(tmpdir) / "global"
            global_agent_dir = global_dir / "agents"
            global_agent_dir.mkdir(parents=True)
            global_agent = global_agent_dir / "custom-agent.md"
            global_agent.write_text("# Global Custom Agent")

            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("ensemble.config.get_global_config_dir", return_value=global_dir):
                    path = resolve_agent_path("custom-agent")
                    assert path == global_agent
                    assert path.exists()
            finally:
                os.chdir(original_cwd)


class TestResolveWorkflowPath:
    """Test resolve_workflow_path function."""

    def test_resolve_package_workflow(self):
        """Test resolving workflow from package templates."""
        path = resolve_workflow_path("default")
        assert path is not None
        assert path.exists()
        assert path.name == "default.yaml"

    def test_resolve_nonexistent_workflow(self):
        """Test resolving nonexistent workflow returns None."""
        path = resolve_workflow_path("nonexistent-workflow-xyz")
        assert path is None

    def test_resolve_local_workflow(self):
        """Test resolving workflow from local project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Create local workflow
                local_workflow_dir = Path(tmpdir) / ".ensemble" / "workflows"
                local_workflow_dir.mkdir(parents=True)
                local_workflow = local_workflow_dir / "custom.yaml"
                local_workflow.write_text("name: custom\nsteps: []\n")

                path = resolve_workflow_path("custom")
                assert path == local_workflow
                assert path.exists()
            finally:
                os.chdir(original_cwd)

    def test_resolve_global_workflow(self):
        """Test resolving workflow from global config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global workflow
            global_dir = Path(tmpdir) / "global"
            global_workflow_dir = global_dir / "workflows"
            global_workflow_dir.mkdir(parents=True)
            global_workflow = global_workflow_dir / "custom-global.yaml"
            global_workflow.write_text("name: custom-global\nsteps: []\n")

            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("ensemble.config.get_global_config_dir", return_value=global_dir):
                    path = resolve_workflow_path("custom-global")
                    assert path == global_workflow
                    assert path.exists()
            finally:
                os.chdir(original_cwd)
