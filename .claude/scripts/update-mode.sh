#!/bin/bash
# scripts/update-mode.sh
# Ensembleの実行モード（A/B/C/T/IDLE）を視覚化するASCIIアートを生成
#
# Usage: ./scripts/update-mode.sh <mode> <status> [options]
# mode: idle|A|B|C|T
# status: active|completed|error|waiting
# options:
#   --workers N           ワーカー数
#   --workflow NAME       ワークフロー名
#   --tasks-total N       タスク総数
#   --tasks-done N        完了タスク数
#   --worktrees N         worktree数
#   --teammates N         teammate数
#   --worker-states STR   ワーカー状態（カンマ区切り: "busy,idle,done"）
#   --frame N             アニメーションフレーム（0 or 1）

set -euo pipefail

MODE="${1:-idle}"
STATUS="${2:-active}"
shift 2

# オプション引数
WORKERS=1
WORKFLOW=""
TASKS_TOTAL=0
TASKS_DONE=0
WORKTREES=3
TEAMMATES=3
WORKER_STATES=""
FRAME=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --workers)       WORKERS="$2";       shift 2 ;;
        --workflow)      WORKFLOW="$2";      shift 2 ;;
        --tasks-total)   TASKS_TOTAL="$2";   shift 2 ;;
        --tasks-done)    TASKS_DONE="$2";    shift 2 ;;
        --worktrees)     WORKTREES="$2";     shift 2 ;;
        --teammates)     TEAMMATES="$2";     shift 2 ;;
        --worker-states) WORKER_STATES="$2"; shift 2 ;;
        --frame)         FRAME="$2";         shift 2 ;;
        *) echo "Unknown option: $1"; shift ;;
    esac
done

OUTPUT_FILE=".ensemble/status/mode.md"
PARAMS_FILE=".ensemble/status/mode-params.env"
mkdir -p "$(dirname "$OUTPUT_FILE")"

# ステータス記号とグローバルワーカー状態
case $STATUS in
    active)    STATUS_SYMBOL="● ACTIVE";  WORKER_STATUS="busy" ;;
    completed) STATUS_SYMBOL="✓ DONE";    WORKER_STATUS="done" ;;
    error)     STATUS_SYMBOL="✗ ERROR";   WORKER_STATUS="fail" ;;
    *)         STATUS_SYMBOL="○ Waiting"; WORKER_STATUS="idle" ;;
esac

# アニメーションフレーム用矢印
if [ "${FRAME}" = "1" ]; then
    ARROW_S="══>"
    ARROW_L="════════>"
    ARROW_FORK="═══┬═══>"
    ARROW_F="═══>"
else
    ARROW_S="──→"
    ARROW_L="────────→"
    ARROW_FORK="───┬───→"
    ARROW_F="───>"
fi

# ワーカー状態記号取得（1-indexed）
get_worker_state() {
    local idx=$1
    local state=""
    if [ -n "$WORKER_STATES" ]; then
        state=$(echo "$WORKER_STATES" | tr ',' '\n' | sed -n "${idx}p")
        [ -z "$state" ] && state=$(echo "$WORKER_STATES" | tr ',' '\n' | head -1)
    fi
    [ -z "$state" ] && state="$WORKER_STATUS"
    case "$state" in
        busy) echo "● busy" ;;
        idle) echo "○ idle" ;;
        done) echo "✓ done" ;;
        fail) echo "✗ fail" ;;
        *)    echo "○ idle" ;;
    esac
}

# Tasks行生成
get_tasks_line() {
    if [ "$TASKS_TOTAL" -eq 0 ]; then
        case "$STATUS" in
            active)    echo "Tasks: running" ;;
            completed) echo "Tasks: all done" ;;
            *)         echo "Tasks: pending" ;;
        esac
    elif [ "$TASKS_DONE" -ge "$TASKS_TOTAL" ]; then
        echo "Tasks: $TASKS_DONE/$TASKS_TOTAL completed"
    else
        echo "Tasks: $TASKS_DONE/$TASKS_TOTAL in progress"
    fi
}

# ボックスライン生成（65幅: ║ + 63chars + ║）
# wc -m でマルチバイト文字を正しくカウント
INNER_W=63
box_line() {
    local content="${1:-}"
    local char_count
    char_count=$(printf '%s' "$content" | wc -m)
    local padding=$((INNER_W - char_count))
    [ $padding -lt 0 ] && padding=0
    printf '║%s%*s║\n' "$content" "$padding" ""
}

BORDER_TOP="╔═══════════════════════════════════════════════════════════════╗"
BORDER_SEP="╠═══════════════════════════════════════════════════════════════╣"
BORDER_BOT="╚═══════════════════════════════════════════════════════════════╝"

# IDLE モード
generate_idle() {
    printf '%s\n' "$BORDER_TOP"
    box_line "  💤 EXECUTION MODE"
    printf '%s\n' "$BORDER_SEP"
    box_line ""
    box_line "  Mode: IDLE"
    box_line "  Status: ○ Waiting"
    box_line ""
    box_line "              ┌──────────┐"
    box_line "              │Conductor │  No active tasks"
    box_line "              │  (opus)  │"
    box_line "              └──────────┘"
    box_line ""
    printf '%s\n' "$BORDER_BOT"
}

