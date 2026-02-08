#!/bin/bash
# CLAUDE.md 150行制限チェック（hookify用）
# ステージングされたCLAUDE.mdの変更時のみチェック

MAX_LINES=150
CLAUDE_MD="CLAUDE.md"

# ステージングされたファイルをチェック
if git diff --cached --name-only | grep -q "^${CLAUDE_MD}$"; then
    # CLAUDE.mdの行数を取得
    if [ -f "$CLAUDE_MD" ]; then
        lines=$(wc -l < "$CLAUDE_MD")

        if [ "$lines" -gt "$MAX_LINES" ]; then
            echo "❌ ERROR: CLAUDE.md exceeds $MAX_LINES lines (current: $lines)"
            echo "   CLAUDE.md should be kept concise for better adherence."
            echo "   Consider splitting additional content into .claude/rules/"
            echo ""
            echo "   Suggested actions:"
            echo "   1. Move detailed workflows to .claude/rules/workflow.md"
            echo "   2. Move deployment steps to .claude/rules/deploy.md"
            echo "   3. Move communication protocols to .claude/rules/communication.md"
            exit 1
        else
            echo "✅ CLAUDE.md: $lines lines (limit: $MAX_LINES)"
        fi
    fi
fi

exit 0
