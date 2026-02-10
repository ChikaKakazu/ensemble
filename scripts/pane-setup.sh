#!/bin/bash
# scripts/pane-setup.sh
# ワーカーペインをensemble-workers:mainウィンドウの右側に追加する
# フレンドリーファイア防止のため3秒間隔で起動
#
# 注意: ペインIDを使用することで、ユーザーのtmux設定（pane-base-index等）に
#       依存せずに動作する
#
# 初期レイアウト (launch.sh後):
# Session: ensemble-workers, Window: main
# +------------------+------------------+
# |   dispatch       |   worker-area    |
# +------------------+------------------+
#
# Worker 1追加後:
# +------------------+------------------+
# |   dispatch       |   worker-1       |
# +------------------+------------------+
#
# Worker 2追加後:
# +------------------+----------+
# |                  | worker-1 |
# |   dispatch       +----------+
# |                  | worker-2 |
# +------------------+----------+
#
# Worker 4追加後:
# +------------------+----------+
# |                  | worker-1 |
# |                  +----------+
# |   dispatch       | worker-2 |
# |                  +----------+
# |                  | worker-3 |
# |                  +----------+
# |                  | worker-4 |
# +------------------+----------+

set -euo pipefail

REQUESTED_WORKER_COUNT="${1:-2}"  # 引数を別変数に保存（source上書き防止）
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
PANES_FILE="$PROJECT_DIR/.ensemble/panes.env"

# 最大4ワーカー（Claude Max 5並列 - Conductor用1を除く）
if [ "$REQUESTED_WORKER_COUNT" -gt 4 ]; then
    echo "Warning: Max 4 workers allowed. Reducing from $REQUESTED_WORKER_COUNT to 4."
    REQUESTED_WORKER_COUNT=4
fi

# panes.env から既存のペインIDを読み込む（CONDUCTOR_PANE, DISPATCH_PANE等を取得）
if [ -f "$PANES_FILE" ]; then
    source "$PANES_FILE"
else
    echo "Error: $PANES_FILE not found. Run launch.sh first."
    exit 1
fi

# sourceで上書きされたWORKER_COUNTを引数の値で復元
CONDUCTOR_SESSION="${CONDUCTOR_SESSION:-ensemble-conductor}"
WORKERS_SESSION="${WORKERS_SESSION:-ensemble-workers}"
WORKER_COUNT="$REQUESTED_WORKER_COUNT"

echo "Adding $WORKER_COUNT worker panes to ensemble-workers:main window..."

# ensemble-workersセッションのmainウィンドウを選択
tmux select-window -t "$WORKERS_SESSION:main"

# ワーカーペインIDを格納する配列
declare -a WORKER_PANES=()

# 現在のペインID一覧を取得（後で新しいペインを特定するため）
get_all_pane_ids() {
    tmux list-panes -t "$WORKERS_SESSION:main" -F '#{pane_id}'
}

# 最初のワーカーはWORKER_AREA_PANEを使用（プレースホルダーを置き換え）
if [ -n "${WORKER_AREA_PANE:-}" ]; then
    FIRST_WORKER_PANE="$WORKER_AREA_PANE"
else
    # WORKER_AREA_PANEがない場合は、右側のペインを探す（dispatchでないペイン）
    FIRST_WORKER_PANE=$(tmux list-panes -t "$WORKERS_SESSION:main" -F '#{pane_id}' | \
        grep -v "$DISPATCH_PANE" | head -1)
fi

echo "  First worker will use pane: $FIRST_WORKER_PANE"

