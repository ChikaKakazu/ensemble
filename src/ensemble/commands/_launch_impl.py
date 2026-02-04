"""Implementation of the ensemble launch command."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

from ensemble.templates import get_template_path


def run_launch(session: str = "ensemble", attach: bool = True) -> None:
    """Run the launch command implementation.

    Args:
        session: Name of the tmux session.
        attach: Whether to attach to the session after creation.
    """
    # Check prerequisites
    if not _check_tmux():
        click.echo(click.style("Error: tmux is not installed or not in PATH", fg="red"))
        sys.exit(1)

    if not _check_claude():
        click.echo(click.style("Error: claude CLI is not installed or not in PATH", fg="red"))
        click.echo("Install Claude Code from: https://claude.ai/code")
        sys.exit(1)

    # Check if session already exists
    if _session_exists(session):
        click.echo(f"Session '{session}' already exists.")
        if attach:
            click.echo(f"Attaching to existing session...")
            _attach_session(session)
        return

    project_root = Path.cwd()
    ensemble_dir = project_root / ".ensemble"

    # Verify project is initialized
    if not ensemble_dir.exists():
        click.echo(click.style("Error: Project not initialized for Ensemble", fg="red"))
        click.echo("Run 'ensemble init' first")
        sys.exit(1)

    click.echo(f"Launching Ensemble session '{session}'...")

    # Get agent paths
    agents = _resolve_agent_paths(project_root)

    # Create tmux session with 2-window layout
    _create_session(session, project_root, agents)

    # Save pane IDs
    _save_pane_ids(session, ensemble_dir)

    click.echo(click.style("Ensemble session started!", fg="green"))
    click.echo("")
    click.echo("Window 1: conductor (user interaction)")
    click.echo("Window 2: workers (dispatch, dashboard, workers)")
    click.echo("")
    click.echo("Window switching: Ctrl+B, n/p or Ctrl+B, 0/1")

    if attach:
        _attach_session(session)


def _check_tmux() -> bool:
    """Check if tmux is available."""
    return shutil.which("tmux") is not None


def _check_claude() -> bool:
    """Check if claude CLI is available."""
    return shutil.which("claude") is not None


def _session_exists(session: str) -> bool:
    """Check if a tmux session exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    return result.returncode == 0


def _attach_session(session: str) -> None:
    """Attach to an existing tmux session."""
    os.execvp("tmux", ["tmux", "attach-session", "-t", session])


def _resolve_agent_paths(project_root: Path) -> dict[str, Path]:
    """Resolve agent definition paths with priority.

    Priority order:
    1. Local project: ./.claude/agents/
    2. Global config: ~/.config/ensemble/agents/
    3. Package templates
    """
    agents = {}
    agent_names = ["conductor", "dispatch", "worker", "reviewer", "security-reviewer", "integrator", "learner"]

    local_agents = project_root / ".claude" / "agents"
    global_agents = Path.home() / ".config" / "ensemble" / "agents"
    template_agents = get_template_path("agents")

    for name in agent_names:
        filename = f"{name}.md"

        # Check local first
        local_path = local_agents / filename
        if local_path.exists():
            agents[name] = local_path
            continue

        # Check global
        global_path = global_agents / filename
        if global_path.exists():
            agents[name] = global_path
            continue

        # Fall back to template
        template_path = template_agents / filename
        if template_path.exists():
            agents[name] = template_path

    return agents


