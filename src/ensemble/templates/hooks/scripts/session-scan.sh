#!/bin/bash
# session-scan.sh
# SessionStart hook: scan codebase for task candidates on session start.
# Hook output goes into Claude's context, so keep it concise.

# Check if ensemble CLI is available
if ! command -v uv &>/dev/null; then
    echo "[scan] uv not found, skipping scan"
    exit 0
fi

# Run scan (exclude test files, limit output)
SCAN_OUTPUT=$(uv run ensemble scan --exclude-tests --format json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "[scan] scan failed or not available"
    exit 0
fi

# Extract task count
TOTAL=$(echo "$SCAN_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)

if [ "$TOTAL" = "0" ] || [ -z "$TOTAL" ]; then
    echo "[scan] No task candidates found"
    exit 0
fi

# Show summary only (prevent context pollution)
echo "[scan] Found $TOTAL task candidate(s). Run 'ensemble scan --exclude-tests' for details or 'ensemble investigate' to analyze."

# Show top 3 task titles
echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tasks = data.get('tasks', [])[:3]
for t in tasks:
    src = t.get('source','?')
    title = t.get('title','?')[:60]
    pri = t.get('priority','?')
    print(f'  [{pri}] ({src}) {title}')
if len(data.get('tasks',[])) > 3:
    print(f'  ... and {len(data[\"tasks\"]) - 3} more')
" 2>/dev/null
