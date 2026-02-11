#!/bin/bash
# scripts/update-mode.sh
# Ensembleの実行モード（A/B/C/T/IDLE）を視覚化するASCIIアートを生成
#
# Usage: .claude/scripts/update-mode.sh <mode> <status> [options]
# mode: idle|A|B|C|T
# status: active|completed|error
# options: --workers N --workflow NAME --tasks-total N --tasks-done N --worktrees N --teammates N

set -euo pipefail

MODE="${1:-idle}"
STATUS="${2:-active}"
shift 2

# オプション引数の解析
WORKERS=0
WORKFLOW=""
TASKS_TOTAL=0
TASKS_DONE=0
WORKTREES=0
TEAMMATES=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        --tasks-total)
            TASKS_TOTAL="$2"
            shift 2
            ;;
        --tasks-done)
            TASKS_DONE="$2"
            shift 2
            ;;
        --worktrees)
            WORKTREES="$2"
            shift 2
            ;;
        --teammates)
            TEAMMATES="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            shift
            ;;
    esac
done

# 出力先
OUTPUT_FILE=".ensemble/status/mode.md"

# ステータス記号
case $STATUS in
    active)
        STATUS_SYMBOL="● ACTIVE"
        WORKER_STATUS="● busy"
        ;;
    completed)
        STATUS_SYMBOL="✓ DONE"
        WORKER_STATUS="✓ done"
        ;;
    error)
        STATUS_SYMBOL="✗ ERROR"
        WORKER_STATUS="✗ fail"
        ;;
    *)
        STATUS_SYMBOL="○ Waiting"
        WORKER_STATUS="○ idle"
        ;;
esac

# モード別ASCIIアート生成関数
generate_idle() {
    cat << 'EOF'
╔══════════════════════════════════════╗
║  💤 EXECUTION MODE                   ║
╠══════════════════════════════════════╣
║                                      ║
║  Mode: IDLE                          ║
║  Status: ○ Waiting                   ║
║                                      ║
║  ┌──────────┐                        ║
║  │Conductor │  No active tasks       ║
║  │  (opus)  │                        ║
║  └──────────┘                        ║
║                                      ║
╚══════════════════════════════════════╝
EOF
}

generate_mode_a() {
    cat << EOF
╔══════════════════════════════════════╗
║  ⚡ EXECUTION MODE                   ║
╠══════════════════════════════════════╣
║                                      ║
║  Mode: A - Direct (subagent)         ║
║  Status: $STATUS_SYMBOL                    ║
║  Workflow: ${WORKFLOW:-simple}                    ║
║                                      ║
║  ┌──────────┐    ┌────────┐          ║
║  │Conductor │ →  │Dispatch│          ║
║  │  (opus)  │    │(sonnet)│          ║
║  └──────────┘    └───┬────┘          ║
║                      │               ║
║                      ▼               ║
║                 ┌────────┐           ║
║                 │Worker-1│           ║
║                 │$WORKER_STATUS│           ║
║                 └────────┘           ║
║                                      ║
║  Tasks: $TASKS_DONE/$TASKS_TOTAL in progress              ║
╚══════════════════════════════════════╝
EOF
}

generate_mode_b() {
    local worker_boxes=""
    if [ "$WORKERS" -le 2 ]; then
        # 2ワーカーまで: 横並び
        worker_boxes=$(cat << EOF
║                  ┌───┴───┐           ║
║                  ▼       ▼           ║
║            ┌────────┐┌────────┐      ║
║            │Worker-1││Worker-2│      ║
║            │$WORKER_STATUS││$WORKER_STATUS│      ║
║            └────────┘└────────┘      ║
EOF
)
    else
        # 3-4ワーカー: 縦並び
        worker_boxes=$(cat << EOF
║                  ┌───┴───┐           ║
║                  ▼       ▼           ║
║            ┌────────┐┌────────┐      ║
║            │Worker-1││Worker-2│      ║
║            │$WORKER_STATUS││$WORKER_STATUS│      ║
║            └────────┘└────────┘      ║
EOF
)
        if [ "$WORKERS" -eq 3 ]; then
            # workers=3: Worker-3のみ表示
            worker_boxes+=$(cat << EOF

║            ┌────────┐              ║
║            │Worker-3│              ║
║            │$WORKER_STATUS│              ║
║            └────────┘              ║
EOF
)
        fi
        if [ "$WORKERS" -ge 4 ]; then
            # workers=4以上: Worker-3とWorker-4を表示
            worker_boxes+=$(cat << EOF

║            ┌────────┐┌────────┐      ║
║            │Worker-3││Worker-4│      ║
║            │$WORKER_STATUS││$WORKER_STATUS│      ║
║            └────────┘└────────┘      ║
EOF
)
        fi
    fi

    cat << EOF
╔══════════════════════════════════════╗
║  ⚡ EXECUTION MODE                   ║
╠══════════════════════════════════════╣
║                                      ║
║  Mode: B - Parallel (tmux)           ║
║  Status: $STATUS_SYMBOL                    ║
║  Workflow: ${WORKFLOW:-default}                   ║
║                                      ║
║  ┌──────────┐    ┌────────┐          ║
║  │Conductor │ →  │Dispatch│          ║
║  │  (opus)  │    │(sonnet)│          ║
║  └──────────┘    └───┬────┘          ║
$worker_boxes
║                                      ║
║  Tasks: $TASKS_DONE/$TASKS_TOTAL completed                ║
╚══════════════════════════════════════╝
EOF
}

