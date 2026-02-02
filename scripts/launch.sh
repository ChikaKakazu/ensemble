#!/bin/bash
# scripts/launch.sh
# Ensembleのメインtmuxセッションを起動する
# 構成: 左=conductor、右=その他（tiled）

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

# === レイアウト ===
# +------------------+----------+
# |    conductor     |          |
# |                  | dashboard|
# +------------------+          |
# |    dispatch      |          |
# +------------------+----------+
# ワーカー追加時はdashboard列に縦に追加される

# 1. セッション作成（全体）
echo "Starting Conductor (Opus, no thinking)..."
tmux new-session -d -s "$SESSION" -n "main" -c "$PROJECT_DIR"

# 2. 左右に分割（左65% : 右35%）
tmux split-window -h -t "$SESSION:main" -c "$PROJECT_DIR" -l 35%

# 3. 左ペイン(0)を上下に分割（conductor / dispatch）
tmux split-window -v -t "$SESSION:main.0" -c "$PROJECT_DIR" -l 50%

# 現在の状態:
# pane 0: conductor (左上)
# pane 1: dispatch (左下)
# pane 2: dashboard (右、フル高さ)

# 4. 各ペインでコマンド起動
# pane 0: conductor (--agent でエージェント定義をロード)
tmux send-keys -t "$SESSION:main.0" \
    "MAX_THINKING_TOKENS=0 claude --agent conductor --model opus --dangerously-skip-permissions" C-m

# フレンドリーファイア防止
sleep 3

# pane 1: dispatch (--agent でエージェント定義をロード)
echo "Starting Dispatch (Sonnet)..."
tmux send-keys -t "$SESSION:main.1" \
    "claude --agent dispatch --model sonnet --dangerously-skip-permissions" C-m

# フレンドリーファイア防止
sleep 3

# pane 2: dashboard
echo "Starting Dashboard monitor..."
tmux send-keys -t "$SESSION:main.2" \
    "watch -n 5 cat status/dashboard.md" C-m

# 5. 左上ペイン（conductor）にフォーカス
tmux select-pane -t "$SESSION:main.0"

echo ""
echo "=========================================="
echo "  Ensemble launched successfully!"
echo "=========================================="
echo ""
echo "Layout:"
echo "  +------------------+----------+"
echo "  |    conductor     |          |"
echo "  |                  | dashboard|"
echo "  +------------------+          |"
echo "  |    dispatch      |          |"
echo "  +------------------+----------+"
echo ""
echo "Panes:"
echo "  - pane 0 (left-top)   : Conductor (Opus, no thinking)"
echo "  - pane 1 (left-bottom): Dispatch (Sonnet)"
echo "  - pane 2 (right)      : Dashboard monitor"
echo ""
echo "Add workers: ./scripts/pane-setup.sh [count]"
echo "To attach:   tmux attach-session -t $SESSION"
echo ""
