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
| `ensemble init --full` | Also copy agent/command definitions locally |
| `ensemble launch` | Start 2 tmux sessions (conductor + workers) |
| `ensemble launch --no-attach` | Start sessions without attaching |
| `ensemble upgrade` | Sync template updates (agents, commands, scripts) |
| `ensemble --version` | Show version |

### In-Session Commands (Conductor)

| Command | Description |
|---------|-------------|
| `/go <task>` | Full workflow with auto-pattern detection |
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

## Requirements

- Python 3.11+
- Claude Code CLI (`claude` command available)
- tmux
- git 2.20+ (for worktree support)
- Claude Max plan recommended (for parallel execution)

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
