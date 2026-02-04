#!/bin/bash
# scripts/launch.sh
# Ensembleの2セッションtmux環境を起動する
# 構成: 2つの独立したセッション（conductor専用 + workers）
#
# これにより、2つのターミナルウィンドウで同時に監視できる
#
# 注意: ペインIDを使用することで、ユーザーのtmux設定（pane-base-index等）に
#       依存せずに動作する

set -euo pipefail

SESSION_BASE="${SESSION_BASE:-ensemble}"
SESSION_CONDUCTOR="${SESSION_BASE}-conductor"
SESSION_WORKERS="${SESSION_BASE}-workers"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
LOG_DIR="$PROJECT_DIR/logs"
QUEUE_DIR="$PROJECT_DIR/queue"

echo "Launching Ensemble..."

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# キューディレクトリ作成
mkdir -p "$QUEUE_DIR/tasks" "$QUEUE_DIR/processing" "$QUEUE_DIR/reports" "$QUEUE_DIR/ack" "$QUEUE_DIR/conductor"

# 既存セッションがあれば削除
if tmux has-session -t "$SESSION_CONDUCTOR" 2>/dev/null; then
    echo "Killing existing conductor session..."
    tmux kill-session -t "$SESSION_CONDUCTOR"
fi
if tmux has-session -t "$SESSION_WORKERS" 2>/dev/null; then
    echo "Killing existing workers session..."
    tmux kill-session -t "$SESSION_WORKERS"
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
# セッション1: conductor（フルスクリーン）
# +----------------------------------+
# |                                  |
# |           Conductor              |
# |                                  |
# +----------------------------------+
#
# セッション2: workers
# +------------------+----------+
# |    dispatch      | (worker) |
# +------------------+----------+
# |    dashboard     | (worker) |
# +------------------+----------+

# === セッション1: Conductor ===
echo "Creating conductor session..."
tmux new-session -d -s "$SESSION_CONDUCTOR" -n "main" -c "$PROJECT_DIR"

# conductorペインのIDを取得
CONDUCTOR_PANE=$(tmux list-panes -t "$SESSION_CONDUCTOR:main" -F '#{pane_id}')
echo "  Conductor pane: $CONDUCTOR_PANE"

# conductor (--agent でエージェント定義をロード)
echo "Starting Conductor (Opus, no thinking)..."
tmux send-keys -t "$CONDUCTOR_PANE" \
    "MAX_THINKING_TOKENS=0 claude --agent conductor --model opus --dangerously-skip-permissions"
sleep 1
tmux send-keys -t "$CONDUCTOR_PANE" Enter

# フレンドリーファイア防止
sleep 3

# === セッション2: Workers ===
echo "Creating workers session..."
tmux new-session -d -s "$SESSION_WORKERS" -n "main" -c "$PROJECT_DIR"

# 最初のペインのIDを取得（これがdispatchになる）
DISPATCH_PANE=$(tmux list-panes -t "$SESSION_WORKERS:main" -F '#{pane_id}')
echo "  Dispatch pane: $DISPATCH_PANE"

# 左右に分割（左60% : 右40%）- 右側はワーカー用
tmux split-window -h -t "$DISPATCH_PANE" -c "$PROJECT_DIR" -l 40%

# 右側のペインIDを取得（ワーカー用プレースホルダー）
RIGHT_PANE=$(tmux list-panes -t "$SESSION_WORKERS:main" -F '#{pane_id}' | grep -v "$DISPATCH_PANE")
echo "  Right pane (for workers): $RIGHT_PANE"

# 左ペイン（dispatch）を上下に分割（dispatch / dashboard）
tmux split-window -v -t "$DISPATCH_PANE" -c "$PROJECT_DIR" -l 50%

# dashboardペインIDを取得（dispatchとright以外）
DASHBOARD_PANE=$(tmux list-panes -t "$SESSION_WORKERS:main" -F '#{pane_id}' | grep -v "$DISPATCH_PANE" | grep -v "$RIGHT_PANE")
echo "  Dashboard pane: $DASHBOARD_PANE"

# 現在の状態:
# DISPATCH_PANE: dispatch (左上)
# DASHBOARD_PANE: dashboard (左下)
# RIGHT_PANE: ワーカー用プレースホルダー (右)

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

# dispatchペインを選択
tmux select-pane -t "$DISPATCH_PANE"

# ペインIDをファイルに保存（他のスクリプトから参照可能に）
mkdir -p "$PROJECT_DIR/.ensemble"
cat > "$PROJECT_DIR/.ensemble/panes.env" << EOF
# Ensemble pane IDs (auto-generated)
# Session names
CONDUCTOR_SESSION=$SESSION_CONDUCTOR
WORKERS_SESSION=$SESSION_WORKERS

# Pane IDs (use these with tmux send-keys -t)
CONDUCTOR_PANE=$CONDUCTOR_PANE
DISPATCH_PANE=$DISPATCH_PANE
DASHBOARD_PANE=$DASHBOARD_PANE
WORKER_AREA_PANE=$RIGHT_PANE

# Usage examples:
# source .ensemble/panes.env
# tmux send-keys -t "\$CONDUCTOR_PANE" 'message' Enter
# tmux send-keys -t "\$DISPATCH_PANE" 'message' Enter
EOF

echo ""
echo "=========================================="
echo "  Ensemble launched successfully!"
echo "=========================================="
echo ""
echo "Two separate tmux sessions created!"
echo ""
echo "Session 1: $SESSION_CONDUCTOR"
echo "  +----------------------------------+"
echo "  |           Conductor              |"
echo "  |         (claude CLI)             |"
echo "  +----------------------------------+"
echo ""
echo "Session 2: $SESSION_WORKERS"
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
echo "To view both simultaneously, open two terminal windows:"
echo "  Terminal 1: tmux attach -t $SESSION_CONDUCTOR"
echo "  Terminal 2: tmux attach -t $SESSION_WORKERS"
echo ""
echo "Add workers: ./scripts/pane-setup.sh [count]"
echo ""
