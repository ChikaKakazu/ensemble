"""Ensemble configuration management.

Handles global (~/.config/ensemble/) and local (.ensemble/) configuration.
"""

import shutil
from pathlib import Path
from typing import Any, Optional

import yaml

from ensemble.templates import get_template_path

# Default configuration values
DEFAULT_CONFIG = {
    "version": "0.3.0",
    "session": {
        "name": "ensemble",
        "attach": True,
    },
    "agents": {
        "conductor": "conductor.md",
        "dispatch": "dispatch.md",
        "worker": "worker.md",
        "reviewer": "reviewer.md",
        "security_reviewer": "security-reviewer.md",
        "integrator": "integrator.md",
        "learner": "learner.md",
    },
    "workflow": {
        "default": "default.yaml",
        "simple": "simple.yaml",
        "heavy": "heavy.yaml",
        "worktree": "worktree.yaml",
    },
    "limits": {
        "max_parallel_workers": 4,
        "max_iterations": 15,
    },
}


def get_global_config_dir() -> Path:
    """Get the global configuration directory path."""
    return Path.home() / ".config" / "ensemble"


def get_local_config_dir() -> Path:
    """Get the local configuration directory path (current project)."""
    return Path.cwd() / ".ensemble"


def ensure_global_config() -> Path:
    """Ensure global configuration directory exists with defaults.

    Creates ~/.config/ensemble/ with default templates if it doesn't exist.

    Returns:
        Path to the global config directory
    """
    global_dir = get_global_config_dir()

    if not global_dir.exists():
        global_dir.mkdir(parents=True, exist_ok=True)

        # Copy default config
        _write_default_config(global_dir / "config.yaml")

        # Copy agent templates
        _copy_default_templates(global_dir)

    return global_dir


def _write_default_config(config_path: Path) -> None:
    """Write default configuration to file."""
    with open(config_path, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)


def _copy_default_templates(global_dir: Path) -> None:
    """Copy default templates to global config directory."""
    # Copy agents
    agents_dir = global_dir / "agents"
    agents_dir.mkdir(exist_ok=True)

    template_agents = get_template_path("agents")
    if template_agents.exists():
        for agent_file in template_agents.glob("*.md"):
            shutil.copy(agent_file, agents_dir / agent_file.name)

    # Copy workflows
    workflows_dir = global_dir / "workflows"
    workflows_dir.mkdir(exist_ok=True)

    template_workflows = get_template_path("workflows")
    if template_workflows.exists():
        for workflow_file in template_workflows.glob("*.yaml"):
            shutil.copy(workflow_file, workflows_dir / workflow_file.name)


def load_config() -> dict[str, Any]:
    """Load merged configuration (global + local).

    Priority (highest first):
    1. Local project config (.ensemble/config.yaml)
    2. Global config (~/.config/ensemble/config.yaml)
    3. Default values

    Returns:
        Merged configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()

    # Load global config
    global_config_file = get_global_config_dir() / "config.yaml"
    if global_config_file.exists():
        with open(global_config_file) as f:
            global_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, global_config)

    # Load local config (overrides global)
    local_config_file = get_local_config_dir() / "config.yaml"
    if local_config_file.exists():
        with open(local_config_file) as f:
            local_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, local_config)

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with overriding values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def resolve_agent_path(agent_name: str) -> Optional[Path]:
    """Resolve the path to an agent definition file.

    Priority (highest first):
    1. Local project: ./.claude/agents/{agent}.md
    2. Global config: ~/.config/ensemble/agents/{agent}.md
    3. Package template: ensemble/templates/agents/{agent}.md

    Args:
        agent_name: Name of the agent (e.g., "conductor", "dispatch")

    Returns:
        Path to the agent file, or None if not found
    """
    filename = f"{agent_name}.md"

    # Check local
    local_path = Path.cwd() / ".claude" / "agents" / filename
    if local_path.exists():
        return local_path

    # Check global
    global_path = get_global_config_dir() / "agents" / filename
    if global_path.exists():
        return global_path

    # Check package template
    template_path = get_template_path("agents") / filename
    if template_path.exists():
        return template_path

    return None


def resolve_workflow_path(workflow_name: str) -> Optional[Path]:
    """Resolve the path to a workflow definition file.

    Priority (highest first):
    1. Local project: ./.ensemble/workflows/{workflow}.yaml
    2. Global config: ~/.config/ensemble/workflows/{workflow}.yaml
    3. Package template: ensemble/templates/workflows/{workflow}.yaml

    Args:
        workflow_name: Name of the workflow (e.g., "default", "simple")

    Returns:
        Path to the workflow file, or None if not found
    """
    filename = f"{workflow_name}.yaml"

    # Check local
    local_path = Path.cwd() / ".ensemble" / "workflows" / filename
    if local_path.exists():
        return local_path

    # Check global
    global_path = get_global_config_dir() / "workflows" / filename
    if global_path.exists():
        return global_path

    # Check package template
    template_path = get_template_path("workflows") / filename
    if template_path.exists():
        return template_path

    return None
