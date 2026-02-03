"""Tests for Ensemble templates module."""

import pytest

from ensemble.templates import get_template_path, get_template_file, list_templates


class TestGetTemplatePath:
    """Test get_template_path function."""

    def test_get_agents_path(self):
        """Test getting agents template path."""
        path = get_template_path("agents")
        assert path.exists()
        assert path.is_dir()
        assert (path / "conductor.md").exists()

    def test_get_commands_path(self):
        """Test getting commands template path."""
        path = get_template_path("commands")
        assert path.exists()
        assert path.is_dir()
        assert (path / "go.md").exists()

    def test_get_workflows_path(self):
        """Test getting workflows template path."""
        path = get_template_path("workflows")
        assert path.exists()
        assert path.is_dir()
        assert (path / "default.yaml").exists()

    def test_get_scripts_path(self):
        """Test getting scripts template path."""
        path = get_template_path("scripts")
        assert path.exists()
        assert path.is_dir()
        assert (path / "launch.sh").exists()

    def test_invalid_template_type(self):
        """Test that invalid template type raises error."""
        with pytest.raises(ValueError):
            get_template_path("invalid")


class TestGetTemplateFile:
    """Test get_template_file function."""

    def test_get_existing_file(self):
        """Test getting an existing template file."""
        path = get_template_file("agents", "conductor.md")
        assert path is not None
        assert path.exists()
        assert path.name == "conductor.md"

    def test_get_nonexistent_file(self):
        """Test getting a nonexistent template file."""
        path = get_template_file("agents", "nonexistent.md")
        assert path is None


class TestListTemplates:
    """Test list_templates function."""

    def test_list_agents(self):
        """Test listing agent templates."""
        templates = list_templates("agents")
        assert len(templates) >= 7
        assert "conductor.md" in templates
        assert "dispatch.md" in templates
        assert "worker.md" in templates

    def test_list_commands(self):
        """Test listing command templates."""
        templates = list_templates("commands")
        assert len(templates) >= 5
        assert "go.md" in templates
        assert "status.md" in templates

    def test_list_workflows(self):
        """Test listing workflow templates."""
        templates = list_templates("workflows")
        assert len(templates) >= 4
        assert "default.yaml" in templates
        assert "simple.yaml" in templates

    def test_list_scripts(self):
        """Test listing script templates."""
        templates = list_templates("scripts")
        assert len(templates) >= 4
        assert "launch.sh" in templates
