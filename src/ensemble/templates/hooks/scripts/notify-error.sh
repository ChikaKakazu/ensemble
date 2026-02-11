#!/bin/bash
# notify-error.sh
# PostToolUseFailure hook: notify on tool errors.

# Ring terminal bell
echo -e '\a'
sleep 0.2
echo -e '\a'

echo "Error occurred"

# Show tool name if available
if [ -n "$CLAUDE_TOOL_NAME" ]; then
    echo "Tool: $CLAUDE_TOOL_NAME"
fi
