"""Ensemble templates package.

Provides access to bundled agent definitions, commands, workflows, and scripts.
"""

from importlib import resources
from pathlib import Path
from typing import Optional


def get_template_path(template_type: str) -> Path:
    """Get the path to a template directory.

    Args:
        template_type: One of "agents", "commands", "workflows", "scripts"

    Returns:
        Path to the template directory

    Raises:
        ValueError: If template_type is not valid
    """
    valid_types = {"agents", "commands", "workflows", "scripts"}
    if template_type not in valid_types:
        raise ValueError(f"Invalid template type: {template_type}. Must be one of {valid_types}")

    # Use importlib.resources for Python 3.9+
    try:
        # Python 3.9+ style
        with resources.as_file(resources.files("ensemble.templates") / template_type) as path:
            return Path(path)
    except (TypeError, AttributeError):
        # Fallback for older Python or edge cases
        package_dir = Path(__file__).parent
        return package_dir / template_type


def get_template_file(template_type: str, filename: str) -> Optional[Path]:
    """Get the path to a specific template file.

    Args:
        template_type: One of "agents", "commands", "workflows", "scripts"
        filename: Name of the file within the template directory

    Returns:
        Path to the template file, or None if not found
    """
    template_dir = get_template_path(template_type)
    file_path = template_dir / filename

    if file_path.exists():
        return file_path
    return None


def list_templates(template_type: str) -> list[str]:
    """List all template files of a given type.

    Args:
        template_type: One of "agents", "commands", "workflows", "scripts"

    Returns:
        List of template filenames
    """
    template_dir = get_template_path(template_type)
    if not template_dir.exists():
        return []

    if template_type in ("agents", "commands"):
        return [f.name for f in template_dir.glob("*.md")]
    elif template_type == "workflows":
        return [f.name for f in template_dir.glob("*.yaml")]
    elif template_type == "scripts":
        return [f.name for f in template_dir.glob("*.sh")]
    return []
