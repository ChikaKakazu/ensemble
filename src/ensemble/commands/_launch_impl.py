"""Implementation of the ensemble launch command."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click

from ensemble.templates import get_template_path


def run_launch(session: str = "ensemble", attach: bool = True) -> None:
    """Run the launch command implementation.

    Args:
        session: Base name for the tmux sessions (will create {session}-conductor and {session}-workers).
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

    # Session names
    conductor_session = f"{session}-conductor"
    workers_session = f"{session}-workers"

    # Check if sessions already exist
    conductor_exists = _session_exists(conductor_session)
    workers_exists = _session_exists(workers_session)

    if conductor_exists or workers_exists:
        click.echo("Existing Ensemble sessions found:")
        if conductor_exists:
            click.echo(f"  - {conductor_session}")
        if workers_exists:
            click.echo(f"  - {workers_session}")
        click.echo("")
        click.echo("To attach, open two terminal windows and run:")
        click.echo(f"  Terminal 1: tmux attach -t {conductor_session}")
        click.echo(f"  Terminal 2: tmux attach -t {workers_session}")
        return

    project_root = Path.cwd()
    ensemble_dir = project_root / ".ensemble"

    # Verify project is initialized
    if not ensemble_dir.exists():
        click.echo(click.style("Error: Project not initialized for Ensemble", fg="red"))
        click.echo("Run 'ensemble init' first")
        sys.exit(1)

    click.echo(f"Launching Ensemble sessions '{session}-*'...")

    # Clean up queue directories
    queue_dir = project_root / "queue"
    if queue_dir.exists():
        for subdir in ["tasks", "processing", "reports", "ack"]:
            subdir_path = queue_dir / subdir
            if subdir_path.exists():
                for f in subdir_path.glob("*.yaml"):
                    f.unlink()
                for f in subdir_path.glob("*.ack"):
                    f.unlink()

    # Ensure queue directories exist
    for subdir in ["tasks", "processing", "reports", "ack", "conductor"]:
        (queue_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Get agent paths
    agents = _resolve_agent_paths(project_root)

    # Create tmux sessions (2 separate sessions)
    _create_sessions(session, project_root, agents)

    # Save pane IDs
    _save_pane_ids(session, ensemble_dir)

    click.echo(click.style("Ensemble sessions started!", fg="green"))
    click.echo("")
    click.echo("==========================================")
    click.echo("  Two separate tmux sessions created!")
    click.echo("==========================================")
    click.echo("")
    click.echo(f"Session 1: {conductor_session}")
    click.echo("  +------------------+------------------+")
    click.echo("  |   Conductor      |   dashboard      |")
    click.echo("  +------------------+------------------+")
    click.echo("")
    click.echo(f"Session 2: {workers_session}")
    click.echo("  +------------------+------------------+")
    click.echo("  |   dispatch       |   worker-area    |")
    click.echo("  +------------------+------------------+")
    click.echo("")
    click.echo("To view both simultaneously, open two terminal windows:")
    click.echo(f"  Terminal 1: tmux attach -t {conductor_session}")
    click.echo(f"  Terminal 2: tmux attach -t {workers_session}")
    click.echo("")

    if attach:
        click.echo(f"Attaching to {conductor_session}...")
        click.echo(f"(Open another terminal and run: tmux attach -t {workers_session})")
        click.echo("")
        _attach_session(conductor_session)


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


def _create_sessions(session: str, project_root: Path, agents: dict[str, Path]) -> None:
    """Create two separate tmux sessions for Ensemble.

    Session 1 ({session}-conductor): Conductor (left 60%) + Dashboard (right 40%)
    Session 2 ({session}-workers): Dispatch (left 60%) + Worker area (right 40%)

    This allows viewing both sessions simultaneously in separate terminal windows.
    """
    conductor_session = f"{session}-conductor"
    workers_session = f"{session}-workers"

    # === Session 1: Conductor ===
    subprocess.run(
        [
            "tmux", "new-session",
            "-d",
            "-s", conductor_session,
            "-c", str(project_root),
            "-n", "main",
        ],
        check=True,
    )

    # Split conductor window: left/right (60/40)
    subprocess.run(
        ["tmux", "split-window", "-t", f"{conductor_session}:main", "-h", "-l", "40%", "-c", str(project_root)],
        check=True,
    )

    # Set pane titles
    subprocess.run(["tmux", "select-pane", "-t", f"{conductor_session}:main.0", "-T", "conductor"], check=True)
    subprocess.run(["tmux", "select-pane", "-t", f"{conductor_session}:main.1", "-T", "dashboard"], check=True)

    # Start Claude in Conductor pane (left)
    conductor_agent = agents.get("conductor")
    if conductor_agent:
        cmd = f"MAX_THINKING_TOKENS=0 claude --agent {conductor_agent} --model opus --dangerously-skip-permissions"
    else:
        cmd = "MAX_THINKING_TOKENS=0 claude --model opus --dangerously-skip-permissions"
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{conductor_session}:main.0", cmd],
        check=True,
    )
    time.sleep(1)
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{conductor_session}:main.0", "Enter"],
        check=True,
    )

    # Start dashboard watch in Dashboard pane (right)
    dashboard_path = project_root / ".ensemble" / "status" / "dashboard.md"
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{conductor_session}:main.1", f"watch -n 5 cat {dashboard_path}"],
        check=True,
    )
    time.sleep(1)
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{conductor_session}:main.1", "Enter"],
        check=True,
    )

    # フレンドリーファイア防止: Conductorが起動完了するまで待機
    time.sleep(3)

    # === Session 2: Workers ===
    subprocess.run(
        [
            "tmux", "new-session",
            "-d",
            "-s", workers_session,
            "-c", str(project_root),
            "-n", "main",
        ],
        check=True,
    )

    # Split workers window: left/right (60/40)
    subprocess.run(
        ["tmux", "split-window", "-t", f"{workers_session}:main", "-h", "-l", "40%", "-c", str(project_root)],
        check=True,
    )

    # Set pane titles
    subprocess.run(["tmux", "select-pane", "-t", f"{workers_session}:main.0", "-T", "dispatch"], check=True)
    subprocess.run(["tmux", "select-pane", "-t", f"{workers_session}:main.1", "-T", "worker-area"], check=True)

    # Start Claude in Dispatch pane (left)
    dispatch_agent = agents.get("dispatch")
    if dispatch_agent:
        cmd = f"claude --agent {dispatch_agent} --model sonnet --dangerously-skip-permissions"
    else:
        cmd = "claude --model sonnet --dangerously-skip-permissions"
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{workers_session}:main.0", cmd],
        check=True,
    )
    time.sleep(1)
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{workers_session}:main.0", "Enter"],
        check=True,
    )

    # Show placeholder message in worker area (right)
    subprocess.run(
        ["tmux", "send-keys", "-t", f"{workers_session}:main.1", "echo '=== Worker Area ===' && echo 'Workers will be started here.'", "Enter"],
        check=True,
    )

    # Select dispatch pane in workers session
    subprocess.run(["tmux", "select-pane", "-t", f"{workers_session}:main.0"], check=True)


