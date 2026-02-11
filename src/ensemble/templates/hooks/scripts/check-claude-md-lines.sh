#!/bin/bash
# CLAUDE.md line limit check
# Checks that CLAUDE.md stays under 150 lines for better adherence.

MAX_LINES=150
CLAUDE_MD="CLAUDE.md"

# Check staged files only
if git diff --cached --name-only | grep -q "^${CLAUDE_MD}$"; then
    if [ -f "$CLAUDE_MD" ]; then
        lines=$(wc -l < "$CLAUDE_MD")

        if [ "$lines" -gt "$MAX_LINES" ]; then
            echo "ERROR: CLAUDE.md exceeds $MAX_LINES lines (current: $lines)"
            echo "   Consider splitting content into .claude/rules/"
            exit 1
        else
            echo "CLAUDE.md: $lines lines (limit: $MAX_LINES)"
        fi
    fi
fi

exit 0
