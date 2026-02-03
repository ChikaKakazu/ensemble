#!/bin/bash
# Ensemble Setup Script
# Creates the directory structure and initial files for Ensemble AI Orchestration

set -e

echo "🎵 Ensemble Setup"
echo "=================="

# Get the project root (parent of scripts/)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 1. Check required commands
echo "Checking required commands..."
for cmd in claude tmux git; do
    if ! command -v $cmd &> /dev/null; then
        echo "⚠️  Warning: $cmd is not installed. Some features may not work."
    fi
done

# 2. Create directory structure
echo "Creating directory structure..."

mkdir -p .claude/{agents,commands,skills}
mkdir -p scripts
mkdir -p workflows
mkdir -p status
mkdir -p notes
mkdir -p queue/{tasks,reports,ack}

# 3. Create CLAUDE.md (only if it doesn't exist)
if [ ! -f CLAUDE.md ]; then
    echo "Creating CLAUDE.md..."
    cat > CLAUDE.md << 'CLAUDEEOF'
# プロジェクト: Ensemble AI Orchestration

## 概要
このプロジェクトはEnsemble AIオーケストレーションシステムを使用しています。

## 基本ルール
- /go コマンドでタスクを開始する
- /go-light で軽量ワークフロー（コスト最小）
- 実行パターンはConductorが自動判定する
- 自己改善フェーズを必ず実行する

## ⚠️ コンパクション復帰プロトコル（全エージェント必須）

コンパクション後は、作業を再開する前に**必ず**以下を実行せよ:

1. **自分のペイン名を確認する**:
   ```bash
   tmux display-message -p '#W'
   ```

2. **対応するエージェント定義を読み直す**:
   - conductor → `.claude/agents/conductor.md`
   - dispatch → `.claude/agents/dispatch.md`
   - reviewer → `.claude/agents/reviewer.md`
   - （その他、自分の役割に対応するファイル）

3. **禁止事項を確認してから作業開始**

4. **現在のタスクをダッシュボードで確認**:
   ```bash
   cat status/dashboard.md
   ```

summaryの「次のステップ」を見てすぐ作業してはならぬ。
**まず自分が誰かを確認せよ。**

## 通信プロトコル
- エージェント間の指示・報告はファイルベースキュー（queue/）経由
- send-keysは「新タスクあり」の通知のみに使用
- ACKファイルで受領確認を行う

## 実行パターン
- パターンA: 単純タスク → subagentで直接実行
- パターンB: 中規模タスク → tmux多ペインで並列実行
- パターンC: 大規模タスク → git worktreeで分離 + 各worktree内並列

## 学習済みルール（自動追記）
<!-- learner agentが自動追記するセクション -->

CLAUDEEOF
else
    echo "CLAUDE.md already exists, skipping..."
fi

# 4. Create dashboard.md
echo "Creating status/dashboard.md..."
cat > status/dashboard.md << 'EOF'
# 🎵 Ensemble Dashboard

## 現在のタスク
なし

## 実行状態
| ペイン/Worktree | 状態 | エージェント | 進捗 |
|---|---|---|---|
| - | idle | - | - |

## 最近の完了タスク
なし

## Skills候補
なし

## 改善ログ
なし

---
*Last updated: -*
EOF

# 5. Create .gitignore additions
if [ -f .gitignore ]; then
    if ! grep -q "queue/tasks/" .gitignore 2>/dev/null; then
        echo "" >> .gitignore
        echo "# Ensemble queue files (transient)" >> .gitignore
        echo "queue/tasks/*.yaml" >> .gitignore
        echo "queue/reports/*.yaml" >> .gitignore
        echo "queue/ack/*.ack" >> .gitignore
    fi
else
    cat > .gitignore << 'EOF'
# Ensemble queue files (transient)
queue/tasks/*.yaml
queue/reports/*.yaml
queue/ack/*.ack

# Python
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# Virtual environments
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
EOF
fi

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "使い方:"
echo "  claude  # Claude Codeを起動"
echo "  /go タスク内容  # Ensembleでタスクを実行"
echo "  /go-light タスク内容  # 軽量ワークフロー"
echo ""
echo "次のステップ:"
echo "  1. .claude/agents/conductor.md を確認"
echo "  2. MAX_THINKING_TOKENS=0 claude --model opus で起動"