for i in $(seq 1 "$WORKER_COUNT"); do
    echo "Starting worker-$i..."

    if [ "$i" -eq 1 ]; then
        # 最初のワーカーはプレースホルダーペインを使用
        NEW_PANE="$FIRST_WORKER_PANE"
    else
        # 2番目以降は右側のペインを分割
        # 分割前のペインID一覧
        BEFORE_PANES=$(get_all_pane_ids)

        # 前のワーカーペインを下に分割
        PREV_PANE="${WORKER_PANES[$((i - 2))]}"
        tmux split-window -v -t "$PREV_PANE" -c "$PROJECT_DIR"

        # フレンドリーファイア防止
        sleep 2

        # 分割後のペインID一覧から新しいペインを特定
        AFTER_PANES=$(get_all_pane_ids)
        NEW_PANE=$(comm -13 <(echo "$BEFORE_PANES" | sort) <(echo "$AFTER_PANES" | sort))
    fi

    echo "  Worker-$i pane: $NEW_PANE"
    WORKER_PANES+=("$NEW_PANE")

    # WORKER_ID環境変数を設定して、--agentでClaudeを起動
    # WORKER_AGENT環境変数が設定されていればそれを使用、なければ worker をデフォルト
    # 重要: send-keysは2回分割で送信（shogunパターン）
    AGENT_NAME="${WORKER_AGENT:-worker}"
    tmux send-keys -t "$NEW_PANE" \
        "export WORKER_ID=$i && claude --agent $AGENT_NAME --dangerously-skip-permissions"
    sleep 1
    tmux send-keys -t "$NEW_PANE" Enter

    # フレンドリーファイア防止（最初以外）
    if [ "$i" -lt "$WORKER_COUNT" ]; then
        sleep 3
    fi
done

# 全ワーカーのClaude起動完了を待つ（各ワーカー約10秒）
echo "Waiting for all workers to initialize..."
sleep $((WORKER_COUNT * 10))

# Conductorセッションのmainウィンドウに戻り、フォーカス
tmux select-window -t "$CONDUCTOR_SESSION:main"
tmux select-pane -t "$CONDUCTOR_PANE"

# panes.env を更新（ワーカーペインIDを追加）
{
    echo "# Ensemble pane IDs (auto-generated)"
    echo "# Session names"
    echo "CONDUCTOR_SESSION=$CONDUCTOR_SESSION"
    echo "WORKERS_SESSION=$WORKERS_SESSION"
    echo ""
    echo "# Pane IDs"
    echo "CONDUCTOR_PANE=$CONDUCTOR_PANE"
    echo "DISPATCH_PANE=$DISPATCH_PANE"
    echo "WORKER_AREA_PANE=${WORKER_AREA_PANE:-}"
    for idx in "${!WORKER_PANES[@]}"; do
        echo "WORKER_$((idx + 1))_PANE=${WORKER_PANES[$idx]}"
    done
    echo "WORKER_COUNT=$WORKER_COUNT"
} > "$PANES_FILE"

echo ""
echo "Worker panes added: $WORKER_COUNT workers (ready for tasks)"
echo ""
echo "Layout (ensemble-workers:main window):"
if [ "$WORKER_COUNT" -eq 1 ]; then
    echo "  +------------------+------------------+"
    echo "  |   dispatch       |   worker-1       |"
    echo "  +------------------+------------------+"
elif [ "$WORKER_COUNT" -eq 2 ]; then
    echo "  +------------------+----------+"
    echo "  |                  | worker-1 |"
    echo "  |   dispatch       +----------+"
    echo "  |                  | worker-2 |"
    echo "  +------------------+----------+"
else
    echo "  +------------------+----------+"
    echo "  |                  | worker-1 |"
    echo "  |                  +----------+"
    echo "  |   dispatch       | worker-2 |"
    echo "  |                  +----------+"
    if [ "$WORKER_COUNT" -ge 3 ]; then
        echo "  |                  | worker-3 |"
        echo "  |                  +----------+"
    fi
    if [ "$WORKER_COUNT" -ge 4 ]; then
        echo "  |                  | worker-4 |"
        echo "  +------------------+----------+"
    else
        echo "  +------------------+----------+"
    fi
fi
echo ""
echo "Current panes in ensemble-workers:main window:"
tmux list-panes -t "$WORKERS_SESSION:main" -F "  #{pane_id}: #{pane_width}x#{pane_height}"
echo ""
echo "Switch to workers window: tmux attach -t $WORKERS_SESSION"
echo ""

# ワーカー起動完了後にモード表示を更新
if [ -f "$PROJECT_DIR/scripts/update-mode.sh" ]; then
    if [ "$WORKER_COUNT" -eq 1 ]; then
        "$PROJECT_DIR/scripts/update-mode.sh" A active --workers 1 --workflow simple --tasks-total 0 --tasks-done 0
    else
        "$PROJECT_DIR/scripts/update-mode.sh" B active --workers "$WORKER_COUNT" --workflow default --tasks-total 0 --tasks-done 0
    fi
fi
