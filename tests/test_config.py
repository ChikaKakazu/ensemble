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
