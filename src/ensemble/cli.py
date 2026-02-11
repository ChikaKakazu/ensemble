"""Ensemble CLI - AI Orchestration Tool for Claude Code."""

import sys
from pathlib import Path

import click

from ensemble import __version__
from ensemble.autonomous_loop import AutonomousLoopRunner, LoopConfig, LoopStatus
from ensemble.commands.init import init
from ensemble.scanner import CodebaseScanner
from ensemble.commands.issue import issue
from ensemble.commands.launch import launch
from ensemble.commands.upgrade import upgrade
from ensemble.pipeline import PipelineRunner


@click.group()
@click.version_option(version=__version__, prog_name="ensemble")
def cli() -> None:
    """Ensemble - AI Orchestration Tool for Claude Code.

    Ensemble provides multi-agent orchestration for complex development tasks,
    enabling parallel execution, automatic code review, and self-improvement.
    """
    pass


cli.add_command(init)
cli.add_command(issue)
cli.add_command(launch)
cli.add_command(upgrade)


@cli.command()
@click.option(
    "--task",
    "-t",
    required=True,
    help="Task description",
)
@click.option(
    "--workflow",
    "-w",
    default="default",
    type=click.Choice(["simple", "default", "heavy"]),
    help="Workflow type (default: default)",
)
@click.option(
    "--auto-pr",
    is_flag=True,
    help="Automatically create PR after execution",
)
@click.option(
    "--branch",
    "-b",
    default=None,
    help="Branch name (auto-generated if not specified)",
)
def pipeline(task: str, workflow: str, auto_pr: bool, branch: str | None) -> None:
    """Run pipeline mode for CI/CD environments.

    Execute tasks in non-interactive mode without tmux.
    Outputs NDJSON logs to stdout and returns exit code.

    Exit codes:
      0 - Success
      1 - Execution error
      2 - Review needs_fix
      3 - Loop detected

    Example:
      ensemble pipeline --task "Fix authentication bug" --auto-pr
    """
    runner = PipelineRunner(task=task, workflow=workflow, auto_pr=auto_pr, branch=branch)
    exit_code = runner.run()
    sys.exit(exit_code)


@cli.command()
@click.option(
    "--max-iterations",
    "-n",
    default=50,
    type=int,
    help="Maximum number of iterations (default: 50)",
)
@click.option(
    "--prompt",
    "-p",
    default="AGENT_PROMPT.md",
    help="Agent prompt file (default: AGENT_PROMPT.md)",
)
@click.option(
    "--model",
    "-m",
    default="sonnet",
    help="Model to use (default: sonnet)",
)
@click.option(
    "--timeout",
    default=600,
    type=int,
    help="Timeout per iteration in seconds (default: 600)",
)
@click.option(
    "--no-commit",
    is_flag=True,
    help="Don't commit after each iteration",
)
@click.option(
    "--queue",
    is_flag=True,
    help="Use TaskQueue for task selection instead of prompt file",
)
@click.option(
    "--work-dir",
    default=".",
    type=click.Path(exists=True),
    help="Working directory (default: current directory)",
)
def loop(
    max_iterations: int,
    prompt: str,
    model: str,
    timeout: int,
    no_commit: bool,
    queue: bool,
    work_dir: str,
) -> None:
    """Run autonomous loop mode.

    Inspired by Anthropic's "Building a C compiler with parallel Claudes".
    Runs Claude in a loop, automatically picking up and completing tasks.

    Each iteration: read prompt → execute claude → commit → repeat.

    Safety features:
      - Max iteration limit (--max-iterations)
      - Per-iteration timeout (--timeout)
      - Git commit per iteration (--no-commit to disable)
      - Full logging to .ensemble/logs/loop/

    Examples:

      # Run with default prompt file
      ensemble loop --prompt AGENT_PROMPT.md --max-iterations 10

      # Run with task queue
      ensemble loop --queue --max-iterations 20

      # Run with opus model, no commits
      ensemble loop --model opus --no-commit
    """
    config = LoopConfig(
        max_iterations=max_iterations,
        task_timeout=timeout,
        prompt_file=prompt,
        model=model,
        commit_each=not no_commit,
    )

    runner = AutonomousLoopRunner(
        work_dir=Path(work_dir).resolve(),
        config=config,
        use_queue=queue,
    )

    click.echo(f"Starting autonomous loop (max {max_iterations} iterations, model: {model})")
    if queue:
        click.echo("Mode: TaskQueue")
    else:
        click.echo(f"Mode: Prompt file ({prompt})")
    click.echo("")

    result = runner.run()

    # 結果表示
    click.echo("")
    click.echo("=" * 50)
    click.echo(f"Autonomous Loop Complete")
    click.echo(f"  Iterations: {result.iterations_completed}")
    click.echo(f"  Status: {result.status.value}")
    click.echo(f"  Commits: {len(result.commits)}")
    click.echo(f"  Errors: {len(result.errors)}")
    click.echo("=" * 50)

    if result.errors:
        click.echo("")
        click.echo("Errors:")
        for err in result.errors[:10]:  # 最大10件表示
            click.echo(f"  - {err}")

    # 終了コード
    if result.status == LoopStatus.ERROR:
        sys.exit(1)
    elif result.status == LoopStatus.LOOP_DETECTED:
        sys.exit(3)
    else:
        sys.exit(0)


@cli.command()
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format (default: text)",
)
@click.option(
    "--include",
    multiple=True,
    type=click.Choice(["todo", "issue", "progress", "all"]),
    default=["all"],
    help="Sources to include (default: all)",
)
def scan(output_format: str, include: tuple[str, ...]) -> None:
    """Scan codebase and generate task candidates.

    Analyzes the project for TODO/FIXME comments, open GitHub issues,
    and unchecked items in PROGRESS.md/PLAN.md.

    Examples:

      # Full scan
      ensemble scan

      # Only TODOs
      ensemble scan --include todo

      # JSON output
      ensemble scan --format json
    """
    import json as json_mod

    scanner = CodebaseScanner(root_dir=Path.cwd())

    include_set = set(include)
    scan_all = "all" in include_set

    tasks = []
    errors = []

    if scan_all or "todo" in include_set:
        try:
            tasks.extend(scanner.scan_todos())
        except Exception as e:
            errors.append(f"todo: {e}")

    if scan_all or "issue" in include_set:
        try:
            tasks.extend(scanner.scan_github_issues())
        except Exception as e:
            errors.append(f"issue: {e}")

    if scan_all or "progress" in include_set:
        try:
            tasks.extend(scanner.scan_progress_files())
        except Exception as e:
            errors.append(f"progress: {e}")

    from ensemble.scanner import ScanResult

    result = ScanResult(tasks=tasks, scan_errors=errors)

    if output_format == "json":
        data = {
            "total": result.total,
            "tasks": [
                {
                    "source": t.source,
                    "title": t.title,
                    "priority": t.priority.value,
                    "file_path": t.file_path,
                    "line_number": t.line_number,
                    "description": t.description,
                }
                for t in result.sorted_by_priority()
            ],
            "errors": result.scan_errors,
        }
        click.echo(json_mod.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(result.format_text())

    if result.total == 0:
        click.echo("No task candidates found.")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
