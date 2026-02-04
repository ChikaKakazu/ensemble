#!/bin/bash
# scripts/launch.sh
# Ensembleのメインtmuxセッションを起動する
# 構成: 2ウィンドウ（conductor独立 + workers）
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
rm -f "$QUEUE_DIR/conductor/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/tasks/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/processing/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/reports/"*.yaml 2>/dev/null || true
rm -f "$QUEUE_DIR/ack/"*.ack 2>/dev/null || true

# ログに記録
echo "$(date -Iseconds) Session started, queue cleaned" >> "$LOG_DIR/ensemble-$(date +%Y%m%d).log"

# === レイアウト ===
# ウィンドウ1: conductor（フルスクリーン）
# +----------------------------------+
# |                                  |
# |           Conductor              |
# |                                  |
# +----------------------------------+
#
# ウィンドウ2: workers
# +------------------+----------+
# |    dispatch      | (worker) |
# +------------------+----------+
# |    dashboard     | (worker) |
# +------------------+----------+

# 1. セッション作成（conductorウィンドウ）
echo "Creating session with conductor window..."
tmux new-session -d -s "$SESSION" -n "conductor" -c "$PROJECT_DIR"

# conductorペインのIDを取得
CONDUCTOR_PANE=$(tmux list-panes -t "$SESSION:conductor" -F '#{pane_id}')
echo "  Conductor pane: $CONDUCTOR_PANE"

# 2. workersウィンドウを追加
echo "Creating workers window..."
tmux new-window -t "$SESSION" -n "workers" -c "$PROJECT_DIR"

# 最初のペインのIDを取得（これがdispatchになる）
DISPATCH_PANE=$(tmux list-panes -t "$SESSION:workers" -F '#{pane_id}')
echo "  Dispatch pane: $DISPATCH_PANE"

# 3. 左右に分割（左60% : 右40%）- 右側はワーカー用
tmux split-window -h -t "$DISPATCH_PANE" -c "$PROJECT_DIR" -l 40%

# 右側のペインIDを取得（ワーカー用プレースホルダー）
RIGHT_PANE=$(tmux list-panes -t "$SESSION:workers" -F '#{pane_id}' | grep -v "$DISPATCH_PANE")
echo "  Right pane (for workers): $RIGHT_PANE"

# 4. 左ペイン（dispatch）を上下に分割（dispatch / dashboard）
tmux split-window -v -t "$DISPATCH_PANE" -c "$PROJECT_DIR" -l 50%

# dashboardペインIDを取得（dispatchとright以外）
DASHBOARD_PANE=$(tmux list-panes -t "$SESSION:workers" -F '#{pane_id}' | grep -v "$DISPATCH_PANE" | grep -v "$RIGHT_PANE")
echo "  Dashboard pane: $DASHBOARD_PANE"

# 現在の状態:
# DISPATCH_PANE: dispatch (左上)
# DASHBOARD_PANE: dashboard (左下)
# RIGHT_PANE: ワーカー用プレースホルダー (右)

# 5. 各ペインでコマンド起動

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

# 右側のプレースホルダーにメッセージ表示
tmux send-keys -t "$RIGHT_PANE" \
    "echo '=== Worker Area ===' && echo 'Run: ./scripts/pane-setup.sh [count]' && echo 'to add workers here.'"
sleep 1
tmux send-keys -t "$RIGHT_PANE" Enter

# 6. conductorウィンドウに戻り、conductorペインにフォーカス
tmux select-window -t "$SESSION:conductor"
tmux select-pane -t "$CONDUCTOR_PANE"

# ペインIDをファイルに保存（他のスクリプトから参照可能に）
mkdir -p "$PROJECT_DIR/.ensemble"
cat > "$PROJECT_DIR/.ensemble/panes.env" << EOF
# Ensemble pane IDs (auto-generated)
# Window names
CONDUCTOR_WINDOW=conductor
WORKERS_WINDOW=workers

# Pane IDs
CONDUCTOR_PANE=$CONDUCTOR_PANE
DISPATCH_PANE=$DISPATCH_PANE
DASHBOARD_PANE=$DASHBOARD_PANE
WORKER_AREA_PANE=$RIGHT_PANE
EOF

echo ""
echo "=========================================="
echo "  Ensemble launched successfully!"
echo "=========================================="
echo ""
echo "Window 1: conductor (user interaction)"
echo "  +----------------------------------+"
echo "  |           Conductor              |"
echo "  |         (claude CLI)             |"
echo "  +----------------------------------+"
echo ""
echo "Window 2: workers (execution)"
echo "  +------------------+----------+"
echo "  |    dispatch      | (worker) |"
echo "  +------------------+----------+"
echo "  |    dashboard     | (worker) |"
echo "  +------------------+----------+"
echo ""
echo "Panes:"
echo "  - $CONDUCTOR_PANE : Conductor (Opus, no thinking)"
echo "  - $DISPATCH_PANE  : Dispatch (Sonnet)"
echo "  - $DASHBOARD_PANE : Dashboard monitor"
echo "  - $RIGHT_PANE     : Worker area (placeholder)"
echo ""
echo "Window switching:"
echo "  Ctrl+B, n    : Next window"
echo "  Ctrl+B, p    : Previous window"
echo "  Ctrl+B, 0    : conductor window"
echo "  Ctrl+B, 1    : workers window"
echo ""
echo "Add workers: ./scripts/pane-setup.sh [count]"
echo "To attach:   tmux attach-session -t $SESSION"
echo ""
