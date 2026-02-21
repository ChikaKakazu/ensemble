#!/bin/bash
# notify-worktree.sh
# WorktreeCreate/WorktreeRemove hook: worktree操作のログ記録

EVENT_TYPE="${CLAUDE_HOOK_EVENT_NAME:-unknown}"
TIMESTAMP=$(date -Iseconds)

# NDJSONログに記録
LOG_DIR=".ensemble/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/session-$(date +%Y%m%d).ndjson"

if [ "$EVENT_TYPE" = "WorktreeCreate" ]; then
    echo "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"worktree_create\",\"message\":\"Worktree created via Claude Code isolation\"}" >> "$LOG_FILE"
    echo "📂 Worktree created (isolation: worktree)"
elif [ "$EVENT_TYPE" = "WorktreeRemove" ]; then
    echo "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"worktree_remove\",\"message\":\"Worktree removed (cleanup)\"}" >> "$LOG_FILE"
    echo "🗑️ Worktree removed (cleanup)"
fi
