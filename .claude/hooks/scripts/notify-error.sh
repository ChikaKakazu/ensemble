#!/bin/bash
# notify-error.sh
# PostToolUseFailure hook: エラー発生時の通知

# ターミナルベルを鳴らす（複数回）
echo -e '\a'
sleep 0.2
echo -e '\a'

# エラーメッセージ表示
echo "❌ エラーが発生しました"

# 環境変数からツール名を取得（存在する場合）
if [ -n "$CLAUDE_TOOL_NAME" ]; then
    echo "Tool: $CLAUDE_TOOL_NAME"
fi
