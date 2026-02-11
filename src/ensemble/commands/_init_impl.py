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
                # Write back content with section removed, then append new section
                with open(claude_md, "w") as f:
                    f.write(content)
                    f.write(ensemble_section)
                click.echo("  Updated CLAUDE.md with Ensemble section")
                return
            else:
                click.echo("  CLAUDE.md already contains Ensemble section (use --force to overwrite)")
                return

        # Append Ensemble section (first time)
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
    click.echo("  Created .ensemble/status/dashboard.md")

    # Also create status/dashboard.md at project root for backward compatibility
    # (agent definitions and scripts reference status/dashboard.md)
    project_root = ensemble_dir.parent
    root_status_dir = project_root / "status"
    root_status_dir.mkdir(parents=True, exist_ok=True)
    root_dashboard = root_status_dir / "dashboard.md"
    root_dashboard.write_text(content)
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
    """Copy all Ensemble templates to local .claude/ directory.

    Copies agents, commands, scripts, workflows, instructions, policies,
    personas, output-contracts, knowledge, skills, hooks, and rules.
    """
    click.echo("\nCopying Ensemble templates for local customization...")

    # Template categories that map to .claude/ subdirectories
    # (template_type, glob_pattern, dest_subdir)
    template_categories: list[tuple[str, str, str]] = [
        ("agents", "*.md", "agents"),
        ("commands", "*.md", "commands"),
        ("scripts", "*.sh", "scripts"),
        ("workflows", "*.yaml", "workflows"),
        ("instructions", "*.md", "instructions"),
        ("policies", "*.md", "policies"),
        ("personas", "*.md", "personas"),
        ("output-contracts", "*.md", "output-contracts"),
        ("knowledge", "*.md", "knowledge"),
        ("skills", "*.md", "skills"),
        ("hooks/scripts", "*.sh", "hooks/scripts"),
        ("rules", "*.md", "rules"),
    ]

    copied = 0
    skipped = 0

    for template_type, glob_pattern, dest_subdir in template_categories:
        template_dir = _get_template_path_safe(template_type)
        if template_dir is None or not template_dir.exists():
            continue

        dest_dir = project_root / ".claude" / dest_subdir
        dest_dir.mkdir(parents=True, exist_ok=True)

        files = list(template_dir.glob(glob_pattern))
        if not files:
            continue

        for src_file in files:
            dest = dest_dir / src_file.name
            if dest.exists() and not force:
                skipped += 1
                continue
            shutil.copy(src_file, dest)
            # Make shell scripts executable
            if src_file.suffix == ".sh":
                dest.chmod(0o755)
            # Record file version for upgrade tracking
            relative_path = str(dest.relative_to(project_root))
            record_file_version(project_root, relative_path, dest)
            copied += 1
            click.echo(f"  Copied {dest_subdir}/{src_file.name}")

    # Copy settings.json template
    settings_template = _get_template_path_safe("settings.json")
    if settings_template and settings_template.exists():
        dest = project_root / ".claude" / "settings.json"
        if not dest.exists() or force:
            shutil.copy(settings_template, dest)
            copied += 1
            click.echo("  Copied settings.json")
        else:
            skipped += 1

    click.echo(f"\n  Total: {copied} copied, {skipped} skipped (use --force to overwrite)")


def _get_template_path_safe(template_type: str) -> Optional[Path]:
    """Get template path without raising ValueError for extended types."""
    try:
        return get_template_path(template_type)
    except ValueError:
        # For types not in the original valid_types, use direct path
        package_dir = Path(__file__).parent.parent / "templates"
        path = package_dir / template_type
        if path.exists():
            return path
        return None
