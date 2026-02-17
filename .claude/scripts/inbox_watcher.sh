#!/bin/bash
# src/ensemble/templates/scripts/inbox_watcher.sh
# Ensembleのqueue/ディレクトリを監視し、ファイル変更をイベント駆動で検知する
#
# inotifywaitでカーネルレベルのファイル変更を検知（CPU 0%）
# ポーリング不要、検知遅延0秒
#
# 参照: Shogun inbox_watcher.sh (https://github.com/yohey-w/multi-agent-shogun)
#
# WSL2対応: inotifywait不発時のタイムアウトフォールバック（5秒間隔）

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
PANES_FILE="$PROJECT_DIR/.ensemble/panes.env"
PID_FILE="$PROJECT_DIR/.ensemble/inbox_watcher.pid"
QUEUE_DIR="$PROJECT_DIR/queue"

# PIDファイルに自身のPIDを記録
echo $$ > "$PID_FILE"

# クリーンシャットダウン用のシグナルハンドラ
cleanup() {
    echo "inbox_watcher: Shutting down..."
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup SIGTERM SIGINT

# panes.envから環境変数を読み込む
if [ ! -f "$PANES_FILE" ]; then
    echo "Error: $PANES_FILE not found. Run launch.sh first."
    exit 1
fi

source "$PANES_FILE"

# inotifywaitが利用可能か確認
if ! command -v inotifywait &> /dev/null; then
    echo "Warning: inotifywait not found. Falling back to polling mode (5-second interval)."
    echo "Install inotify-tools for better performance: sudo apt-get install inotify-tools"

    # フォールバック: 5秒間隔のポーリング
    LAST_CHECK=$(date +%s)
    while true; do
        sleep 5
        NOW=$(date +%s)

        # 最終チェック以降に変更されたファイルを検出
        find "$QUEUE_DIR" -type f -newermt "@$LAST_CHECK" 2>/dev/null | while read -r file; do
            # ファイル種別に応じて通知
            case "$file" in
                */completion-summary.yaml)
                    tmux send-keys -t "$CONDUCTOR_PANE" 'completion-summary.yaml を確認してください'
                    sleep 1
                    tmux send-keys -t "$CONDUCTOR_PANE" Enter
                    ;;
                */escalation-*.yaml)
                    tmux send-keys -t "$CONDUCTOR_PANE" 'エスカレーション報告を確認してください（queue/reports/）'
                    sleep 1
                    tmux send-keys -t "$CONDUCTOR_PANE" Enter
                    ;;
                */task-*-completed.yaml)
                    tmux send-keys -t "$DISPATCH_PANE" 'queue/reports/ に新しい完了報告があります'
                    sleep 1
                    tmux send-keys -t "$DISPATCH_PANE" Enter
                    ;;
                */dispatch-instruction.yaml)
                    tmux send-keys -t "$DISPATCH_PANE" 'queue/conductor/dispatch-instruction.yaml を確認してください'
                    sleep 1
                    tmux send-keys -t "$DISPATCH_PANE" Enter
                    ;;
            esac
        done

        LAST_CHECK=$NOW
    done
fi

# inotifywait本体の処理
echo "inbox_watcher: Starting (queue: $QUEUE_DIR)"

# inotifywaitを再帰的に監視（-r）、-e create,modify,move イベント
# -t 5: 5秒タイムアウト（WSL2のinotify不発対策）
# --format '%w%f': フルパスを出力
inotifywait -m -r -e create,modify,move -t 5 --format '%w%f' "$QUEUE_DIR" 2>/dev/null | while read -r file; do
    # タイムアウト時はcontinue
    if [ -z "$file" ]; then
        continue
    fi

    # 一時ファイル（.tmp, .lock）は無視
    case "$file" in
        *.tmp|*.lock)
            continue
            ;;
    esac

    # ファイル種別に応じた通知先の振り分け
    case "$file" in
        */completion-summary.yaml)
            # Conductorに通知
            tmux send-keys -t "$CONDUCTOR_PANE" 'completion-summary.yaml を確認してください'
            sleep 1
            tmux send-keys -t "$CONDUCTOR_PANE" Enter
            ;;
        */escalation-*.yaml)
            # Conductorに通知
            tmux send-keys -t "$CONDUCTOR_PANE" 'エスカレーション報告を確認してください（queue/reports/）'
            sleep 1
            tmux send-keys -t "$CONDUCTOR_PANE" Enter
            ;;
        */task-*-completed.yaml)
            # Dispatchに通知
            tmux send-keys -t "$DISPATCH_PANE" 'queue/reports/ に新しい完了報告があります'
            sleep 1
            tmux send-keys -t "$DISPATCH_PANE" Enter
            ;;
        */ack/*.ack)
            # Dispatchに通知（ACK受信）
            tmux send-keys -t "$DISPATCH_PANE" 'queue/ack/ に新しいACKがあります'
            sleep 1
            tmux send-keys -t "$DISPATCH_PANE" Enter
            ;;
        */tasks/worker-*.yaml)
            # Workerに通知（タスク割り当て）
            # ファイル名からWorker番号を抽出
            WORKER_NUM=$(echo "$file" | sed -n 's/.*worker-\([0-9]\+\)-task\.yaml/\1/p')
            if [ -n "$WORKER_NUM" ]; then
                WORKER_PANE_VAR="WORKER_${WORKER_NUM}_PANE"
                WORKER_PANE="${!WORKER_PANE_VAR:-}"

                if [ -n "$WORKER_PANE" ]; then
                    tmux send-keys -t "$WORKER_PANE" "queue/tasks/worker-${WORKER_NUM}-task.yaml を確認して実行してください"
                    sleep 1
                    tmux send-keys -t "$WORKER_PANE" Enter
                fi
            fi
            ;;
        */conductor/dispatch-instruction.yaml)
            # Dispatchに通知
            tmux send-keys -t "$DISPATCH_PANE" 'queue/conductor/dispatch-instruction.yaml を確認してください'
            sleep 1
            tmux send-keys -t "$DISPATCH_PANE" Enter
            ;;
    esac
done

# inotifywaitが終了した場合（通常は発生しない）
echo "inbox_watcher: inotifywait terminated unexpectedly"
cleanup
