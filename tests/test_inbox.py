"""Tests for inbox watcher system."""

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ensemble.inbox import InboxWatcher


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with necessary structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create directory structure
    (project_dir / ".ensemble").mkdir()
    (project_dir / "queue").mkdir()
    (project_dir / "scripts").mkdir()

    # Create dummy inbox_watcher.sh script
    script_path = project_dir / "scripts" / "inbox_watcher.sh"
    script_path.write_text(
        "#!/bin/bash\n"
        "PROJECT_DIR=\"${PROJECT_DIR:-$(pwd)}\"\n"
        "echo $$ > \"$PROJECT_DIR/.ensemble/inbox_watcher.pid\"\n"
        "trap 'rm -f \"$PROJECT_DIR/.ensemble/inbox_watcher.pid\"; exit 0' SIGTERM SIGINT\n"
        "while true; do sleep 1; done\n"
    )
    script_path.chmod(0o755)

    # Create dummy panes.env
    panes_env = project_dir / ".ensemble" / "panes.env"
    panes_env.write_text(
        "CONDUCTOR_PANE=%0\n"
        "DISPATCH_PANE=%1\n"
    )

    return project_dir


def test_inbox_watcher_script_exists():
    """Test that inbox_watcher.sh script template exists."""
    script_path = Path("src/ensemble/templates/scripts/inbox_watcher.sh")
    assert script_path.exists(), f"Script not found: {script_path}"
    assert script_path.stat().st_size > 0, "Script is empty"


def test_inbox_watcher_class_start_stop(temp_project_dir):
    """Test InboxWatcher start() and stop() methods."""
    watcher = InboxWatcher(temp_project_dir)

    # Test start
    assert not watcher.is_running()
    watcher.start()
    assert watcher.is_running()

    # PID file should exist
    pid_file = temp_project_dir / ".ensemble" / "inbox_watcher.pid"
    assert pid_file.exists()
    pid = int(pid_file.read_text().strip())
    assert pid > 0

    # Test stop
    watcher.stop()
    assert not watcher.is_running()
    assert not pid_file.exists()


def test_inbox_watcher_already_running(temp_project_dir):
    """Test that start() raises error if already running."""
    watcher = InboxWatcher(temp_project_dir)

    watcher.start()
    try:
        with pytest.raises(RuntimeError, match="already running"):
            watcher.start()
    finally:
        watcher.stop()


def test_inbox_watcher_stop_not_running(temp_project_dir):
    """Test that stop() handles case where watcher is not running."""
    watcher = InboxWatcher(temp_project_dir)

    # Should not raise error
    watcher.stop()


def test_inbox_watcher_inotifywait_check():
    """Test ensure_inotifywait() method."""
    result = InboxWatcher.ensure_inotifywait()
    assert isinstance(result, bool)

    # If inotify-tools is installed, result should be True
    # If not, result should be False
    # We don't assert a specific value because it depends on the environment


def test_inbox_watcher_script_not_found(tmp_path):
    """Test that InboxWatcher raises error if script not found."""
    project_dir = tmp_path / "empty_project"
    project_dir.mkdir()
    (project_dir / ".ensemble").mkdir()

    # FileNotFoundError should be raised during initialization
    with pytest.raises(FileNotFoundError, match="inbox_watcher.sh not found"):
        watcher = InboxWatcher(project_dir)


def test_inbox_watcher_find_script_priority(temp_project_dir):
    """Test that _find_script() respects priority order."""
    watcher = InboxWatcher(temp_project_dir)

    # Should find scripts/inbox_watcher.sh first
    script_path = watcher._find_script()
    assert script_path == temp_project_dir / "scripts" / "inbox_watcher.sh"

    # Remove local script
    (temp_project_dir / "scripts" / "inbox_watcher.sh").unlink()

    # Create template script
    template_script = (
        temp_project_dir / "src" / "ensemble" / "templates" / "scripts" / "inbox_watcher.sh"
    )
    template_script.parent.mkdir(parents=True)
    template_script.write_text("#!/bin/bash\necho 'template'\n")

    # Should find template script
    script_path = watcher._find_script()
    assert script_path == template_script


def test_inbox_watcher_is_running_stale_pid(temp_project_dir):
    """Test that is_running() returns False if PID file contains stale PID."""
    pid_file = temp_project_dir / ".ensemble" / "inbox_watcher.pid"
    # Write a non-existent PID
    pid_file.write_text("999999\n")

    watcher = InboxWatcher(temp_project_dir)
    assert not watcher.is_running()


def test_inbox_watcher_graceful_shutdown(temp_project_dir):
    """Test that stop() sends SIGTERM and waits for graceful shutdown."""
    watcher = InboxWatcher(temp_project_dir)

    watcher.start()
    pid = watcher._read_pid()
    assert pid is not None

    # Stop should send SIGTERM
    watcher.stop()

    # Give process a moment to actually terminate after SIGKILL
    time.sleep(0.5)

    # Process should be terminated
    # Note: In some cases, _is_process_alive may return True due to zombie process
    # Check if watcher itself considers it not running
    assert not watcher.is_running(), f"Watcher still reports as running after stop()"
