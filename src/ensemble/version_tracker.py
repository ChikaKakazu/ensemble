"""Version tracking for Ensemble files.

Tracks file hashes to detect user modifications and safely upgrade files.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: Path to the file

    Returns:
        Hex string of the SHA256 hash
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_versions(project_root: Path) -> dict:
    """Load versions.json from .ensemble directory.

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary mapping relative paths to their hashes
    """
    versions_file = project_root / ".ensemble" / "versions.json"
    if not versions_file.exists():
        return {}

    try:
        with open(versions_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_versions(project_root: Path, versions: dict) -> None:
    """Save versions.json to .ensemble directory.

    Args:
        project_root: Root directory of the project
        versions: Dictionary mapping relative paths to their hashes
    """
    versions_file = project_root / ".ensemble" / "versions.json"
    versions_file.parent.mkdir(parents=True, exist_ok=True)

    with open(versions_file, "w") as f:
        json.dump(versions, f, indent=2, sort_keys=True)


def record_file_version(project_root: Path, relative_path: str, file_path: Path) -> None:
    """Record the hash of a file in versions.json.

    Args:
        project_root: Root directory of the project
        relative_path: Relative path from project root (e.g., ".claude/agents/conductor.md")
        file_path: Absolute path to the file
    """
    versions = load_versions(project_root)
    file_hash = compute_file_hash(file_path)
    versions[relative_path] = file_hash
    save_versions(project_root, versions)


def check_file_modified(project_root: Path, relative_path: str, file_path: Path) -> bool:
    """Check if a file has been modified by the user.

    Args:
        project_root: Root directory of the project
        relative_path: Relative path from project root
        file_path: Absolute path to the file

    Returns:
        True if the file has been modified (hash doesn't match), False otherwise
    """
    if not file_path.exists():
        return False

    versions = load_versions(project_root)
    recorded_hash = versions.get(relative_path)

    if recorded_hash is None:
        # No record means it was never tracked
        return True

    current_hash = compute_file_hash(file_path)
    return current_hash != recorded_hash
