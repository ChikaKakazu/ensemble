#!/bin/bash
# scripts/pane-setup.sh
# ワーカーペインを既存のmainウィンドウに追加する（右側縦並び）
# フレンドリーファイア防止のため3秒間隔で起動
#
# 注意: ペインIDを使用することで、ユーザーのtmux設定（pane-base-index等）に
#       依存せずに動作する
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
PANES_FILE="$PROJECT_DIR/.ensemble/panes.env"

# 最大4ワーカー（Claude Max 5並列 - Conductor用1を除く）
if [ "$WORKER_COUNT" -gt 4 ]; then
    echo "Warning: Max 4 workers allowed. Reducing from $WORKER_COUNT to 4."
    WORKER_COUNT=4
fi

# panes.env から既存のペインIDを読み込む
if [ -f "$PANES_FILE" ]; then
    source "$PANES_FILE"
else
    echo "Error: $PANES_FILE not found. Run launch.sh first."
    exit 1
fi

echo "Adding $WORKER_COUNT worker panes..."
echo "  Using dashboard pane: $DASHBOARD_PANE"

# mainウィンドウを選択
tmux select-window -t "$SESSION:main"

# ワーカーペインIDを格納する配列
declare -a WORKER_PANES=()

# 現在のペインID一覧を取得（後で新しいペインを特定するため）
get_all_pane_ids() {
    tmux list-panes -t "$SESSION:main" -F '#{pane_id}'
}

for i in $(seq 1 "$WORKER_COUNT"); do
    echo "Starting worker-$i..."

    # 分割前のペインID一覧
    BEFORE_PANES=$(get_all_pane_ids)

    # dashboardペインを上に分割してワーカーを追加
    tmux split-window -v -t "$DASHBOARD_PANE" -c "$PROJECT_DIR" -b

    # フレンドリーファイア防止
    sleep 2

    # 分割後のペインID一覧から新しいペインを特定
    AFTER_PANES=$(get_all_pane_ids)
    NEW_PANE=$(comm -13 <(echo "$BEFORE_PANES" | sort) <(echo "$AFTER_PANES" | sort))

    echo "  Worker-$i pane: $NEW_PANE"
    WORKER_PANES+=("$NEW_PANE")

    # WORKER_ID環境変数を設定して、--agent workerでClaudeを起動
    # 重要: send-keysは2回分割で送信（shogunパターン）
    tmux send-keys -t "$NEW_PANE" \
        "export WORKER_ID=$i && claude --agent worker --dangerously-skip-permissions"
    sleep 1
    tmux send-keys -t "$NEW_PANE" Enter
done

# 全ワーカーのClaude起動完了を待つ（各ワーカー約10秒）
echo "Waiting for all workers to initialize..."
sleep $((WORKER_COUNT * 10))

# Conductorペインにフォーカスを戻す
tmux select-pane -t "$CONDUCTOR_PANE"

# panes.env を更新（ワーカーペインIDを追加）
{
    echo "# Ensemble pane IDs (auto-generated)"
    echo "CONDUCTOR_PANE=$CONDUCTOR_PANE"
    echo "DISPATCH_PANE=$DISPATCH_PANE"
    echo "DASHBOARD_PANE=$DASHBOARD_PANE"
    for idx in "${!WORKER_PANES[@]}"; do
        echo "WORKER_$((idx + 1))_PANE=${WORKER_PANES[$idx]}"
    done
    echo "WORKER_COUNT=$WORKER_COUNT"
} > "$PANES_FILE"

echo ""
echo "Worker panes added: $WORKER_COUNT workers (ready for tasks)"
echo ""
echo "Current panes:"
tmux list-panes -t "$SESSION:main" -F "  #{pane_id}: #{pane_width}x#{pane_height}"
