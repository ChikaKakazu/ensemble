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
  - Pattern B: Medium tasks via tmux parallel panes
  - Pattern C: Large tasks via git worktree separation
- **Parallel Review**: Architecture + Security reviews run in parallel
- **Self-Improvement**: Automatic learning and CLAUDE.md updates
- **Compaction Recovery**: Built-in protocol to prevent role amnesia

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
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `ensemble init` | Initialize Ensemble in current project |
| `ensemble init --full` | Also copy agent/command definitions locally |
| `ensemble launch` | Start 2 tmux sessions (conductor + workers) |
| `ensemble launch --no-attach` | Start sessions without attaching |
| `ensemble --version` | Show version |

## Requirements

- Python 3.10+
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
