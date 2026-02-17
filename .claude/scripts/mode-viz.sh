#!/bin/bash
# scripts/mode-viz.sh
# mode.mdをアニメーション表示する（1秒間隔でフレームを切り替え）
#
# Usage: bash scripts/mode-viz.sh
#   - .ensemble/status/mode-params.env を参照してパラメータを取得
#   - フレーム0と1を交互に切り替えてアニメーション効果を実現
#   - Ctrl+C で終了

set -euo pipefail

PARAMS_FILE=".ensemble/status/mode-params.env"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# tput が使える場合はちらつき防止
if command -v tput &>/dev/null; then
    CLEAR_CMD="tput clear"
else
    CLEAR_CMD="clear"
fi

# シグナルハンドラ（Ctrl+C で終了）
trap 'echo ""; echo "mode-viz: stopped."; exit 0' INT TERM

FRAME=0

while true; do
    # パラメータを読み込む
    MODE="idle"
    STATUS="active"
    WORKERS=1
    WORKFLOW=""
    TASKS_TOTAL=0
    TASKS_DONE=0
    WORKER_STATES=""

    if [ -f "$PARAMS_FILE" ]; then
        # shellcheck disable=SC1090
        source "$PARAMS_FILE"
    fi

    # mode-params.envに保存されたFRAMEは使わず、ループ内のFRAMEを使う
    # update-mode.sh を実行（--frame でフレームを指定）
    ARGS=(
        "$MODE"
        "${STATUS:-active}"
        "--frame" "$FRAME"
    )
    [ -n "${WORKERS:-}" ]      && ARGS+=("--workers" "$WORKERS")
    [ -n "${WORKFLOW:-}" ]     && ARGS+=("--workflow" "$WORKFLOW")
    [ -n "${TASKS_TOTAL:-}" ]  && ARGS+=("--tasks-total" "$TASKS_TOTAL")
    [ -n "${TASKS_DONE:-}" ]   && ARGS+=("--tasks-done" "$TASKS_DONE")
    [ -n "${WORKER_STATES:-}" ] && ARGS+=("--worker-states" "$WORKER_STATES")

    bash "$SCRIPTS_DIR/update-mode.sh" "${ARGS[@]}" 2>/dev/null || true

    # 画面クリアして表示
    $CLEAR_CMD
    if [ -f ".ensemble/status/mode.md" ]; then
        cat ".ensemble/status/mode.md"
    else
        echo "(mode.md not found)"
    fi

    # フレームを切り替え（0 → 1 → 0 → ...）
    if [ "$FRAME" -eq 0 ]; then
        FRAME=1
    else
        FRAME=0
    fi

    sleep 1
done