# モードA: Conductor → Dispatch → Worker-1 横一列
generate_mode_a() {
    local w1
    w1=$(get_worker_state 1)
    local tasks_line
    tasks_line=$(get_tasks_line)
    local wf="${WORKFLOW:-simple}"

    printf '%s\n' "$BORDER_TOP"
    box_line "  ⚡ EXECUTION MODE"
    printf '%s\n' "$BORDER_SEP"
    box_line ""
    box_line "  Mode: A - Direct (subagent)"
    box_line "  Status: $STATUS_SYMBOL"
    box_line "  Workflow: $wf"
    box_line ""
    box_line "  ┌──────────┐     ┌────────┐           ┌──────────┐"
    box_line "  │Conductor │ $ARROW_S │Dispatch│ $ARROW_L │ Worker-1 │"
    box_line "  │  (opus)  │     │(sonnet)│           │ $w1   │"
    box_line "  └──────────┘     └────────┘           └──────────┘"
    box_line ""
    box_line "  $tasks_line"
    printf '%s\n' "$BORDER_BOT"
}

# モードB: Conductor → Dispatch → Worker-1..N (横展開)
generate_mode_b() {
    local num_workers="${WORKERS:-2}"
    local tasks_line
    tasks_line=$(get_tasks_line)
    local wf="${WORKFLOW:-default}"
    local w1
    w1=$(get_worker_state 1)

    printf '%s\n' "$BORDER_TOP"
    box_line "  ⚡ EXECUTION MODE"
    printf '%s\n' "$BORDER_SEP"
    box_line ""
    box_line "  Mode: B - Parallel (tmux)"
    box_line "  Status: $STATUS_SYMBOL"
    box_line "  Workflow: $wf"
    box_line ""

    if [ "$num_workers" -le 1 ]; then
        # 1ワーカー: Pattern A同様の横一列
        box_line "  ┌──────────┐     ┌────────┐           ┌──────────┐"
        box_line "  │Conductor │ $ARROW_S │Dispatch│ $ARROW_L │ Worker-1 │"
        box_line "  │  (opus)  │     │(sonnet)│           │ $w1   │"
        box_line "  └──────────┘     └────────┘           └──────────┘"
    else
        # 2+ワーカー: Dispatchから分岐（横展開 + 縦並び）
        box_line "  ┌──────────┐     ┌────────┐          ┌──────────┐"
        box_line "  │Conductor │ $ARROW_S │Dispatch│ $ARROW_FORK │ Worker-1 │"
        box_line "  │  (opus)  │     │(sonnet)│    │     │ $w1   │"
        box_line "  └──────────┘     └────────┘    │     └──────────┘"

        # 追加ワーカーを縦に並べる（DispatchのY軸延長から分岐）
        # ┬は位置33（0-indexed）: "  │Conductor │ ──→ │Dispatch│ " = 33文字
        local PRE33="                                 "   # 33スペース
        local PRE39="                                       "  # 39スペース
        local i
        for i in $(seq 2 "$num_workers"); do
            local wi
            wi=$(get_worker_state "$i")
            if [ "$i" -lt "$num_workers" ]; then
                # 中間ワーカー: ├───→
                box_line "${PRE33}│     ┌──────────┐"
                box_line "${PRE33}├$ARROW_F │ Worker-$i │"
                box_line "${PRE33}│     │ $wi   │"
                box_line "${PRE33}│     └──────────┘"
            else
                # 最後のワーカー: └───→
                box_line "${PRE33}│     ┌──────────┐"
                box_line "${PRE33}└$ARROW_F │ Worker-$i │"
                box_line "${PRE39}│ $wi   │"
                box_line "${PRE39}└──────────┘"
            fi
        done
    fi

    box_line ""
    box_line "  $tasks_line"
    printf '%s\n' "$BORDER_BOT"
}

