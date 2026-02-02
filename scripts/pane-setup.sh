#!/bin/bash
# scripts/pane-setup.sh
# ワーカーペインをセットアップする
# フレンドリーファイア防止のため3秒間隔で起動

set -euo pipefail

SESSION="${SESSION:-ensemble}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
WORKER_COUNT="${1:-2}"  # デフォルト2ワーカー

# 最大4ワーカー（Claude Max 5並列 - Conductor用1を除く）
if [ "$WORKER_COUNT" -gt 4 ]; then
    echo "Warning: Max 4 workers allowed. Reducing from $WORKER_COUNT to 4."
    WORKER_COUNT=4
fi

echo "Setting up $WORKER_COUNT worker panes..."

# ワーカーウィンドウ作成（存在しない場合）
if ! tmux has-session -t "$SESSION:workers" 2>/dev/null; then
    tmux new-window -t "$SESSION" -n "workers" -c "$PROJECT_DIR"
fi

# 最初のペインは既存のものを使用
for i in $(seq 1 "$WORKER_COUNT"); do
    PANE_NAME="worker-$i"

    if [ "$i" -eq 1 ]; then
        # 最初のワーカーは既存のペインを使用
        tmux select-window -t "$SESSION:workers"
    else
        # 2つ目以降はペインを分割
        tmux split-window -t "$SESSION:workers" -h -c "$PROJECT_DIR"

        # レイアウトを均等に調整
        tmux select-layout -t "$SESSION:workers" tiled
    fi

    # フレンドリーファイア防止
    sleep 3

    # Claudeを起動（ワーカーモード）
    tmux send-keys -t "$SESSION:workers" \
        "claude --dangerously-skip-permissions" C-m

    echo "Started $PANE_NAME"
done

# レイアウトを最終調整
tmux select-layout -t "$SESSION:workers" tiled

echo "Worker panes setup complete: $WORKER_COUNT workers"
