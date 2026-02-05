"""Implementation of the ensemble init command."""

import shutil
from pathlib import Path
from typing import Optional

import click

from ensemble.templates import get_template_path
from ensemble.version_tracker import record_file_version


def run_init(full: bool = False, force: bool = False) -> None:
    """Run the init command implementation.

    Args:
        full: If True, copy all agent definitions locally.
        force: If True, overwrite existing files.
    """
    project_root = Path.cwd()
    ensemble_dir = project_root / ".ensemble"

    click.echo(f"Initializing Ensemble in {project_root}")

    # Create directory structure
    _create_directories(ensemble_dir)

    # Create CLAUDE.md or append Ensemble section
    _setup_claude_md(project_root, force)

    # Update .gitignore
    _update_gitignore(project_root)

    # Create initial dashboard
    _create_dashboard(ensemble_dir)

    # Create panes.env placeholder
    _create_panes_env(ensemble_dir)

    # If --full, copy agent definitions
    if full:
        _copy_agent_definitions(project_root, force)

    click.echo(click.style("Ensemble initialized successfully!", fg="green"))
    click.echo("\nNext steps:")
    click.echo("  1. Run 'ensemble launch' to start the tmux session")
    click.echo("  2. Use '/go <task>' to begin orchestration")


def _create_directories(ensemble_dir: Path) -> None:
    """Create the .ensemble directory structure."""
    dirs = [
        ensemble_dir,
        ensemble_dir / "queue" / "conductor",
        ensemble_dir / "queue" / "tasks",
        ensemble_dir / "queue" / "reports",
        ensemble_dir / "queue" / "ack",
        ensemble_dir / "status",
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        click.echo(f"  Created {dir_path.relative_to(ensemble_dir.parent)}")


def _setup_claude_md(project_root: Path, force: bool) -> None:
    """Create or update CLAUDE.md with Ensemble section."""
    claude_md = project_root / "CLAUDE.md"
    ensemble_section = '''
## Ensemble AI Orchestration

This project uses Ensemble for AI-powered development orchestration.

### Quick Start
- `/go <task>` - Start a task with automatic planning and execution
- `/go-light <task>` - Lightweight execution for simple changes
- `/status` - View current progress

### Communication Protocol
- Agent communication via file-based queue (.ensemble/queue/)
- Dashboard updates in .ensemble/status/dashboard.md

For more information, see the [Ensemble documentation](https://github.com/ChikaKakazu/ensemble).
'''

    if claude_md.exists():
        content = claude_md.read_text()
        if "## Ensemble AI Orchestration" in content:
            if force:
                # Remove existing section and re-add
                lines = content.split("\n")
                new_lines = []
                skip = False
                for line in lines:
                    if line.startswith("## Ensemble AI Orchestration"):
                        skip = True
                        continue
                    if skip and line.startswith("## "):
                        skip = False
                    if not skip:
                        new_lines.append(line)
                content = "\n".join(new_lines)
            else:
                click.echo("  CLAUDE.md already contains Ensemble section (use --force to overwrite)")
                return

        # Append Ensemble section
        with open(claude_md, "a") as f:
            f.write(ensemble_section)
        click.echo("  Updated CLAUDE.md with Ensemble section")
    else:
        # Create new CLAUDE.md
        with open(claude_md, "w") as f:
            f.write(f"# {project_root.name}\n")
            f.write(ensemble_section)
        click.echo("  Created CLAUDE.md")


def _update_gitignore(project_root: Path) -> None:
    """Update .gitignore with Ensemble exclusions."""
    gitignore = project_root / ".gitignore"
    ensemble_ignores = """
# Ensemble
.ensemble/queue/
.ensemble/panes.env
"""

    if gitignore.exists():
        content = gitignore.read_text()
        if "# Ensemble" in content:
            click.echo("  .gitignore already contains Ensemble section")
            return
        with open(gitignore, "a") as f:
            f.write(ensemble_ignores)
        click.echo("  Updated .gitignore")
    else:
        with open(gitignore, "w") as f:
            f.write(ensemble_ignores.strip() + "\n")
        click.echo("  Created .gitignore")


def _create_dashboard(ensemble_dir: Path) -> None:
    """Create initial dashboard.md."""
    dashboard = ensemble_dir / "status" / "dashboard.md"
    content = """# Ensemble Dashboard

## Current Task
None

## Execution Status
| Pane/Worktree | Status | Agent | Progress |
|---|---|---|---|
| - | idle | - | - |

## Recent Completed Tasks
| Task | Result | Completed |
|------|--------|-----------|
| - | - | - |

---
*Last updated: -
"""
    dashboard.write_text(content)
    click.echo("  Created status/dashboard.md")


def _create_panes_env(ensemble_dir: Path) -> None:
    """Create panes.env placeholder."""
    panes_env = ensemble_dir / "panes.env"
    content = """# Ensemble pane IDs (auto-generated by launch)
# This file will be populated when 'ensemble launch' is run
"""
    panes_env.write_text(content)
    click.echo("  Created panes.env placeholder")


def _copy_agent_definitions(project_root: Path, force: bool) -> None:
    """Copy agent definitions to local .claude/agents/."""
    click.echo("\nCopying agent definitions for local customization...")

    claude_agents_dir = project_root / ".claude" / "agents"
    claude_agents_dir.mkdir(parents=True, exist_ok=True)

    template_agents = get_template_path("agents")
    if not template_agents.exists():
        click.echo(click.style("  Warning: Agent templates not found", fg="yellow"))
        return

    for agent_file in template_agents.glob("*.md"):
        dest = claude_agents_dir / agent_file.name
        if dest.exists() and not force:
            click.echo(f"  Skipped {agent_file.name} (exists, use --force to overwrite)")
            continue
        shutil.copy(agent_file, dest)
        # Record file version for upgrade tracking
        relative_path = str(dest.relative_to(project_root))
        record_file_version(project_root, relative_path, dest)
        click.echo(f"  Copied {agent_file.name}")

    # Also copy commands
    claude_commands_dir = project_root / ".claude" / "commands"
    claude_commands_dir.mkdir(parents=True, exist_ok=True)

    template_commands = get_template_path("commands")
    if template_commands.exists():
        for cmd_file in template_commands.glob("*.md"):
            dest = claude_commands_dir / cmd_file.name
            if dest.exists() and not force:
                click.echo(f"  Skipped {cmd_file.name} (exists)")
                continue
            shutil.copy(cmd_file, dest)
            # Record file version for upgrade tracking
            relative_path = str(dest.relative_to(project_root))
            record_file_version(project_root, relative_path, dest)
            click.echo(f"  Copied {cmd_file.name}")