generate_mode_c() {
    local worktree_count="${WORKTREES:-3}"
    local worktree_boxes=""

    if [ "$worktree_count" -eq 2 ]; then
        worktree_boxes=$(cat << EOF
║          ┌───────────┴───────────┐   ║
║          ▼                       ▼   ║
║    ┌──────────┐          ┌──────────┐║
║    │ worktree │          │ worktree │║
║    │  feat-1  │          │  feat-2  │║
║    │$WORKER_STATUS Worker │          │$WORKER_STATUS Worker │║
║    └──────────┘          └──────────┘║
EOF
)
    elif [ "$worktree_count" -eq 3 ]; then
        worktree_boxes=$(cat << EOF
║          ┌───────────┼───────────┐   ║
║          ▼           ▼           ▼   ║
║    ┌──────────┐┌──────────┐┌──────────┐
║    │ worktree ││ worktree ││ worktree │║
║    │  feat-1  ││  feat-2  ││  feat-3  │║
║    │$WORKER_STATUS Worker ││$WORKER_STATUS Worker ││$WORKER_STATUS Worker │║
║    └──────────┘└──────────┘└──────────┘║
EOF
)
    else
        # 4+の場合は省略表示
        worktree_boxes=$(cat << EOF
║          ┌───────────┼───────────┐   ║
║          ▼           ▼           ▼   ║
║    ┌──────────┐┌──────────┐┌──────────┐
║    │ worktree ││ worktree ││   ...    │║
║    │  feat-1  ││  feat-2  ││  ($worktree_count total)││
║    │$WORKER_STATUS Worker ││$WORKER_STATUS Worker ││          │║
║    └──────────┘└──────────┘└──────────┘║
EOF
)
    fi

    cat << EOF
╔══════════════════════════════════════╗
║  ⚡ EXECUTION MODE                   ║
╠══════════════════════════════════════╣
║                                      ║
║  Mode: C - Isolated (worktree)       ║
║  Status: $STATUS_SYMBOL                    ║
║  Workflow: ${WORKFLOW:-heavy}                     ║
║                                      ║
║  ┌──────────┐    ┌────────┐          ║
║  │Conductor │ →  │Dispatch│          ║
║  │  (opus)  │    │(sonnet)│          ║
║  └──────────┘    └───┬────┘          ║
║                      │               ║
$worktree_boxes
║                                      ║
║  Tasks: $TASKS_DONE/$TASKS_TOTAL completed                ║
╚══════════════════════════════════════╝
EOF
}

generate_mode_t() {
    local teammate_count="${TEAMMATES:-3}"
    local teammate_boxes=""

    if [ "$teammate_count" -eq 2 ]; then
        teammate_boxes=$(cat << EOF
║         ┌─────┴─────┐               ║
║         ▼           ▼               ║
║    ┌────────┐  ┌────────┐           ║
║    │Mate #1 │  │Mate #2 │           ║
║    │security│  │  perf  │           ║
║    │$WORKER_STATUS│  │$WORKER_STATUS│           ║
║    └────────┘  └────────┘           ║
║        ↕           ↕                ║
║    [ mailbox: discussion active ]    ║
EOF
)
    elif [ "$teammate_count" -eq 3 ]; then
        teammate_boxes=$(cat << EOF
║         ┌─────┼─────┐               ║
║         ▼     ▼     ▼               ║
║    ┌────────┐┌────────┐┌────────┐   ║
║    │Mate #1 ││Mate #2 ││Mate #3 │   ║
║    │security││  perf  ││  test  │   ║
║    │$WORKER_STATUS││$WORKER_STATUS││$WORKER_STATUS│   ║
║    └────────┘└────────┘└────────┘   ║
║        ↕         ↕         ↕        ║
║    [ mailbox: discussion active ]    ║
EOF
)
    else
        # 4+の場合
        teammate_boxes=$(cat << EOF
║         ┌─────┼─────┼─────┐         ║
║         ▼     ▼     ▼     ▼         ║
║    ┌────────┐┌────────┐┌────────┐   ║
║    │Mate #1 ││Mate #2 ││  ...   │   ║
║    │security││  perf  ││($teammate_count total) │   ║
║    │$WORKER_STATUS││$WORKER_STATUS││$WORKER_STATUS│   ║
║    └────────┘└────────┘└────────┘   ║
║        ↕         ↕         ↕        ║
║    [ mailbox: discussion active ]    ║
EOF
)
    fi

    cat << EOF
╔══════════════════════════════════════╗
║  🔬 EXECUTION MODE                   ║
╠══════════════════════════════════════╣
║                                      ║
║  Mode: T - Research (Agent Teams)    ║
║  Status: $STATUS_SYMBOL                    ║
║                                      ║
║        ┌──────────────┐              ║
║        │  Conductor   │              ║
║        │ (Team Lead)  │              ║
║        └──────┬───────┘              ║
$teammate_boxes
║                                      ║
║  Teammates: $teammate_count active                 ║
╚══════════════════════════════════════╝
EOF
}

# モード別に生成
case $MODE in
    idle)
        generate_idle > "$OUTPUT_FILE"
        ;;
    A)
        generate_mode_a > "$OUTPUT_FILE"
        ;;
    B)
        generate_mode_b > "$OUTPUT_FILE"
        ;;
    C)
        generate_mode_c > "$OUTPUT_FILE"
        ;;
    T)
        generate_mode_t > "$OUTPUT_FILE"
        ;;
    *)
        echo "Error: Unknown mode: $MODE"
        echo "Valid modes: idle, A, B, C, T"
        exit 1
        ;;
esac

echo "Mode display updated: $OUTPUT_FILE (mode=$MODE, status=$STATUS)"
