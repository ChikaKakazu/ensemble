#!/bin/bash
# CLAUDE.md 150行制限チェック
# pre-commit hook として使用

MAX_LINES=150
CLAUDE_MD="CLAUDE.md"

if git diff --cached --name-only | grep -q "^${CLAUDE_MD}$"; then
    lines=$(wc -l < "$CLAUDE_MD")
    if [ "$lines" -gt "$MAX_LINES" ]; then
        echo "❌ CLAUDE.md exceeds $MAX_LINES lines (current: $lines)"
        echo "   Consider splitting into .claude/rules/"
        exit 1
    else
        echo "✅ CLAUDE.md: $lines lines (limit: $MAX_LINES)"
    fi
fi

exit 0
