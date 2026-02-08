#!/bin/bash
# statusline.sh
# Status Line: 現在の状態を1行で表示

# 現在のgitブランチ
branch=$(git branch --show-current 2>/dev/null || echo "no-branch")

# tmuxセッション状態
if tmux has-session -t ensemble-conductor 2>/dev/null; then
    conductor="✓"
else
    conductor="✗"
fi

if tmux has-session -t ensemble-workers 2>/dev/null; then
    workers="✓"
else
    workers="✗"
fi

# Worker数（.ensemble/panes.env から取得）
if [ -f ".ensemble/panes.env" ]; then
    worker_count=$(grep "^WORKER_COUNT=" .ensemble/panes.env 2>/dev/null | cut -d= -f2)
    if [ -z "$worker_count" ]; then
        worker_count="0"
    fi
else
    worker_count="0"
fi

# 出力（1行）
echo "⎇ $branch | C:$conductor W:$workers | Workers: $worker_count"
