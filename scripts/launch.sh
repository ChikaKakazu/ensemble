#!/bin/bash
# scripts/launch.sh
# Ensembleのメインtmuxセッションを起動する

set -euo pipefail

SESSION="ensemble"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
LOG_DIR="$PROJECT_DIR/logs"
QUEUE_DIR="$PROJECT_DIR/queue"

echo "Launching Ensemble..."

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# キューディレクトリ作成
mkdir -p "$QUEUE_DIR/tasks" "$QUEUE_DIR/processing" "$QUEUE_DIR/reports" "$QUEUE_DIR/ack"

# 既存セッションがあれば削除
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Killing existing session..."
    tmux kill-session -t "$SESSION"
fi

# キューのクリーンアップ（新しいセッションはクリーンスタート）
echo "Cleaning up queue..."
rm -f "$QUEUE_DIR/tasks/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/processing/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/reports/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/ack/"*.ack 2>/dev/null || true

# ログに記録
echo "$(date -Iseconds) Session started, queue cleaned" >> "$LOG_DIR/ensemble-$(date +%Y%m%d).log"

# === Conductorウィンドウ（Thinking無効） ===
echo "Starting Conductor (Opus, no thinking)..."
tmux new-session -d -s "$SESSION" -n "conductor" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:conductor" \
    "MAX_THINKING_TOKENS=0 claude --model opus --dangerously-skip-permissions" C-m

# フレンドリーファイア防止
sleep 3

# === Dispatchウィンドウ（Sonnet、軽量モデル） ===
echo "Starting Dispatch (Sonnet)..."
tmux new-window -t "$SESSION" -n "dispatch" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:dispatch" \
    "claude --model sonnet --dangerously-skip-permissions" C-m

# フレンドリーファイア防止
sleep 3

# === ダッシュボード用ウィンドウ ===
echo "Starting Dashboard monitor..."
tmux new-window -t "$SESSION" -n "dashboard" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:dashboard" \
    "watch -n 5 cat status/dashboard.md" C-m

echo ""
echo "=========================================="
echo "  Ensemble launched successfully!"
echo "=========================================="
echo ""
echo "Windows:"
echo "  - conductor : Opus (no thinking) - Main brain"
echo "  - dispatch  : Sonnet - Task dispatcher"
echo "  - dashboard : Status monitor (5s refresh)"
echo ""
echo "To attach: tmux attach-session -t $SESSION"
echo ""