# モードC: Conductor → Dispatch → worktrees (横展開)
generate_mode_c() {
    local worktree_count="${WORKTREES:-3}"
    local tasks_line
    tasks_line=$(get_tasks_line)
    local wf="${WORKFLOW:-heavy}"
    local wt_status
    wt_status=$(get_worker_state 1)

    printf '%s\n' "$BORDER_TOP"
    box_line "  ⚡ EXECUTION MODE"
    printf '%s\n' "$BORDER_SEP"
    box_line ""
    box_line "  Mode: C - Isolated (worktree)"
    box_line "  Status: $STATUS_SYMBOL"
    box_line "  Workflow: $wf"
    box_line ""
    box_line "  ┌──────────┐     ┌────────┐"
    box_line "  │Conductor │ $ARROW_S │Dispatch│"
    box_line "  │  (opus)  │     │(sonnet)│"
    box_line "  └──────────┘     └───┬────┘"
    box_line ""

    if [ "$worktree_count" -eq 2 ]; then
        box_line "          ┌──────────┴──────────┐"
        box_line "          ▼                     ▼"
        box_line "    ┌──────────┐         ┌──────────┐"
        box_line "    │ worktree │         │ worktree │"
        box_line "    │  feat-1  │         │  feat-2  │"
        box_line "    │$wt_status Worker │         │$wt_status Worker │"
        box_line "    └──────────┘         └──────────┘"
    elif [ "$worktree_count" -eq 3 ]; then
        box_line "       ┌──────────┼──────────┐"
        box_line "       ▼          ▼          ▼"
        box_line "  ┌──────────┐┌──────────┐┌──────────┐"
        box_line "  │ worktree ││ worktree ││ worktree │"
        box_line "  │  feat-1  ││  feat-2  ││  feat-3  │"
        box_line "  │$wt_status││$wt_status││$wt_status│"
        box_line "  └──────────┘└──────────┘└──────────┘"
    else
        box_line "       ┌──────────┼──────────┐"
        box_line "       ▼          ▼          ▼"
        box_line "  ┌──────────┐┌──────────┐┌──────────┐"
        box_line "  │ worktree ││ worktree ││   ...    │"
        box_line "  │  feat-1  ││  feat-2  ││($worktree_count total)│"
        box_line "  │$wt_status││$wt_status││          │"
        box_line "  └──────────┘└──────────┘└──────────┘"
    fi

    box_line ""
    box_line "  $tasks_line"
    printf '%s\n' "$BORDER_BOT"
}

# モードT: Conductor (Team Lead) → Teammates (横展開)
generate_mode_t() {
    local teammate_count="${TEAMMATES:-3}"
    local tm_status
    tm_status=$(get_worker_state 1)

    printf '%s\n' "$BORDER_TOP"
    box_line "  🔬 EXECUTION MODE"
    printf '%s\n' "$BORDER_SEP"
    box_line ""
    box_line "  Mode: T - Research (Agent Teams)"
    box_line "  Status: $STATUS_SYMBOL"
    box_line ""
    box_line "            ┌──────────────┐"
    box_line "            │  Conductor   │"
    box_line "            │ (Team Lead)  │"
    box_line "            └──────┬───────┘"
    box_line ""

    if [ "$teammate_count" -eq 2 ]; then
        box_line "         ┌─────┴─────┐"
        box_line "         ▼           ▼"
        box_line "    ┌────────┐  ┌────────┐"
        box_line "    │Mate #1 │  │Mate #2 │"
        box_line "    │security│  │  perf  │"
        box_line "    │$tm_status│  │$tm_status│"
        box_line "    └────────┘  └────────┘"
        box_line "        ↕           ↕"
        box_line "    [ mailbox: discussion active ]"
    elif [ "$teammate_count" -eq 3 ]; then
        box_line "         ┌─────┼─────┐"
        box_line "         ▼     ▼     ▼"
        box_line "    ┌────────┐┌────────┐┌────────┐"
        box_line "    │Mate #1 ││Mate #2 ││Mate #3 │"
        box_line "    │security││  perf  ││  test  │"
        box_line "    │$tm_status││$tm_status││$tm_status│"
        box_line "    └────────┘└────────┘└────────┘"
        box_line "        ↕         ↕         ↕"
        box_line "    [ mailbox: discussion active ]"
    else
        box_line "         ┌─────┼─────┼─────┐"
        box_line "         ▼     ▼     ▼     ▼"
        box_line "    ┌────────┐┌────────┐┌────────┐"
        box_line "    │Mate #1 ││Mate #2 ││  ...   │"
        box_line "    │security││  perf  ││($teammate_count total)│"
        box_line "    │$tm_status││$tm_status││$tm_status│"
        box_line "    └────────┘└────────┘└────────┘"
        box_line "        ↕         ↕         ↕"
        box_line "    [ mailbox: discussion active ]"
    fi

    box_line ""
    box_line "  Teammates: $teammate_count active"
    printf '%s\n' "$BORDER_BOT"
}

# モード別に生成してOUTPUT_FILEに書き込む
{
    case $MODE in
        idle) generate_idle ;;
        A)    generate_mode_a ;;
        B)    generate_mode_b ;;
        C)    generate_mode_c ;;
        T)    generate_mode_t ;;
        *)
            echo "Error: Unknown mode: $MODE"
            echo "Valid modes: idle, A, B, C, T"
            exit 1
            ;;
    esac
} > "$OUTPUT_FILE"

# モードパラメータを保存（mode-viz.shが参照する）
mkdir -p "$(dirname "$PARAMS_FILE")"
cat > "$PARAMS_FILE" << EOF
MODE=$MODE
STATUS=$STATUS
WORKERS=${WORKERS:-1}
WORKFLOW=${WORKFLOW:-}
TASKS_TOTAL=$TASKS_TOTAL
TASKS_DONE=$TASKS_DONE
WORKER_STATES=${WORKER_STATES:-}
FRAME=$FRAME
EOF

echo "Mode display updated: $OUTPUT_FILE (mode=$MODE, status=$STATUS)"
