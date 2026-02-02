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

## Quick Start

```bash
# Setup
./scripts/setup.sh

# Launch Claude Code with Conductor settings
MAX_THINKING_TOKENS=0 claude --model opus

# Run a task
/go implement user authentication

# Light workflow (minimal cost)
/go-light fix typo in README
```

## Requirements

- Claude Code (claude command available)
- tmux
- git 2.20+ (for worktree support)
- Claude Max plan recommended (for parallel execution)

## License

TBD