def _save_pane_ids(session: str, ensemble_dir: Path) -> None:
    """Save pane IDs to panes.env file."""
    conductor_session = f"{session}-conductor"
    workers_session = f"{session}-workers"

    # Get conductor session pane IDs
    result = subprocess.run(
        ["tmux", "list-panes", "-t", f"{conductor_session}:main", "-F", "#{pane_index}:#{pane_id}"],
        capture_output=True,
        text=True,
        check=True,
    )

    conductor_pane_map = {}
    for line in result.stdout.strip().split("\n"):
        if ":" in line:
            idx, pane_id = line.split(":", 1)
            conductor_pane_map[int(idx)] = pane_id

    # Get workers session pane IDs
    result = subprocess.run(
        ["tmux", "list-panes", "-t", f"{workers_session}:main", "-F", "#{pane_index}:#{pane_id}"],
        capture_output=True,
        text=True,
        check=True,
    )

    workers_pane_map = {}
    for line in result.stdout.strip().split("\n"):
        if ":" in line:
            idx, pane_id = line.split(":", 1)
            workers_pane_map[int(idx)] = pane_id

    # Write panes.env
    panes_env = ensemble_dir / "panes.env"
    with open(panes_env, "w") as f:
        f.write("# Ensemble pane IDs (auto-generated)\n")
        f.write("# Session names\n")
        f.write(f"CONDUCTOR_SESSION={conductor_session}\n")
        f.write(f"WORKERS_SESSION={workers_session}\n")
        f.write("\n")
        f.write("# Pane IDs (use these with tmux send-keys -t)\n")
        f.write(f"CONDUCTOR_PANE={conductor_pane_map.get(0, '%0')}\n")
        f.write(f"DASHBOARD_PANE={conductor_pane_map.get(1, '%1')}\n")
        f.write(f"DISPATCH_PANE={workers_pane_map.get(0, '%0')}\n")
        f.write(f"WORKER_AREA_PANE={workers_pane_map.get(1, '%1')}\n")
        f.write("\n")
        f.write("# Usage examples:\n")
        f.write("# source .ensemble/panes.env\n")
        f.write("# tmux send-keys -t \"$CONDUCTOR_PANE\" 'message' Enter\n")
        f.write("# tmux send-keys -t \"$DISPATCH_PANE\" 'message' Enter\n")

    click.echo(f"  Saved pane IDs to {panes_env.relative_to(ensemble_dir.parent)}")
