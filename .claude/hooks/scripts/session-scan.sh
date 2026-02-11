#!/bin/bash
# session-scan.sh
# SessionStart時にensemble scanを実行し、タスク候補をサマリー表示する。
# フックの出力はClaudeのコンテキストに入るため、簡潔にする。

# ensemble CLIが利用可能か確認
if ! command -v uv &>/dev/null; then
    echo "[scan] uv not found, skipping scan"
    exit 0
fi

# scan実行（テストファイル除外、出力を制限）
SCAN_OUTPUT=$(uv run ensemble scan --exclude-tests --format json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "[scan] scan failed or not available"
    exit 0
fi

# タスク数を抽出
TOTAL=$(echo "$SCAN_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)

if [ "$TOTAL" = "0" ] || [ -z "$TOTAL" ]; then
    echo "[scan] No task candidates found"
    exit 0
fi

# サマリーのみ表示（コンテキスト汚染防止）
echo "[scan] Found $TOTAL task candidate(s). Run 'ensemble scan --exclude-tests' for details or 'ensemble investigate' to analyze."

# 上位3件のタイトルを表示
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
