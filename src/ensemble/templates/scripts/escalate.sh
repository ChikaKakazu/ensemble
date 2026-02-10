#!/bin/bash
# 3段階自動エスカレーションスクリプト
# 引数: PANE_ID WORKER_ID PHASE(1/2/3)

set -e

# 引数バリデーション
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 PANE_ID WORKER_ID PHASE" >&2
    exit 1
fi

PANE_ID="$1"
WORKER_ID="$2"
PHASE="$3"

# ログ出力
echo "[escalate] Phase $PHASE for worker-$WORKER_ID (pane: $PANE_ID)" >&2

case "$PHASE" in
    1)
        # Phase 1: 通常nudge（send-keys再送）
        echo "[escalate] Phase 1: Sending normal nudge" >&2
        tmux send-keys -t "$PANE_ID" "queue/tasks/worker-${WORKER_ID}-task.yaml を確認して実行してください"
        tmux send-keys -t "$PANE_ID" Enter
        ;;
    2)
        # Phase 2: Escape×2 + C-c + nudge
        echo "[escalate] Phase 2: Escape×2 + C-c + nudge" >&2
        tmux send-keys -t "$PANE_ID" Escape
        sleep 0.5
        tmux send-keys -t "$PANE_ID" Escape
        sleep 0.5
        tmux send-keys -t "$PANE_ID" C-c
        sleep 1
        tmux send-keys -t "$PANE_ID" "queue/tasks/worker-${WORKER_ID}-task.yaml を確認して実行してください"
        tmux send-keys -t "$PANE_ID" Enter
        ;;
    3)
        # Phase 3: /clear + nudge
        echo "[escalate] Phase 3: /clear + nudge" >&2
        tmux send-keys -t "$PANE_ID" '/clear'
        tmux send-keys -t "$PANE_ID" Enter
        sleep 5  # /clear処理完了待ち
        tmux send-keys -t "$PANE_ID" "queue/tasks/worker-${WORKER_ID}-task.yaml を確認して実行してください"
        tmux send-keys -t "$PANE_ID" Enter
        ;;
    *)
        echo "Error: Invalid phase '$PHASE'. Must be 1, 2, or 3." >&2
        exit 1
        ;;
esac

echo "[escalate] Phase $PHASE completed for worker-$WORKER_ID" >&2
