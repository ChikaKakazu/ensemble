"""Implementation of the ensemble upgrade command."""

import shutil
import difflib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import click

from ensemble.templates import get_template_path
from ensemble.version_tracker import (
    check_file_modified,
    compute_file_hash,
    load_versions,
    record_file_version,
)

# All template categories: (template_type, glob_pattern, dest_subdir)
TEMPLATE_CATEGORIES: list[tuple[str, str, str]] = [
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


def run_upgrade(dry_run: bool = False, force: bool = False, diff: bool = False) -> None:
    """Run the upgrade command implementation.

    Args:
        dry_run: If True, show what would be updated without making changes.
        force: If True, force update all files, creating backups of modified files.
        diff: If True, show diff of changes before applying.
    """
    project_root = Path.cwd()
    ensemble_dir = project_root / ".ensemble"

    if not ensemble_dir.exists():
        click.echo(click.style("Error: Not an Ensemble project. Run 'ensemble init' first.", fg="red"))
        return

    click.echo("Checking for updates...\n")

    # Check if --full was used (local agent definitions exist)
    claude_agents_dir = project_root / ".claude" / "agents"
    if not claude_agents_dir.exists():
        click.echo(click.style("No local agent definitions found.", fg="yellow"))
        click.echo("This project was initialized without --full flag.")
        click.echo("Agent definitions will be used from the package.\n")
        click.echo("To customize agents locally, run: ensemble init --full --force")
        return

    # Collect files to update from all template categories
    files_to_update = []
    for template_type, glob_pattern, dest_subdir in TEMPLATE_CATEGORIES:
        files_to_update.extend(
            _scan_category(template_type, glob_pattern, dest_subdir, project_root)
        )

    # Also scan settings.json (single file, not a directory)
    files_to_update.extend(_scan_settings_json(project_root))

    if not files_to_update:
        click.echo(click.style("All files are up to date!", fg="green"))
        return

    # Display what will be updated
    click.echo("Files to update:")
    for status, relative_path, reason in files_to_update:
        icon = _get_status_icon(status)
        click.echo(f"  {icon} {relative_path} {click.style(reason, fg=_get_status_color(status))}")

    click.echo()

    # Show diff if requested
    if diff:
        _show_diff(files_to_update, project_root)

    # Apply updates unless dry-run
    if dry_run:
        click.echo(click.style("Dry run - no changes made.", fg="yellow"))
        _print_summary(files_to_update, dry_run=True)
    else:
        _apply_updates(files_to_update, project_root, force)
        _print_summary(files_to_update, dry_run=False)


def _scan_category(
    template_type: str,
    glob_pattern: str,
    dest_subdir: str,
    project_root: Path,
) -> List[Tuple[str, str, str]]:
    """Scan a template category and determine what needs updating.

    Args:
        template_type: Template type (e.g., "agents", "hooks/scripts")
        glob_pattern: Glob pattern for files (e.g., "*.md", "*.sh")
        dest_subdir: Destination subdirectory under .claude/ (e.g., "agents", "hooks/scripts")
        project_root: Root directory of the project

    Returns:
        List of (status, relative_path, reason) tuples
        Status can be: "new", "update", "skip", "force_update"
    """
    template_dir = _get_template_path_safe(template_type)
    if template_dir is None or not template_dir.exists():
        return []

    local_dir = project_root / ".claude" / dest_subdir
    if not local_dir.exists():
        return []

    results = []

    for template_file in template_dir.glob(glob_pattern):
        local_file = local_dir / template_file.name
        relative_path = str(local_file.relative_to(project_root))

        if not local_file.exists():
            results.append(("new", relative_path, "(new file)"))
        else:
            # Check if file was modified by user
            if check_file_modified(project_root, relative_path, local_file):
                results.append(("skip", relative_path, "(modified locally, skipping)"))
            else:
                # Check if template has changed
                template_hash = compute_file_hash(template_file)
                local_hash = compute_file_hash(local_file)
                if template_hash != local_hash:
                    results.append(("update", relative_path, "(no local changes)"))
                # else: file is up to date, don't include in list

    return results


def _scan_settings_json(project_root: Path) -> List[Tuple[str, str, str]]:
    """Scan settings.json template and determine if it needs updating.

    Args:
        project_root: Root directory of the project

    Returns:
        List of (status, relative_path, reason) tuples
    """
    template_file = _get_template_path_safe("settings.json")
    if template_file is None or not template_file.exists():
        return []

    local_file = project_root / ".claude" / "settings.json"
    relative_path = str(local_file.relative_to(project_root))

    if not local_file.exists():
        return [("new", relative_path, "(new file)")]

    # Check if file was modified by user
    if check_file_modified(project_root, relative_path, local_file):
        return [("skip", relative_path, "(modified locally, skipping)")]

    # Check if template has changed
    template_hash = compute_file_hash(template_file)
    local_hash = compute_file_hash(local_file)
    if template_hash != local_hash:
        return [("update", relative_path, "(no local changes)")]

    return []


def _get_template_path_safe(template_type: str) -> Optional[Path]:
    """Get template path without raising ValueError for extended types.

    Handles both directory types (e.g., "agents") and file types (e.g., "settings.json").
    """
    try:
        return get_template_path(template_type)
    except ValueError:
        # For types not in the original valid_types, use direct path
        package_dir = Path(__file__).parent.parent / "templates"
        path = package_dir / template_type
        if path.exists():
            return path
        return None


# Keep legacy functions as aliases for backward compatibility
def _scan_directory(template_type: str, project_root: Path) -> List[Tuple[str, str, str]]:
    """Legacy: Scan a template directory (agents/commands only).

    Delegates to _scan_category with *.md glob pattern.
    """
    return _scan_category(template_type, "*.md", template_type, project_root)


def _scan_scripts(project_root: Path) -> List[Tuple[str, str, str]]:
    """Legacy: Scan scripts directory.

    Delegates to _scan_category with correct .claude/scripts/ path.
    """
    return _scan_category("scripts", "*.sh", "scripts", project_root)


def _get_status_icon(status: str) -> str:
    """Get icon for status."""
    icons = {
        "new": "+",
        "update": "✓",
        "skip": "⚠",
        "force_update": "!",
    }
    return icons.get(status, "?")


def _get_status_color(status: str) -> str:
    """Get color for status."""
    colors = {
        "new": "green",
        "update": "green",
        "skip": "yellow",
        "force_update": "red",
    }
    return colors.get(status, "white")


def _show_diff(files_to_update: List[Tuple[str, str, str]], project_root: Path) -> None:
    """Show diff for files that will be updated.

    Args:
        files_to_update: List of (status, relative_path, reason) tuples
        project_root: Root directory of the project
    """
    click.echo(click.style("Showing diffs:", fg="cyan"))
    click.echo()

    for status, relative_path, _ in files_to_update:
        if status == "new":
            continue  # Skip new files (no diff to show)

        if status == "skip":
            continue  # Skip files that won't be updated

        local_file = project_root / relative_path
        template_file = _get_template_file_for_relative_path(relative_path)

        if not template_file or not template_file.exists():
            continue

        click.echo(click.style(f"--- {relative_path}", fg="cyan"))

        with open(local_file, "r") as f:
            local_lines = f.readlines()
        with open(template_file, "r") as f:
            template_lines = f.readlines()

        diff = difflib.unified_diff(
            local_lines,
            template_lines,
            fromfile=f"{relative_path} (current)",
            tofile=f"{relative_path} (new)",
            lineterm="",
        )

        for line in diff:
            if line.startswith("---") or line.startswith("+++"):
                click.echo(click.style(line, fg="cyan"))
            elif line.startswith("-"):
                click.echo(click.style(line, fg="red"))
            elif line.startswith("+"):
                click.echo(click.style(line, fg="green"))
            else:
                click.echo(line)

        click.echo()


def _apply_updates(files_to_update: List[Tuple[str, str, str]], project_root: Path, force: bool) -> None:
    """Apply updates to files.

    Args:
        files_to_update: List of (status, relative_path, reason) tuples
        project_root: Root directory of the project
        force: If True, force update modified files with backup
    """
    for status, relative_path, _ in files_to_update:
        local_file = project_root / relative_path

        # Skip modified files unless force is enabled
        if status == "skip":
            if not force:
                continue
            # Create backup before overwriting
            _create_backup(local_file)
            status = "force_update"

        template_file = _get_template_file_for_relative_path(relative_path)
        if not template_file or not template_file.exists():
            click.echo(click.style(f"  Warning: Template not found for {relative_path}", fg="yellow"))
            continue

        # Ensure parent directory exists (for new files in new categories)
        local_file.parent.mkdir(parents=True, exist_ok=True)

        # Copy file from template
        shutil.copy(template_file, local_file)

        # Make shell scripts executable
        if local_file.suffix == ".sh":
            local_file.chmod(0o755)

        # Record new version
        record_file_version(project_root, relative_path, local_file)


def _create_backup(file_path: Path) -> None:
    """Create a backup of a file.

    Args:
        file_path: Path to the file to backup
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f".backup_{timestamp}{file_path.suffix}")
    shutil.copy(file_path, backup_path)
    click.echo(f"  Created backup: {backup_path.name}")


def _get_template_file_for_relative_path(relative_path: str) -> Optional[Path]:
    """Get template file path for a relative path.

    Args:
        relative_path: Relative path like ".claude/agents/conductor.md",
                       ".claude/hooks/scripts/session-scan.sh",
                       or ".claude/settings.json"

    Returns:
        Path to the template file, or None if not found
    """
    parts = Path(relative_path).parts

    # Handle .claude/ directory
    if ".claude" in parts:
        idx = parts.index(".claude")
        remaining = parts[idx + 1:]  # Everything after .claude/

        if not remaining:
            return None

        # Handle settings.json (single file directly under .claude/)
        if len(remaining) == 1:
            filename = remaining[0]
            template_path = _get_template_path_safe(filename)
            if template_path and template_path.is_file():
                return template_path
            return None

        # Handle nested paths like hooks/scripts/session-scan.sh
        # and simple paths like agents/conductor.md
        filename = remaining[-1]
        template_type = "/".join(remaining[:-1])  # e.g., "agents" or "hooks/scripts"

        template_dir = _get_template_path_safe(template_type)
        if template_dir and template_dir.is_dir():
            return template_dir / filename

    return None


def _print_summary(files_to_update: List[Tuple[str, str, str]], dry_run: bool) -> None:
    """Print summary of what was (or would be) updated.

    Args:
        files_to_update: List of (status, relative_path, reason) tuples
        dry_run: Whether this was a dry run
    """
    new_count = sum(1 for s, _, _ in files_to_update if s == "new")
    update_count = sum(1 for s, _, _ in files_to_update if s == "update")
    skip_count = sum(1 for s, _, _ in files_to_update if s == "skip")
    force_count = sum(1 for s, _, _ in files_to_update if s == "force_update")

    verb = "Would update" if dry_run else "Updated"
    click.echo(
        f"{verb} {update_count} file{'s' if update_count != 1 else ''}, "
        f"{'would add' if dry_run else 'added'} {new_count} new file{'s' if new_count != 1 else ''}, "
        f"skipped {skip_count} modified file{'s' if skip_count != 1 else ''}."
    )

    if force_count > 0:
        click.echo(f"Force updated {force_count} modified file{'s' if force_count != 1 else ''} with backups.")

    if skip_count > 0 and not dry_run:
        click.echo(click.style("\nTip: Use --force to update modified files (backups will be created).", fg="cyan"))
