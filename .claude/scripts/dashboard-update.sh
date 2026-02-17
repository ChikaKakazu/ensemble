#!/bin/bash
# scripts/dashboard-update.sh
# ダッシュボードを更新する

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
DASHBOARD="$PROJECT_DIR/status/dashboard.md"

# コマンド
CMD="${1:-}"
shift || true

case "$CMD" in
    task)
        # タスク名を設定: dashboard-update.sh task "タスク名"
        TASK_NAME="${1:-なし}"
        sed -i "s/## 現在のタスク.*/## 現在のタスク\n$TASK_NAME/" "$DASHBOARD"
        ;;

    status)
        # エージェント状態を更新: dashboard-update.sh status "pane-0" "busy" "conductor" "計画中"
        PANE="${1:-}"
        STATE="${2:-idle}"
        AGENT="${3:--}"
        PROGRESS="${4:--}"

        # 状態行を生成
        STATUS_LINE="| $PANE | $STATE | $AGENT | $PROGRESS |"

        # 既存の状態テーブルを更新（簡易版：最後の行を置換）
        # TODO: 複数ペイン対応
        ;;

    complete)
        # タスク完了を記録: dashboard-update.sh complete "task-001" "success"
        TASK_ID="${1:-}"
        RESULT="${2:-success}"
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

        # 完了タスクに追加
        if grep -q "## 最近の完了タスク" "$DASHBOARD"; then
            sed -i "/## 最近の完了タスク/a - $TASK_ID: $RESULT ($TIMESTAMP)" "$DASHBOARD"
        fi
        ;;

    log)
        # ログを追加: dashboard-update.sh log "メッセージ"
        MESSAGE="${1:-}"
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

        if grep -q "## 改善ログ" "$DASHBOARD"; then
            sed -i "/## 改善ログ/a - [$TIMESTAMP] $MESSAGE" "$DASHBOARD"
        fi
        ;;

    timestamp)
        # 最終更新時刻を更新
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        sed -i "s/*Last updated:.*/*Last updated: $TIMESTAMP*/" "$DASHBOARD"
        ;;

    *)
        echo "Usage: dashboard-update.sh <command> [args]"
        echo ""
        echo "Commands:"
        echo "  task <name>           - Set current task name"
        echo "  status <pane> <state> <agent> <progress> - Update agent status"
        echo "  complete <task_id> <result> - Record task completion"
        echo "  log <message>         - Add log entry"
        echo "  timestamp             - Update last modified time"
        exit 1
        ;;
esac

# 常に最終更新時刻を更新
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
sed -i "s/*Last updated:.*/*Last updated: $TIMESTAMP*/" "$DASHBOARD"
