# Ensemble

> **"One task. Many minds. One result."**

AI Orchestration Tool for Claude Code.

## Overview

Ensemble is an AI orchestration system that combines the best practices from:
- **shogun** - Autonomous AI collaboration with tmux parallel execution
- **takt** - Workflow enforcement with quality gates
- **Boris's practices** - Effective use of skills, subagents, CLAUDE.md, and hooks

## Features

- **Autonomous AI Coordination**: One instruction triggers multiple AI agents working together
- **Flexible Execution Patterns**:
  - Pattern A: Simple tasks via subagent
  - Pattern B: Medium tasks via tmux parallel panes (2-4 workers, auto-scaled)
  - Pattern C: Large tasks via git worktree separation
  - Mode T: Research/review tasks via Agent Teams (parallel investigation)
- **Parallel Execution Enhancements**:
  - Dynamic worker count (auto-scales based on task count)
  - Worker-level subagent parallelization (for 3+ files)
- **Parallel Review**: Architecture + Security reviews run in parallel
- **Self-Improvement**: Automatic learning and CLAUDE.md updates
  - Categorized learning (communication, workflow, code quality, tools)
  - Duplicate detection and consolidation
  - Subagent execution result collection
- **Compaction Recovery**: Built-in protocol to prevent role amnesia
- **Extensibility**:
  - `/create-skill` - Generate project-specific skill templates
  - `/create-agent` - Auto-generate specialized agents from tech stack
- **RPI Workflow**: Research → Plan → Implement staged workflow for large features
- **Hooks Notification**: Terminal bell on agent completion (Stop) and errors (PostToolUseFailure)
- **Status Line**: Real-time display of git branch, session state, worker count
- **CLAUDE.md 150-line Limit Check**: Pre-commit hook to prevent instruction bloat
- **Event-Driven Communication**: inbox_watcher.sh + inotifywait for 0ms detection
- **Exclusive Locking**: flock + atomic write for concurrent YAML protection
- **3-Phase Auto-Escalation**: Automatic worker recovery (nudge → Escape+C-c → /clear)
- **Loop Detection**: LoopDetector + CycleDetector for infinite loop prevention
- **Task Dependencies**: blocked_by field with DependencyResolver and cycle detection
- **NDJSON Session Logging**: Structured logging for full session traceability
- **Faceted Prompting**: 5-concern separation (WHO/RULES/WHAT/CONTEXT/OUTPUT)
- **Progressive Disclosure Skills**: Dynamic skill injection based on task type
- **CI/CD Pipeline Mode**: Non-interactive execution with `ensemble pipeline`
- **Autonomous Loop Mode**: `ensemble loop --scan` for automatic task discovery and fix
- **Codebase Scanner**: `ensemble scan` finds TODO/FIXME, GitHub Issues, PROGRESS.md tasks
- **Task Investigation**: `ensemble investigate` analyzes scan results (inline, subprocess, or Agent Teams)
- **Autonomous Task Continuation**: `/go` automatically scans for next tasks after completion
- **Bloom's Taxonomy Classification**: Cognitive-level-based model selection (L1-L3: sonnet, L4-L6: opus)
- **Bottom-Up Skill Discovery**: Auto-detect repeated patterns and suggest skill creation

## Installation

### Using uv (recommended)

```bash
# Install globally
uv tool install ensemble-claude

# Or add to your project
uv add ensemble-claude
```

### Using pip

```bash
pip install ensemble-claude
```

### From source

```bash
git clone https://github.com/ChikaKakazu/ensemble.git
cd ensemble

# Using uv
uv pip install -e .

# Or using pip
pip install -e .
```

## Quick Start