def _create_session(session: str, project_root: Path, agents: dict[str, Path]) -> None:
    """Create the tmux session with 2-window Ensemble layout.

    Layout:
    Window 1 (conductor): Full screen conductor
    Window 2 (workers):
        +------------------+----------+
        |    dispatch      | (worker) |
        +------------------+----------+
        |    dashboard     | (worker) |
        +------------------+----------+
    """
    # Create new session with conductor window (detached)
    subprocess.run(
        [
            "tmux", "new-session",
            "-d",
            "-s", session,
            "-c", str(project_root),
            "-n", "conductor",
        ],
        check=True,
    )

    # Start Claude in Conductor pane
    conductor_agent = agents.get("conductor")
    if conductor_agent:
        cmd = f"claude --agent {conductor_agent}"
    else:
        cmd = "claude"
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{session}:conductor", cmd, "Enter"],
        check=True,
    )

    # Create workers window
    subprocess.run(
        [
            "tmux", "new-window",
            "-t", session,
            "-c", str(project_root),
            "-n", "workers",
        ],
        check=True,
    )

    # Split workers window: left/right (60/40)
    subprocess.run(
        ["tmux", "split-window", "-t", f"{session}:workers", "-h", "-l", "40%", "-c", str(project_root)],
        check=True,
    )

    # Split left pane vertically (dispatch/dashboard)
    subprocess.run(
        ["tmux", "split-window", "-t", f"{session}:workers.0", "-v", "-l", "50%", "-c", str(project_root)],
        check=True,
    )

    # Set pane titles
    subprocess.run(["tmux", "select-pane", "-t", f"{session}:workers.0", "-T", "dispatch"], check=True)
    subprocess.run(["tmux", "select-pane", "-t", f"{session}:workers.1", "-T", "dashboard"], check=True)
    subprocess.run(["tmux", "select-pane", "-t", f"{session}:workers.2", "-T", "worker-area"], check=True)

    # Start Claude in Dispatch pane (pane 0 - left top)
    dispatch_agent = agents.get("dispatch")
    if dispatch_agent:
        cmd = f"claude --agent {dispatch_agent}"
    else:
        cmd = "claude"
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{session}:workers.0", cmd, "Enter"],
        check=True,
    )

    # Start dashboard watch in Dashboard pane (pane 1 - left bottom)
    dashboard_path = project_root / ".ensemble" / "status" / "dashboard.md"
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{session}:workers.1", f"watch -n 2 cat {dashboard_path}", "Enter"],
        check=True,
    )

    # Show placeholder message in worker area (pane 2 - right)
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{session}:workers.2", "echo '=== Worker Area ===' && echo 'Workers will be started here.'", "Enter"],
        check=True,
    )

    # Select conductor window and pane
    subprocess.run(["tmux", "select-window", "-t", f"{session}:conductor"], check=True)
    subprocess.run(["tmux", "select-pane", "-t", f"{session}:conductor.0"], check=True)


def _save_pane_ids(session: str, ensemble_dir: Path) -> None:
    """Save pane IDs to panes.env file."""
    # Get conductor pane ID
    result = subprocess.run(
        ["tmux", "list-panes", "-t", f"{session}:conductor", "-F", "#{pane_id}"],
        capture_output=True,
        text=True,
        check=True,
    )
    conductor_pane = result.stdout.strip()

    # Get workers pane IDs
    result = subprocess.run(
        ["tmux", "list-panes", "-t", f"{session}:workers", "-F", "#{pane_index}:#{pane_id}"],
        capture_output=True,
        text=True,
        check=True,
    )

    pane_map = {}
    for line in result.stdout.strip().split("\n"):
        if ":" in line:
            idx, pane_id = line.split(":", 1)
            pane_map[int(idx)] = pane_id

    # Write panes.env
    panes_env = ensemble_dir / "panes.env"
    with open(panes_env, "w") as f:
        f.write("# Ensemble pane IDs (auto-generated)\n")
        f.write("# Window names\n")
        f.write("CONDUCTOR_WINDOW=conductor\n")
        f.write("WORKERS_WINDOW=workers\n")
        f.write("\n")
        f.write("# Pane IDs\n")
        f.write(f"CONDUCTOR_PANE={conductor_pane}\n")
        f.write(f"DISPATCH_PANE={pane_map.get(0, '%0')}\n")
        f.write(f"DASHBOARD_PANE={pane_map.get(1, '%1')}\n")
        f.write(f"WORKER_AREA_PANE={pane_map.get(2, '%2')}\n")

    click.echo(f"  Saved pane IDs to {panes_env.relative_to(ensemble_dir.parent)}")
