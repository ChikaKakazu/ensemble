#!/bin/bash
# scripts/pane-setup.sh
# ワーカーペインを既存のmainウィンドウに追加する（右側縦並び）
# フレンドリーファイア防止のため3秒間隔で起動
#
# 初期レイアウト:
# +------------------+----------+
# |    conductor     |          |
# |                  | dashboard|
# +------------------+          |
# |    dispatch      |          |
# +------------------+----------+
#
# ワーカー追加後:
# +------------------+----------+
# |    conductor     | worker-1 |
# |                  +----------+
# +------------------+ worker-2 |
# |    dispatch      +----------+
# |                  | dashboard|
# +------------------+----------+

set -euo pipefail

SESSION="${SESSION:-ensemble}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
WORKER_COUNT="${1:-2}"  # デフォルト2ワーカー

# 最大4ワーカー（Claude Max 5並列 - Conductor用1を除く）
if [ "$WORKER_COUNT" -gt 4 ]; then
    echo "Warning: Max 4 workers allowed. Reducing from $WORKER_COUNT to 4."
    WORKER_COUNT=4
fi

echo "Adding $WORKER_COUNT worker panes..."

# mainウィンドウを選択
tmux select-window -t "$SESSION:main"

# 初期状態: pane 0=conductor, pane 1=dispatch, pane 2=dashboard
# ワーカーを dashboard(2) の上に挿入する

for i in $(seq 1 "$WORKER_COUNT"); do
    echo "Starting worker-$i..."

    # dashboard(pane 2)を上に分割してワーカーを追加
    tmux split-window -v -t "$SESSION:main.2" -c "$PROJECT_DIR" -b

    # フレンドリーファイア防止
    sleep 3

    # WORKER_ID環境変数を設定して、--agent workerでClaudeを起動
    tmux send-keys -t "$SESSION:main.2" \
        "export WORKER_ID=$i && claude --agent worker --dangerously-skip-permissions" Enter
done

# 全ワーカーのClaude起動完了を待つ（各ワーカー約10秒）
echo "Waiting for all workers to initialize..."
sleep $((WORKER_COUNT * 10))

# Conductorペインにフォーカスを戻す
tmux select-pane -t "$SESSION:main.0"

echo ""
echo "Worker panes added: $WORKER_COUNT workers (ready for tasks)"
echo ""
echo "Current panes:"
tmux list-panes -t "$SESSION:main" -F "  pane #{pane_index}: #{pane_width}x#{pane_height}"
