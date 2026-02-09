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

# Agent Teams モード検出
AGENT_TEAMS_MODE="${CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS:-0}"
if [ "$AGENT_TEAMS_MODE" = "1" ]; then
    echo "Launching Ensemble..."
    echo "  Agent Teams Mode: available (for research/review tasks)"
else
    echo "Launching Ensemble..."
    echo "  Agent Teams Mode: disabled (set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 to enable)"
fi

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
# セッション1: conductor
# +------------------+------------------+
# |   Conductor      |   dashboard      |
# +------------------+------------------+
#
# セッション2: workers
# +------------------+------------------+
# |   dispatch       |   worker-area    |
# +------------------+------------------+

# === セッション1: Conductor ===
echo "Creating conductor session..."
tmux new-session -d -s "$SESSION_CONDUCTOR" -n "main" -c "$PROJECT_DIR"

# conductorペインのIDを取得
CONDUCTOR_PANE=$(tmux list-panes -t "$SESSION_CONDUCTOR:main" -F '#{pane_id}')
echo "  Conductor pane: $CONDUCTOR_PANE"

# 左右に分割（左60% : 右40%）- 右側はdashboard
# split-windowは新しいペインIDを返すので、それを直接キャプチャする
DASHBOARD_PANE=$(tmux split-window -h -t "$CONDUCTOR_PANE" -c "$PROJECT_DIR" -l 40% -P -F '#{pane_id}')
echo "  Dashboard pane: $DASHBOARD_PANE"

# conductor (--agent でエージェント定義をロード)
echo "Starting Conductor (Opus, no thinking)..."
tmux send-keys -t "$CONDUCTOR_PANE" \
    "MAX_THINKING_TOKENS=0 claude --agent conductor --model opus --dangerously-skip-permissions"
sleep 1
tmux send-keys -t "$CONDUCTOR_PANE" Enter

# dashboard (watch for periodic refresh, Ctrl+C to stop)
echo "Starting Dashboard monitor (in conductor session)..."
tmux send-keys -t "$DASHBOARD_PANE" \
    "watch -n 5 -t cat .ensemble/status/dashboard.md"
sleep 1
tmux send-keys -t "$DASHBOARD_PANE" Enter

# conductorペインを選択
tmux select-pane -t "$CONDUCTOR_PANE"

# フレンドリーファイア防止
sleep 3

# === セッション2: Workers ===
echo "Creating workers session..."
tmux new-session -d -s "$SESSION_WORKERS" -n "main" -c "$PROJECT_DIR"

# 最初のペインのIDを取得（これがdispatchになる）
DISPATCH_PANE=$(tmux list-panes -t "$SESSION_WORKERS:main" -F '#{pane_id}')
echo "  Dispatch pane: $DISPATCH_PANE"

# 左右に分割（左60% : 右40%）- 右側はワーカー用
# split-windowは新しいペインIDを返すので、それを直接キャプチャする
WORKER_AREA_PANE=$(tmux split-window -h -t "$DISPATCH_PANE" -c "$PROJECT_DIR" -l 40% -P -F '#{pane_id}')
echo "  Worker area pane: $WORKER_AREA_PANE"

# 現在の状態:
# DISPATCH_PANE: dispatch (左、フルハイト)
# WORKER_AREA_PANE: ワーカー用プレースホルダー (右、フルハイト)

# dispatch (--agent でエージェント定義をロード)
echo "Starting Dispatch (Sonnet)..."
tmux send-keys -t "$DISPATCH_PANE" \
    "claude --agent dispatch --model sonnet --dangerously-skip-permissions"
sleep 1
tmux send-keys -t "$DISPATCH_PANE" Enter

# フレンドリーファイア防止
sleep 3

# 右側のプレースホルダーにメッセージ表示
tmux send-keys -t "$WORKER_AREA_PANE" \
    "echo '=== Worker Area ===' && echo 'Run: ./scripts/pane-setup.sh [count]' && echo 'to add workers here.'"
sleep 1
tmux send-keys -t "$WORKER_AREA_PANE" Enter

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
WORKER_AREA_PANE=$WORKER_AREA_PANE

# Agent Teams mode
AGENT_TEAMS_MODE=$AGENT_TEAMS_MODE

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
echo "  +------------------+------------------+"
echo "  |   Conductor      |   dashboard      |"
echo "  +------------------+------------------+"
echo ""
echo "Session 2: $SESSION_WORKERS"
echo "  +------------------+------------------+"
echo "  |   dispatch       |   worker-area    |"
echo "  +------------------+------------------+"
echo ""
echo "Panes:"
echo "  - $CONDUCTOR_PANE : Conductor (Opus, no thinking)"
echo "  - $DASHBOARD_PANE : Dashboard monitor"
echo "  - $DISPATCH_PANE  : Dispatch (Sonnet)"
echo "  - $WORKER_AREA_PANE : Worker area (placeholder)"
echo ""
echo "To view both simultaneously, open two terminal windows:"
echo "  Terminal 1: tmux attach -t $SESSION_CONDUCTOR"
echo "  Terminal 2: tmux attach -t $SESSION_WORKERS"
echo ""
echo "Add workers: ./scripts/pane-setup.sh [count]"
echo ""
if [ "$AGENT_TEAMS_MODE" = "1" ]; then
    echo "=== Agent Teams Mode ==="
    echo "  Available for research/review tasks (not for code implementation)."
    echo "  Conductor acts as Team Lead for investigation/review teams."
    echo "  Use Pattern A/B/C for actual code implementation."
    echo ""
fi
