#!/bin/bash
# scripts/launch.sh
# Ensembleのメインtmuxセッションを起動する
# 構成: 左=conductor、右=その他（tiled）
#
# 注意: ペインIDを使用することで、ユーザーのtmux設定（pane-base-index等）に
#       依存せずに動作する

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
echo "Creating session..."
tmux new-session -d -s "$SESSION" -n "main" -c "$PROJECT_DIR"

# 最初のペインのIDを取得（これがconductorになる）
CONDUCTOR_PANE=$(tmux list-panes -t "$SESSION:main" -F '#{pane_id}')
echo "  Conductor pane: $CONDUCTOR_PANE"

# 2. 左右に分割（左65% : 右35%）
tmux split-window -h -t "$CONDUCTOR_PANE" -c "$PROJECT_DIR" -l 35%

# 新しく作成されたペインのIDを取得（これがdashboardになる）
DASHBOARD_PANE=$(tmux list-panes -t "$SESSION:main" -F '#{pane_id}' | grep -v "$CONDUCTOR_PANE")
echo "  Dashboard pane: $DASHBOARD_PANE"

# 3. 左ペイン（conductor）を上下に分割（conductor / dispatch）
tmux split-window -v -t "$CONDUCTOR_PANE" -c "$PROJECT_DIR" -l 50%

# 新しく作成されたペインのIDを取得（これがdispatchになる）
# conductorとdashboard以外のペインがdispatch
DISPATCH_PANE=$(tmux list-panes -t "$SESSION:main" -F '#{pane_id}' | grep -v "$CONDUCTOR_PANE" | grep -v "$DASHBOARD_PANE")
echo "  Dispatch pane: $DISPATCH_PANE"

# 現在の状態:
# CONDUCTOR_PANE: conductor (左上)
# DISPATCH_PANE: dispatch (左下)
# DASHBOARD_PANE: dashboard (右、フル高さ)

# 4. 各ペインでコマンド起動（2回分割方式）
# conductor (--agent でエージェント定義をロード)
echo "Starting Conductor (Opus, no thinking)..."
tmux send-keys -t "$CONDUCTOR_PANE" \
    "MAX_THINKING_TOKENS=0 claude --agent conductor --model opus --dangerously-skip-permissions"
sleep 1
tmux send-keys -t "$CONDUCTOR_PANE" Enter

# フレンドリーファイア防止
sleep 3

# dispatch (--agent でエージェント定義をロード)
echo "Starting Dispatch (Sonnet)..."
tmux send-keys -t "$DISPATCH_PANE" \
    "claude --agent dispatch --model sonnet --dangerously-skip-permissions"
sleep 1
tmux send-keys -t "$DISPATCH_PANE" Enter

# フレンドリーファイア防止
sleep 3

# dashboard
echo "Starting Dashboard monitor..."
tmux send-keys -t "$DASHBOARD_PANE" \
    "watch -n 5 cat status/dashboard.md"
sleep 1
tmux send-keys -t "$DASHBOARD_PANE" Enter

# 5. conductorペインにフォーカス
tmux select-pane -t "$CONDUCTOR_PANE"

# ペインIDをファイルに保存（他のスクリプトから参照可能に）
mkdir -p "$PROJECT_DIR/.ensemble"
cat > "$PROJECT_DIR/.ensemble/panes.env" << EOF
# Ensemble pane IDs (auto-generated)
CONDUCTOR_PANE=$CONDUCTOR_PANE
DISPATCH_PANE=$DISPATCH_PANE
DASHBOARD_PANE=$DASHBOARD_PANE
EOF

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
echo "  - $CONDUCTOR_PANE (left-top)   : Conductor (Opus, no thinking)"
echo "  - $DISPATCH_PANE (left-bottom): Dispatch (Sonnet)"
echo "  - $DASHBOARD_PANE (right)      : Dashboard monitor"
echo ""
echo "Add workers: ./scripts/pane-setup.sh [count]"
echo "To attach:   tmux attach-session -t $SESSION"
echo ""
