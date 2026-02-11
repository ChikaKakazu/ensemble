#!/bin/bash
# notify-stop.sh
# Stop hook: notify when agent work is complete.

# Ring terminal bell (most portable method)
echo -e '\a'

# Check if completion-summary.yaml exists
if [ -f "queue/reports/completion-summary.yaml" ]; then
    echo "All tasks complete"
else
    echo "Agent work complete"
fi