```bash
# 1. Initialize Ensemble in your project
ensemble init

# 2. Launch the tmux sessions (2 separate sessions)
ensemble launch

# 3. Open another terminal to view workers session
tmux attach -t ensemble-workers

# 4. Run a task in the Conductor session
/go implement user authentication

# Light workflow (minimal cost)
/go-light fix typo in README

# Create project-specific tools
/create-skill my-feature "Description of the skill"
/create-agent  # Interactive tech stack analysis
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `ensemble init` | Initialize Ensemble in current project |
| `ensemble init --full` | Copy all templates (agents, commands, scripts, workflows, hooks, rules, settings, etc.) |
| `ensemble launch` | Start 2 tmux sessions (conductor + workers) |
| `ensemble launch --no-attach` | Start sessions without attaching |
| `ensemble upgrade` | Sync template updates (agents, commands, scripts) |
| `ensemble scan` | Scan codebase for task candidates (TODO/FIXME, Issues, PROGRESS.md) |
| `ensemble scan --exclude-tests` | Scan excluding test files |
| `ensemble investigate` | Investigate scan results with Claude |
| `ensemble loop --scan` | Autonomous loop: scan → fix → repeat |
| `ensemble pipeline --task "..." ` | Non-interactive CI/CD pipeline mode |
| `ensemble --version` | Show version |

### In-Session Commands (Conductor)

| Command | Description |
|---------|-------------|
| `/go <task>` | Full workflow with auto-pattern detection + auto-continuation |
| `/go --confirm <task>` | Same as /go but asks before starting next task |
| `/go --teams <task>` | Force Mode T: Research/review via Agent Teams |
| `/go-light <task>` | Lightweight workflow for simple changes |
| `/go-issue [number]` | Start implementation from GitHub Issue |
| `/rpi-research <task>` | Research phase: requirement analysis, technical investigation, feasibility assessment |
| `/rpi-plan` | Plan phase: detailed planning, architecture design, task breakdown |
| `/rpi-implement` | Implement phase: execute implementation based on plan (delegates to /go) |
| `/create-skill <name> <desc>` | Generate project-specific skill template |
| `/create-agent` | Auto-generate specialized agent from tech stack |
| `/review` | Run architecture + security review |
| `/improve` | Manual self-improvement analysis |
| `/status` | View current progress |
| `/deploy` | Version bump, merge, and publish to PyPI |

### What `ensemble init --full` Copies

| Category | Files | Description |
|----------|-------|-------------|
| agents/ | 7 | Agent definitions (conductor, dispatch, worker, reviewer, etc.) |
| commands/ | 11 | Slash commands (/go, /go-issue, /review, /improve, /rpi-*, etc.) |
| scripts/ | 9 | Shell scripts (launch, pane-setup, dashboard-update, etc.) |
| workflows/ | 4 | Workflow definitions (simple, default, heavy, worktree) |
| instructions/ | 6 | Phase instructions (plan, implement, review, dispatch, etc.) |
| policies/ | 5 | Policies (communication, delegation, review, coding, security) |
| personas/ | 7 | Agent persona definitions |
| output-contracts/ | 3 | Output format contracts (worker-report, review-report, etc.) |
| knowledge/ | 1 | Project knowledge templates |
| skills/ | 6 | Skill templates (testing, security-audit, worktree-manager, etc.) |
| hooks/scripts/ | 4 | Claude Code hooks (session-scan, notify-stop, notify-error, etc.) |
| rules/ | 4 | Rules (workflow, communication, infrastructure, agent-teams) |
| settings.json | 1 | Claude Code project settings with hooks configuration |
| **Total** | **68** | |

## Requirements

- Python 3.11+
- **Claude Code CLI** (`claude` command available) - [Install](https://claude.ai/code)
- **tmux** - `apt install tmux` (Ubuntu) / `brew install tmux` (macOS)
- **git** 2.20+ (for worktree support)
- Claude Max plan recommended (for parallel execution)
- **Optional**: `gh` CLI for GitHub Issue integration
- **Optional**: `inotifywait` for event-driven notifications (`apt install inotify-tools`)

> **Note**: Ensemble requires Linux or macOS. On Windows, use WSL.

## Agent Architecture

```
┌─────────────┐
│  Conductor  │ ← Orchestrator (planning, judgment, delegation)
└──────┬──────┘
       │
  ┌────┴────┐
  ▼         ▼
┌────────┐ ┌──────────┐
│Dispatch│ │ Learner  │
└───┬────┘ └──────────┘
    │        ↑ Learning records
    ▼
┌─────────────────────────────┐
│  Reviewer / Security-Reviewer│ ← Parallel reviews
└─────────────────────────────┘
    │
    ▼ (worktree mode)
┌──────────┐
│Integrator│ ← Merge & integrate
└──────────┘
```

## License

MIT License - see [LICENSE](LICENSE) for details.
