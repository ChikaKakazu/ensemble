# AIオーケストレーションツール「Ensemble」実装計画書 v2

> **"One task. Many minds. One result."**

## 1. コンセプト

### 1.1 名前候補: **Ensemble（アンサンブル）**

オーケストラの「合奏」から。taktが「指揮棒」なら、Ensembleは「演奏する側」の視点。
AIたちが自律的に協調して一つの成果物を作り上げるイメージ。

### 1.2 設計思想

3つのアプローチを以下のように統合する。

| 要素 | 採用元 | Ensembleでの実現方法 |
|---|---|---|
| **自律的AI協調** | shogun | 1つの指示で、AI同士がやりとりして成果物を作る |
| **強制ワークフロー** | takt | デフォルトワークフローで品質ゲートを保証しつつ、AI自身がワークフローを提案・改善できる |
| **Claude Code素の力** | Boris氏 | skills, subagents, CLAUDE.md, hooks, plan mode をフル活用 |
| **並列実行** | shogun + Boris氏 | tmux多ペイン × git worktree のハイブリッド |
| **自己改善** | shogun + Boris氏 | skills/CLAUDE.md/agentsの自動生成・更新 |
| **コンパクション耐性** | shogun v1.1 | 役割忘却を仕組みで防止する |
| **通信の信頼性** | shogun v1.3 | ACK機構 + フレンドリーファイア防止 |
| **SPOF排除** | shogun v1.3 | 頭脳と手足の役割分離 |
| **並列レビュー** | takt v0.3 | parallel step + all/any集約ルール |
| **コスト意識** | takt GH Actions | タスク重さ別のワークフロー選択 |

### 1.3 先行ツールの失敗から学んだ教訓

4つの追加記事から得られた、**設計段階で織り込むべき教訓**:

| # | 教訓 | 出典 | Ensembleでの対策 |
|---|---|---|---|
| 1 | コンパクション後にAIが役割を忘れる | shogun v1.1 | CLAUDE.mdに復帰手順を必須記載 + hook自動化 |
| 2 | 委譲役がExtended Thinkingで考えすぎて遅い | shogun v1.1 | Conductorは`MAX_THINKING_TOKENS=0`で起動 |
| 3 | send-keysの同時到達でCLIがcrash（フレンドリーファイア） | shogun v1.3 | ファイルベースキュー + ロック機構で順次処理 |
| 4 | 中間管理職がSPOF（死んだら全軍停止） | shogun v1.3 | Conductorを「頭脳」と「伝達」に分離 |
| 5 | send-keysがfire-and-forget（届いたか不明） | shogun v1.3 | ACK機構（完了マーカーファイル）導入 |
| 6 | 直列レビューで待ち時間が長い | takt v0.3 | parallelステップで独立レビューを並列化 |
| 7 | API課金がタスクごとに$1〜$5かかる | takt GH Actions | コスト意識のワークフロー選択（simple/default/heavy） |

### 1.4 基本フロー

```
人間: 「ユーザー認証機能を実装して」
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  Conductor（指揮者 = メインClaude Code）              │
│  ※ Opus, Thinking無効 = 即断即決、委譲に特化         │
│                                                     │
│  1. planモードで計画策定                              │
│  2. タスク分解 → worktree必要？ペイン分割必要？判断    │
│  3. 必要なskills/agentsがあるか確認、なければ生成提案   │
│  4. コスト見積もり → ワークフロー選択                  │
│  5. 実行モード選択:                                   │
│     a. 単純タスク → サブエージェントで直接実行          │
│     b. 中規模 → tmux多ペインで並列実行                 │
│     c. 大規模 → git worktreeで分離 + 各worktree内並列  │
│  6. Dispatch（伝達役）が各エージェントにタスク配信      │
│  7. 実行 → 並列レビュー → 統合 → 最終レビュー         │
│  8. 完了後: CLAUDE.md更新、skills候補提案              │
└─────────────────────────────────────────────────────┘
  │
  ▼
人間: 成果物を確認（ダッシュボードで進捗監視可能）
```

---

## 2. アーキテクチャ

### 2.1 全体構成

```
ensemble/
├── CLAUDE.md                    # プロジェクトルートの指示書
├── .claude/
│   ├── agents/                  # カスタムサブエージェント定義
│   │   ├── conductor.md         # 指揮者（頭脳：計画・判断に特化）
│   │   ├── dispatch.md          # 伝達役（手足：配信・収集・ダッシュボード）
│   │   ├── planner.md           # 計画立案
│   │   ├── reviewer.md          # コードレビュー
│   │   ├── security-reviewer.md # セキュリティレビュー
│   │   ├── integrator.md        # worktree統合
│   │   └── learner.md           # 自己改善（skills/CLAUDE.md更新）
│   ├── skills/                  # 自動生成されるスキル群
│   │   ├── worktree-manager/
│   │   │   └── SKILL.md
│   │   ├── pane-orchestrator/
│   │   │   └── SKILL.md
│   │   ├── self-improve/
│   │   │   └── SKILL.md
│   │   └── dashboard/
│   │       └── SKILL.md
│   ├── commands/                # スラッシュコマンド
│   │   ├── go.md                # /go — ワンコマンド実行
│   │   ├── go-light.md          # /go-light — 軽量ワークフロー（コスト最小）
│   │   ├── plan.md              # /plan — 計画のみ
│   │   ├── review.md            # /review — 全worktreeの統合レビュー
│   │   ├── improve.md           # /improve — 自己改善実行
│   │   └── status.md            # /status — ダッシュボード更新
│   └── settings.json            # Claude Code設定
│
├── scripts/                     # シェルスクリプト群
│   ├── setup.sh                 # 初回セットアップ
│   ├── launch.sh                # 日次起動
│   ├── worktree-create.sh       # worktree作成+Claude起動
│   ├── worktree-merge.sh        # worktree統合
│   └── pane-setup.sh            # tmuxペイン構成
│
├── workflows/                   # YAMLワークフロー定義
│   ├── default.yaml             # 標準: plan→implement→parallel review→improve
│   ├── simple.yaml              # 軽量: plan→implement→review（ループなし）
│   ├── heavy.yaml               # 重厚: plan→implement→5段レビュー→improve
│   ├── worktree.yaml            # worktree分離フロー
│   └── custom/                  # AI or ユーザーが追加するカスタムWF
│
├── queue/                       # エージェント間通信（ファイルベースキュー）
│   ├── tasks/                   # タスクYAML（Conductor → 各エージェント）
│   ├── reports/                 # 完了報告（各エージェント → Dispatch）
│   └── ack/                     # ACKマーカー（配信確認）
│
├── status/
│   └── dashboard.md             # リアルタイムダッシュボード
│
├── notes/                       # タスクごとの学習ノート
│   └── {task-id}/
│       ├── plan.md
│       ├── decisions.md
│       └── lessons.md
│
├── .github/                     # GitHub Actions統合（オプション）
│   └── workflows/
│       └── ensemble-action.yml
│
├── package.json                 # npm公開用（将来）
└── README.md
```

### 2.2 エージェント階層

shogunの固定3層（将軍→家老→足軽）ではなく、**タスクに応じて動的に構成が変わる**設計にする。

さらにshogun v1.3の教訓を反映し、**Conductorを頭脳（Conductor）と手足（Dispatch）に分離**する。

```
┌──────────────────────────────────────────────────────────┐
│  Conductor（頭脳）                                        │
│  Opus, Thinking無効, 考えない、即判断・即委譲              │
│  担当: 計画策定、タスク分解、パターン選択、最終判断        │
│                                                          │
│  Dispatch（手足）  ← shogun v1.3「奉行」の発想            │
│  Sonnet, 軽量モデル                                       │
│  担当: YAML配信、send-keys、ACK確認、報告収集、           │
│        ダッシュボード更新                                  │
│  ※ Dispatchが死んでもConductorの計画は生きている           │
│  ※ Conductorのコンテキスト消費を60-70%削減                 │
└──────────────────────────────────────────────────────────┘

パターンA: 単純タスク（ファイル1個の修正など）
  Conductor(計画) → subagent(coder) → subagent(reviewer) → 完了

パターンB: 中規模タスク（複数ファイル、テスト含む）
  Conductor(計画) → Dispatch(配信) → tmux 3ペイン並列:
    ├── pane0: coder (実装)
    ├── pane1: coder (テスト)
    └── pane2: coder (ドキュメント)
  → Dispatch(報告収集) → parallel review → 完了

パターンC: 大規模タスク（複数機能、独立開発可能）
  Conductor(計画) → Dispatch(配信) → git worktree × N:
    ├── worktree-auth/
    │   └── tmux 2ペイン: [coder] [tester]
    ├── worktree-api/
    │   └── tmux 2ペイン: [coder] [tester]
    └── worktree-ui/
        └── tmux 2ペイン: [coder] [tester]
  → Dispatch(報告収集) → integrator (統合) → 相互レビュー → 完了
```

---

## 3. コア機能の詳細設計

### 3.1 Conductor（指揮者 = 頭脳）— メインエージェント

**ファイル:** `.claude/agents/conductor.md`

shogun v1.1の教訓：**「考えるな、委譲しろ（Don't think. Delegate.）」**
ConductorはExtended Thinkingを無効化し、即断即決に特化する。

```markdown
<!-- .claude/agents/conductor.md -->
---
name: conductor
description: |
  Ensembleの指揮者（頭脳）。ユーザーのタスクを受け取り、
  計画・分解・パターン選択・最終判断を行う。
  実行の伝達・監視はDispatchに委譲する。考えすぎない。即判断。
tools: Read, Write, Edit, Bash, Glob, Grep, Skill
model: opus
---

あなたはEnsembleの指揮者（Conductor）です。

## 最重要ルール: 考えるな、委譲しろ
- あなたの仕事は「判断」と「委譲」。自分でコードを書いたりファイルを直接操作するな。
- 計画を立てたら即座にDispatchまたはサブエージェントに委譲せよ。
- 30秒で済む判断に5分かけるな。

## 行動原則
1. まずplanモードで全体計画を立てる
2. タスクを分解し、最適な実行パターンを選択する
3. コスト見積もりを行い、適切なワークフローを選択する
4. 必要なskillsやagentsが不足していれば生成を提案する
5. Dispatchにタスク配信を指示する
6. 完了報告を受けたら最終判断のみ行う
7. 完了後は必ず自己改善フェーズをlearnerに委譲する

## 実行パターン判定基準
- 変更ファイル数 ≤ 3、独立性が高くない → パターンA（subagent直接）
- 変更ファイル数 4〜10、並列可能な作業あり → パターンB（tmux並列）
- 機能が独立、変更ファイル数 > 10 or 複数ブランチ必要 → パターンC（worktree分離）

## コスト意識のワークフロー選択
- README更新、typo修正 → simple.yaml（レビュー1段、ループなし）
- 通常の機能開発 → default.yaml（並列レビュー + 修正ループ）
- 大規模リファクタ、セキュリティ重要 → heavy.yaml（5段レビュー）

## worktree統合プロトコル
パターンCの場合、全worktreeの作業完了後:
1. integrator agentが各worktreeの変更をメインブランチへマージ
2. コンフリクトがあればConductorに報告
3. マージ後、各worktreeのCoderが「自分以外の変更」をレビュー（相互レビュー）
4. 全員承認で完了

## 重要な設計判断のプロトコル
アーキテクチャやテンプレート構造など、重要な設計判断を下す際は:
- 単一エージェントの意見で即決しない
- 複数の専門家ペルソナ（3〜5人）を召喚し、熟議させる
- 多数決ではなく、各専門領域からの総意を得る
```

**起動コマンド:**
```bash
MAX_THINKING_TOKENS=0 claude --model opus --agent conductor --dangerously-skip-permissions
```

### 3.2 Dispatch（伝達役 = 手足）— 新設エージェント

**ファイル:** `.claude/agents/dispatch.md`

shogun v1.3で判明した**家老過負荷問題**の解決策。
Conductorから「頭を使わない仕事」を全て引き受ける。

```markdown
---
name: dispatch
description: |
  Ensembleの伝達役。Conductorの計画を各エージェントに配信し、
  完了報告を収集し、ダッシュボードを更新する。
  自分で考えて判断しない。指示された通りに伝達・記録する。
tools: Read, Write, Edit, Bash, Glob
model: sonnet
---

あなたはEnsembleの伝達役（Dispatch）です。

## 最重要ルール
- 自分で計画を立てない。Conductorの指示を忠実に伝達する。
- 自分でコードを書かない。
- 判断が必要な事態はConductorにエスカレーションする。

## 担当業務
1. **タスク配信**: Conductorの計画をYAMLに書き出し、各ペイン/worktreeに配信
2. **ACK確認**: 配信後、受領確認を待つ。タイムアウト時はリトライ。
3. **報告収集**: 各エージェントの完了報告を queue/reports/ から収集
4. **ダッシュボード更新**: status/dashboard.md を常に最新に保つ
5. **Conductor報告**: 全タスク完了時にConductorに最終報告

## 配信プロトコル（フレンドリーファイア防止）
- 複数エージェントへの同時配信は行わない
- 1エージェントずつ、ACKを確認してから次に配信
- 配信間隔は最低3秒空ける（CLI crash防止）
- 配信はsend-keysではなくファイルベースキューを優先使用

## ACK機構
1. タスクYAMLを queue/tasks/{agent}-{task-id}.yaml に書き込む
2. send-keysで「新しいタスクがqueue/tasksにある。確認せよ」と通知
3. エージェントがタスクを読み、queue/ack/{agent}-{task-id}.ack を作成
4. Dispatchがackファイルの存在を確認（5秒間隔、最大3回リトライ）
5. ACKがなければConductorにエスカレーション
```

### 3.3 コンパクション復帰メカニズム

**shogun v1.1最大の教訓: 「AIもうっかり忘れる」**

コンパクション後にエージェントが自分の役割を忘れるのは**仕組みの問題**。
CLAUDE.mdに復帰手順を必須記載し、hookで自動化する。

**CLAUDE.mdに追記するセクション:**

```markdown
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
```

**hookによる自動復帰（.claude/settings.json に追加）:**

```jsonc
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "command": "echo '⚠️ コンパクション復帰チェック: 自分の役割を確認してから作業を開始してください'"
      }
    ]
  }
}
```

### 3.4 send-keys通信の信頼性確保

**shogun v1.3の教訓: 「フレンドリーファイアとfire-and-forget」**

shogunでは足軽8人が同時にsend-keysで家老に報告を送り、CLIがクラッシュした。
Ensembleではファイルベースキュー + ACKで根本解決する。

```
【shogunの問題】
足軽1 →send-keys→ 家老(処理中)
足軽2 →send-keys→ 家老(処理中) ← 割り込み！
足軽3 →send-keys→ 家老        ← CLI crash！

【Ensembleの解決策】
各エージェント → queue/reports/{agent}-{task-id}.yaml に書き込み
                 （ファイル書き込みは衝突しない）
Dispatch    → queue/reports/ を定期スキャン（3秒間隔）
             → 1件ずつ順次処理
             → dashboard.md 更新
```

**ファイルベースキューの設計:**

```yaml
# queue/tasks/pane0-task-001.yaml （Dispatch → エージェント）
task_id: task-001
agent: pane0
type: implement
instruction: "認証モジュールのログイン関数を実装せよ"
created_at: "2026-02-02T10:00:00Z"
status: pending  # pending → acked → in_progress → done

# queue/reports/pane0-task-001.yaml （エージェント → Dispatch）
task_id: task-001
agent: pane0
status: done  # done | failed | blocked
result: "login関数を実装完了。テスト3件追加。"
files_changed:
  - src/auth/login.ts
  - tests/auth/login.test.ts
created_at: "2026-02-02T10:15:00Z"

# queue/ack/pane0-task-001.ack （エージェント → Dispatch、受領確認）
# 空ファイル。存在すればACK。
```

**send-keysはファイルキュー通知のみに限定:**

```bash
# NG: 直接指示をsend-keysで送る（旧shogun方式）
tmux send-keys -t pane0 "ログイン関数を実装しろ" C-m

# OK: ファイルキューの存在を通知するだけ
tmux send-keys -t pane0 "queue/tasks/ に新しいタスクがあります。確認してください。" C-m
```

### 3.5 自己改善メカニズム

Boris氏の「CLAUDE.mdにミスを記録させる」+ shogunの「Skills自動生成」を統合する。

**ファイル:** `.claude/agents/learner.md`

```markdown
---
name: learner
description: |
  タスク完了後に呼び出される自己改善エージェント。
  ミスの記録、skills候補の検出、CLAUDE.md更新を担当。
tools: Read, Write, Edit, Glob, Grep
model: sonnet
---

あなたはEnsembleの学習エージェントです。

## タスク完了後に実行すること

### 1. ミスの記録とCLAUDE.md更新
- 実行中に発生したエラー、手戻り、人間からの修正指示を分析
- パターン化できるものはCLAUDE.mdにルールとして追記
- フォーマット: `## 学習済みルール（自動追記）` セクションに追加
- コンパクション復帰プロトコルが不十分なら改善案も追記

### 2. Skills候補の検出
以下の基準でskill化を検討:
- 今回のタスクで2回以上繰り返された手順
- 汎用的で他プロジェクトでも使えるパターン
- 既存skillsと重複しないこと

候補があれば `notes/{task-id}/skill-candidates.md` に記録し、
Conductorを通じてユーザーに提案する。

### 3. Agent候補の検出
- 既存agentでカバーできないドメイン知識が必要だった場合
- 新しいagent定義を `notes/{task-id}/agent-candidates.md` に記録

### 4. ワークフロー改善
- 選択されたワークフローが最適だったか振り返る
- コスト対効果は妥当だったか
- 改善案があれば `notes/{task-id}/workflow-feedback.md` に記録

### 5. 通信障害の記録
- フレンドリーファイアやACKタイムアウトが発生した場合、パターンを分析
- Dispatchの配信間隔やリトライ設定の改善案を記録
```

### 3.6 tmux並列実行（shogun方式の改良）

shogunのイベント駆動send-keysアプローチを踏襲しつつ、v1.3の教訓を反映し改善する。

- **動的ペイン数**: タスク数に応じて1〜8ペインを自動構成（固定8ではない）
- **ペインごとのエージェント指定**: 全員が同じ足軽ではなく、タスクに応じたagentを割り当て
- **完了検知の自動化**: ファイルベースACKで完了を検知
- **フレンドリーファイア防止**: send-keysは通知のみ、指示本体はファイル経由

**ファイル:** `scripts/pane-setup.sh`

```bash
#!/bin/bash
# 使い方: ./pane-setup.sh <session_name> <pane_count> [agent_type]
# 例: ./pane-setup.sh ensemble-work 4 coder

SESSION_NAME="${1:-ensemble-work}"
PANE_COUNT="${2:-4}"
AGENT_TYPE="${3:-}"
PROJECT_DIR=$(pwd)

# セッション作成（既存なら再利用）
tmux has-session -t "$SESSION_NAME" 2>/dev/null
if [ $? != 0 ]; then
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR"
fi

# ペイン分割
for ((i=1; i<PANE_COUNT; i++)); do
    if ((i % 2 == 1)); then
        tmux split-window -t "$SESSION_NAME" -h -c "$PROJECT_DIR"
    else
        tmux split-window -t "$SESSION_NAME" -v -c "$PROJECT_DIR"
    fi
done

# 均等配置
tmux select-layout -t "$SESSION_NAME" tiled

# 各ペインでClaude Codeを起動
# ※ Conductorのみ Thinking無効、他はデフォルト
for ((i=0; i<PANE_COUNT; i++)); do
    PANE_NAME="pane${i}"
    tmux select-pane -t "$SESSION_NAME:0.$i" -T "$PANE_NAME"

    if [ "$AGENT_TYPE" = "conductor" ]; then
        tmux send-keys -t "$SESSION_NAME:0.$i" \
            "MAX_THINKING_TOKENS=0 claude --model opus --dangerously-skip-permissions" C-m
    elif [ -n "$AGENT_TYPE" ]; then
        tmux send-keys -t "$SESSION_NAME:0.$i" \
            "claude --agent $AGENT_TYPE --dangerously-skip-permissions" C-m
    else
        tmux send-keys -t "$SESSION_NAME:0.$i" \
            "claude --dangerously-skip-permissions" C-m
    fi

    # フレンドリーファイア防止: 起動間隔を3秒空ける
    sleep 3
done

echo "✅ Session '$SESSION_NAME' ready with $PANE_COUNT panes"
```

### 3.7 git worktree管理（Boris氏方式 + shogun並列の統合）

**ファイル:** `.claude/skills/worktree-manager/SKILL.md`

```markdown
---
name: worktree-manager
description: |
  git worktreeの作成・管理・統合を行うスキル。
  worktreeごとにtmuxセッションを作成し、独立したClaude Codeを起動する。
  最終的に全worktreeを統合し、相互レビューを実施する。
allowed-tools: Bash, Read, Write, Edit
---

# Worktree Manager

## worktreeの作成

タスク分解結果に基づき、以下の手順でworktreeを作成する:

1. ブランチ名の決定: `ensemble/{task-id}/{feature-name}`
2. worktree作成:
   ```bash
   git worktree add ../ensemble-{feature-name} -b ensemble/{task-id}/{feature-name}
   ```
3. worktree内でtmuxセッション作成（pane-setup.sh利用）
4. 各ペインでClaude Codeを起動し、ファイルキュー経由でタスクを送信

## worktreeの統合

全worktreeの作業完了後:

1. メインブランチ（main or develop）を最新化
2. 各featureブランチを順次マージ:
   ```bash
   git checkout main
   git merge --no-ff ensemble/{task-id}/{feature-a}
   git merge --no-ff ensemble/{task-id}/{feature-b}
   ```
3. コンフリクトがあれば、関連するworktreeのClaudeに解決を依頼
4. マージ完了後、各worktreeを削除:
   ```bash
   git worktree remove ../ensemble-{feature-name}
   git branch -d ensemble/{task-id}/{feature-name}
   ```

## 相互レビュープロトコル

統合後、以下を各worktreeのClaudeに実行させる:
- 自分が担当した以外の変更差分を確認
- アーキテクチャ整合性、依存関係、インターフェースの整合性をチェック
- 問題があればConductorに報告
```

### 3.8 ワークフロー定義（takt v0.3 並列ステップ反映）

taktのYAML形式を参考にしつつ、以下の拡張を加える:
- **parallelステップ**: 独立したレビューを並列実行（takt v0.3）
- **all/any集約ルール**: サブステップの結果を投票的に集約
- **コスト意識のワークフロー選択**: simple/default/heavyの3段階

**ファイル:** `workflows/default.yaml`

```yaml
name: default
description: |
  標準ワークフロー。計画→実装→並列レビュー→改善の全サイクル。
  通常の機能開発向け。
max_iterations: 15
cost_level: medium  # low/medium/high — ワークフロー選択のヒント

steps:
  - name: plan
    description: タスク分析と実行計画の策定
    agent: conductor
    mode: plan
    thinking: false  # Conductor = thinking無効
    outputs:
      - plan.md
      - task-breakdown.md
    transitions:
      - condition: plan_approved
        next_step: execute
      - condition: needs_clarification
        next_step: PAUSE

  - name: execute
    description: |
      計画に基づき実行。タスク規模に応じて
      subagent/tmux並列/worktree分離を自動選択。
    agent: conductor
    mode: execute
    allow_parallel: true
    allow_worktree: true
    transitions:
      - condition: execution_complete
        next_step: parallel_review
      - condition: blocked
        next_step: plan

  # takt v0.3の並列レビュー構文を採用
  - name: parallel_review
    description: アーキテクチャとセキュリティを並列でレビュー
    parallel:
      - name: arch-review
        agent: reviewer
        rules:
          - condition: approved
          - condition: needs_fix
        instruction_template: |
          アーキテクチャと設計品質に集中してレビューしてください。
          コード構造、依存関係の方向、命名規則を確認。

      - name: security-review
        agent: security-reviewer
        rules:
          - condition: approved
          - condition: needs_fix
        instruction_template: |
          セキュリティに集中してレビューしてください。
          インジェクション、認証、データ保護を確認。
    rules:
      - condition: all("approved")
        next_step: improve
      - condition: any("needs_fix")
        next_step: execute

  - name: improve
    description: 自己改善フェーズ
    agent: learner
    transitions:
      - condition: done
        next_step: COMPLETE
```

**ファイル:** `workflows/simple.yaml`（コスト最小）

```yaml
name: simple
description: |
  軽量ワークフロー。README更新、typo修正など軽微な変更向け。
  レビューは1回、修正ループなし。
max_iterations: 5
cost_level: low

steps:
  - name: plan
    agent: conductor
    mode: plan
    thinking: false
    transitions:
      - condition: plan_approved
        next_step: execute

  - name: execute
    agent: conductor
    mode: execute
    transitions:
      - condition: execution_complete
        next_step: review

  - name: review
    agent: reviewer
    transitions:
      - condition: approved
        next_step: COMPLETE
      - condition: needs_fix
        next_step: execute  # 1回だけ修正
```

**ファイル:** `workflows/worktree.yaml`

```yaml
name: worktree
description: |
  git worktreeを活用した大規模タスク向けワークフロー。
  機能ごとに独立したworktreeで並列開発し、最後に統合+相互レビュー。
max_iterations: 20
cost_level: high

steps:
  - name: plan
    agent: conductor
    mode: plan
    thinking: false
    outputs:
      - plan.md
      - worktree-spec.md
    transitions:
      - condition: plan_approved
        next_step: create_worktrees

  - name: create_worktrees
    description: worktreeの作成とClaude Codeの起動
    agent: conductor
    skill: worktree-manager
    transitions:
      - condition: worktrees_ready
        next_step: parallel_execute

  - name: parallel_execute
    description: 各worktreeで並列実行
    agent: dispatch
    mode: execute
    allow_parallel: true
    transitions:
      - condition: all_worktrees_complete
        next_step: integrate

  - name: integrate
    description: 全worktreeの変更をメインブランチに統合
    agent: integrator
    skill: worktree-manager
    transitions:
      - condition: merge_success
        next_step: cross_review
      - condition: merge_conflict
        next_step: resolve_conflict

  - name: resolve_conflict
    agent: conductor
    transitions:
      - condition: resolved
        next_step: integrate

  - name: cross_review
    description: 各worktree担当者が他の変更をレビュー
    parallel:
      - name: arch-review
        agent: reviewer
        rules:
          - condition: approved
          - condition: needs_fix
      - name: security-review
        agent: security-reviewer
        rules:
          - condition: approved
          - condition: needs_fix
    rules:
      - condition: all("approved")
        next_step: improve
      - condition: any("needs_fix")
        next_step: parallel_execute

  - name: improve
    agent: learner
    transitions:
      - condition: done
        next_step: COMPLETE
```

---

## 4. スラッシュコマンド

### 4.1 `/go` — ワンコマンド実行（メインエントリポイント）

```markdown
<!-- .claude/commands/go.md -->
---
description: |
  Ensembleのメインコマンド。タスクを渡すとConductorが
  自律的に計画・実行・レビュー・改善まで行う。
---

以下のタスクをEnsembleのConductorとして実行してください。

## タスク
$ARGUMENTS

## 実行手順
1. まずplanモードに切り替え、以下を策定:
   - タスクの全体像と成功基準
   - タスク分解（サブタスク一覧）
   - コスト見積もり → ワークフロー選択（simple/default/heavy/worktree）
   - 実行パターンの選択（A: subagent / B: tmux並列 / C: worktree分離）
   - 必要なskills/agents/MCPの確認

2. Dispatchにタスク配信を指示（パターンB/Cの場合）

3. 実行中はDispatchがdashboard.mdを都度更新

4. 全サブタスク完了後:
   - 並列レビュー実行（arch + security）
   - 問題があれば修正ループ
   - 最終承認後、自己改善フェーズをlearnerに委譲

5. 完了報告
```

### 4.2 `/go-light` — 軽量ワークフロー（コスト最小）

```markdown
<!-- .claude/commands/go-light.md -->
---
description: |
  軽量版。README更新やtypo修正など軽微な変更向け。
  simpleワークフローを使用し、コストを最小化する。
---

以下のタスクをsimpleワークフロー（軽量）で実行してください。

## タスク
$ARGUMENTS

## 制約
- simpleワークフローを使用（レビュー1回、修正ループなし）
- tmux並列・worktree分離は使わない
- 自己改善フェーズは省略可
```

### 4.3 `/status` — ダッシュボード確認

```markdown
<!-- .claude/commands/status.md -->
---
description: 現在の進捗状況を表示・更新する
---
status/dashboard.md を読み込み、現在の進捗を報告してください。
未更新の項目があれば、各ペイン/worktreeの状況を確認して更新してください。
queue/reports/ に未処理の完了報告がないかも確認してください。
```

### 4.4 `/improve` — 手動で自己改善を実行

```markdown
<!-- .claude/commands/improve.md -->
---
description: |
  明示的に自己改善を実行。CLAUDE.md更新、skills候補検出、
  ワークフロー改善提案を行う。
---
learner agentを起動し、以下を実行してください:

1. 直近のタスク実行で発生したミス・手戻りの分析
2. CLAUDE.mdへのルール追加提案（コンパクション復帰手順の改善含む）
3. skills候補の検出と提案
4. 新しいagent定義の必要性評価
5. ワークフロー改善案（コスト最適化含む）
6. 通信障害（ACKタイムアウト等）のパターン分析

$ARGUMENTS があればそれを重点的に分析してください。
```

### 4.5 `/review` — 統合レビュー

```markdown
<!-- .claude/commands/review.md -->
---
description: |
  全worktree/全ペインの成果物を統合レビューする。
  並列レビュー（arch + security）と相互レビューを実行。
---
以下を並列で実行してください:

## 並列レビュー
1. **アーキテクチャレビュー** (reviewer agent)
   - コード構造、依存関係の方向、命名規則
2. **セキュリティレビュー** (security-reviewer agent)
   - インジェクション、認証、データ保護

## 統合チェック
3. git diff で全変更を確認
4. テストの網羅性確認
5. worktreeが複数ある場合、相互レビューを実施

レビュー結果をdashboard.mdに記録してください。
```

---

## 5. Hooks（自動化）

```jsonc
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        // タスク完了時にlearnerへの自動委譲を促す
        "matcher": "Task",
        "command": "echo 'Task completed - learner will be invoked'"
      }
    ],
    "PreToolUse": [
      {
        // git commit前にレビュー完了確認
        "matcher": "Bash(git commit:*)",
        "command": "echo '⚠️ Ensure review was completed before committing'"
      }
    ],
    // コンパクション復帰チェック（最重要）
    "Notification": [
      {
        "matcher": "*compaction*",
        "command": "echo '🔄 コンパクション検知！ 自分のエージェント定義を再読み込みしてください。tmux display-message -p #W でペイン名を確認。'"
      }
    ]
  },
  "permissions": {
    "allow": [
      "Read", "Write", "Edit", "Glob", "Grep",
      "Bash(git:*)", "Bash(tmux:*)", "Bash(npm:*)",
      "Skill(*)", "Task(*)"
    ]
  }
}
```

---

## 6. GitHub Actions統合（オプション）

takt-actionの発想を取り入れ、Issueからのリモート実行を可能にする。

**ファイル:** `.github/workflows/ensemble-action.yml`

```yaml
name: Ensemble Action

on:
  issue_comment:
    types: [created]

jobs:
  ensemble:
    if: |
      contains(github.event.comment.body, '@ensemble') &&
      github.event.comment.author_association == 'OWNER'
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code

      - name: Run Ensemble
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # コメントからワークフローを抽出
          COMMENT="${{ github.event.comment.body }}"
          WORKFLOW="default"
          if echo "$COMMENT" | grep -q "simple"; then
            WORKFLOW="simple"
          fi

          # Issue本文をタスクとして実行
          ISSUE_BODY=$(gh issue view ${{ github.event.issue.number }} --json body -q '.body')
          claude -p "以下のタスクを${WORKFLOW}ワークフローで実行: ${ISSUE_BODY}" \
            --dangerously-skip-permissions

      - name: Create PR
        if: success()
        run: |
          git add -A
          git commit -m "feat: resolve #${{ github.event.issue.number }}" || exit 0
          git push origin HEAD
          gh pr create --fill
```

**使い方:**
- `@ensemble run` — defaultワークフローでIssueを実行
- `@ensemble run simple` — simpleワークフロー（軽量・低コスト）

**コスト注意:** API key課金。takt記事によると1タスク≒$1〜$5。
ローカル（Claude Max）との使い分けが重要。

---

## 7. セットアップ手順

### 7.1 前提条件

- Claude Code がインストール済み（`claude` コマンドが動作する）
- tmux がインストール済み
- git 2.20+ （worktree対応）
- Claude Max プラン推奨（並列実行のため）

### 7.2 初回セットアップ

```bash
#!/bin/bash
# scripts/setup.sh

set -e

echo "🎵 Ensemble Setup"
echo "=================="

# 1. 必要コマンドの確認
for cmd in claude tmux git; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ $cmd が見つかりません。インストールしてください。"
        exit 1
    fi
done

# 2. ディレクトリ構成の作成
mkdir -p .claude/{agents,skills,commands}
mkdir -p scripts workflows status notes
mkdir -p queue/{tasks,reports,ack}  # ファイルベースキュー

# 3. CLAUDE.md の初期化（存在しなければ）
if [ ! -f CLAUDE.md ]; then
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

1. 自分のペイン名を確認: `tmux display-message -p '#W'`
2. 対応するエージェント定義を読み直す（.claude/agents/）
3. 禁止事項を確認してから作業開始
4. 現在のタスクをダッシュボードで確認: `cat status/dashboard.md`

**まず自分が誰かを確認せよ。**

## 通信プロトコル
- エージェント間の指示・報告はファイルベースキュー（queue/）経由
- send-keysは「新タスクあり」の通知のみに使用
- ACKファイルで受領確認を行う

## 学習済みルール（自動追記）
<!-- learner agentが自動追記するセクション -->

CLAUDEEOF
fi

# 4. dashboard.md の初期化
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
EOF

echo "✅ セットアップ完了！"
echo ""
echo "使い方:"
echo "  claude  # Claude Codeを起動"
echo "  /go タスク内容  # Ensembleでタスクを実行"
echo "  /go-light タスク内容  # 軽量ワークフロー"
```

### 7.3 日次起動スクリプト

```bash
#!/bin/bash
# scripts/launch.sh
# Ensembleのメインtmuxセッションを起動する

SESSION="ensemble"
PROJECT_DIR=$(pwd)

# 既存セッションがあれば削除
tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"

# キューのクリア（新しいセッションはクリーンスタート）
rm -f queue/tasks/*.yaml queue/reports/*.yaml queue/ack/*.ack

# メインセッション作成（Conductor用、Thinking無効）
tmux new-session -d -s "$SESSION" -n "conductor" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:conductor" \
    "MAX_THINKING_TOKENS=0 claude --model opus --dangerously-skip-permissions" C-m

# Dispatch用ウィンドウ
sleep 3  # フレンドリーファイア防止
tmux new-window -t "$SESSION" -n "dispatch" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:dispatch" \
    "claude --agent dispatch --dangerously-skip-permissions" C-m

# ダッシュボード用ウィンドウ
tmux new-window -t "$SESSION" -n "dashboard" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:dashboard" \
    "watch -n 5 cat status/dashboard.md" C-m

echo "🎵 Ensemble launched!"
echo ""
echo "接続: tmux attach-session -t ensemble"
echo "Conductor: tmux select-window -t ensemble:conductor"
echo "Dispatch:  tmux select-window -t ensemble:dispatch"
echo "Dashboard: tmux select-window -t ensemble:dashboard"
```

---

## 8. 実装ロードマップ

### Phase 1: 基盤構築（1〜2日）

**目標:** 最小限動くものを作る

- [ ] ディレクトリ構成の作成（queue/含む）
- [ ] CLAUDE.md の作成（コンパクション復帰プロトコル含む）
- [ ] conductor.md エージェント定義（Thinking無効）
- [ ] `/go` スラッシュコマンド
- [ ] `setup.sh`, `launch.sh`
- [ ] dashboard.md テンプレート
- [ ] 単純タスク（パターンA）のE2Eテスト

**検証:** `/go "hello worldを出力するPythonスクリプトを作成して"` が動く

### Phase 2: 通信基盤 + 並列実行（2〜3日）

**目標:** フレンドリーファイアしない並列実行

- [ ] dispatch.md エージェント定義
- [ ] ファイルベースキュー（queue/tasks, reports, ack）
- [ ] ACK機構の実装
- [ ] `pane-setup.sh` の実装（起動間隔3秒）
- [ ] reviewer.md, security-reviewer.md エージェント定義
- [ ] dashboard.md のリアルタイム更新（Dispatch担当）
- [ ] 中規模タスク（パターンB）のE2Eテスト

**検証:** `/go "REST APIのCRUDエンドポイント4つを並列で実装して"` がcrashせず動く

### Phase 3: 並列レビュー（1〜2日）

**目標:** takt v0.3式の並列レビュー

- [ ] ワークフローYAMLの `parallel` ステップ実装
- [ ] `all()` / `any()` 集約ルール
- [ ] レビュー結果のプレフィックス付き出力
- [ ] default.yaml（並列レビュー込み）のE2Eテスト

**検証:** arch-reviewとsecurity-reviewが同時実行され、結果が集約される

### Phase 4: git worktree統合（2〜3日）

**目標:** worktree分離 + 統合 + 相互レビュー

- [ ] worktree-manager skill の実装
- [ ] `worktree-create.sh`, `worktree-merge.sh`
- [ ] integrator.md エージェント定義
- [ ] 相互レビュープロトコル
- [ ] コンフリクト解決フロー
- [ ] 大規模タスク（パターンC）のE2Eテスト

**検証:** `/go "認証・API・UIを3つのworktreeで並列開発して統合して"` が動く

### Phase 5: 自己改善 + コスト管理（1〜2日）

**目標:** 自動学習 + コスト意識のワークフロー選択

- [ ] learner.md エージェント定義
- [ ] `/improve` コマンド
- [ ] CLAUDE.md 自動更新ロジック
- [ ] skills候補の検出・提案
- [ ] `/go-light` コマンド（simple.yaml使用）
- [ ] simple.yaml, heavy.yaml の作成
- [ ] notes/ ディレクトリへの学習記録

**検証:** ミスを意図的に起こし、次回同じミスが発生しないことを確認

### Phase 6: GitHub Actions統合（1〜2日、オプション）

**目標:** Issueからリモート実行

- [ ] `.github/workflows/ensemble-action.yml`
- [ ] `@ensemble run` / `@ensemble run simple` の対応
- [ ] PR自動作成
- [ ] コスト監視の仕組み

### Phase 7: 公開準備（2〜3日）

**目標:** OSS公開 or テンプレートリポジトリとして公開

- [ ] README.md の整備
- [ ] セットアップの自動化・簡素化
- [ ] 設定のカスタマイズ性確保
- [ ] サンプルワークフロー/skills/agents の同梱
- [ ] npm パッケージ化（オプション）
- [ ] ライセンス選定（MIT推奨）

---

## 9. 先行ツールとの差別化まとめ

| 観点 | shogun v1.3 | takt v0.3 | Boris氏のチーム | **Ensemble** |
|---|---|---|---|---|
| 自律性 | ◎（AI自由判断） | △（WF強制） | ○（人間判断） | **◎（AI自律 + WF保証ハイブリッド）** |
| 並列実行 | tmux 8ペイン固定 | parallel step | git worktree手動 | **tmux動的ペイン + git worktree自動判定** |
| 並列レビュー | なし | **all/any集約** | なし | **parallel step + all/any（takt採用）** |
| SPOF対策 | karo+bugyo分離 | なし | なし | **Conductor+Dispatch分離** |
| 通信信頼性 | send-keys直接（crash有） | プロセス内 | なし | **ファイルキュー + ACK** |
| コンパクション対策 | CLAUDE.mdに復帰手順 | なし | なし | **CLAUDE.md + hook自動化** |
| Thinking制御 | 将軍のみ無効 | なし | なし | **Conductor無効、Worker有効** |
| 自己改善 | Skills自動生成 | なし | CLAUDE.md手動 | **全レイヤー自動改善** |
| コスト管理 | なし | WF選択で調整 | なし | **simple/default/heavyの3段階** |
| CI/CD連携 | なし | **GitHub Actions** | なし | **GitHub Actions対応** |
| worktree統合 | なし | clone --shared | 手動merge | **自動統合 + 相互レビュー** |

---

## 10. 注意点・リスク

### 10.1 コスト管理（takt GH Actions記事の教訓）
- 並列実行はトークン消費が激しい。Claude Max x5 以上を推奨
- **ワークフロー選択でコスト制御**: simpleは$0.5〜$1、defaultは$2〜$5、heavyは$5〜$15（目安）
- shogunのイベント駆動方式を採用し、待機中のAPI消費をゼロにする
- worktree数・ペイン数の上限を設定可能にする
- GitHub Actions利用時はAPI key課金。ローカル（Claude Max）との使い分け必須

### 10.2 コンテキストウィンドウの管理（shogun v1.1の教訓）
- Boris氏の知見: サブエージェントでメインのコンテキストをクリーンに保つ
- **コンパクション復帰プロトコル必須**: CLAUDE.mdに記載 + hook
- Conductor+Dispatch分離でConductorのコンテキスト消費を60-70%削減
- worktreeごとに独立したセッションなので、コンテキスト汚染は起きにくい

### 10.3 通信信頼性（shogun v1.3の教訓）
- **フレンドリーファイア防止**: ファイルベースキュー + 配信間隔3秒
- **ACK機構**: 配信確認なしで次を送らない
- **SPOF防止**: Dispatchが死んでもConductorの計画は生存。Dispatch再起動で復旧。
- 統合時のコンフリクト → integrator agentが対応、無理なら人間にエスカレーション

### 10.4 信頼性
- shogunで起きた「足軽が仕事を奪いすぎる」問題 → worktree分離で物理的に防止
- taktの「AIが言うことを聞かない」問題 → hooks + ワークフロー強制で対応
- shogunの「家老が過労死」問題 → Conductor+Dispatch分離で負荷分散

### 10.5 段階的な導入
- 最初はPhase 1（パターンA）だけで運用開始し、慣れてからPhase 2, 3に進む
- 自己改善は最初は `/improve` 手動実行から始め、自動化は後から
- GitHub Actionsは最後（オプション）。まずローカルで安定させる

---

## 11. すぐに始めるには

Phase 1 の最小構成なら、以下の4ファイルだけで始められる:

1. **CLAUDE.md** — プロジェクトの基本ルール（コンパクション復帰プロトコル含む）
2. **`.claude/agents/conductor.md`** — Conductorエージェント定義
3. **`.claude/commands/go.md`** — `/go` コマンド
4. **`.claude/commands/go-light.md`** — `/go-light` コマンド（軽量版）

この4ファイルを作成し、Claude Codeを `MAX_THINKING_TOKENS=0 claude --model opus` で起動して `/go タスク内容` と打つだけで、Conductorが計画→実行→レビューまで自律的に進めてくれる。

tmux並列・Dispatch分離・worktreeはPhase 2以降で段階的に追加すればよい。

---

## 付録A: v1→v2 変更差分サマリー

| 項目 | v1（初版） | v2（本版） | 出典 |
|---|---|---|---|
| Conductor thinking | 未指定 | **MAX_THINKING_TOKENS=0** | shogun v1.1 |
| Dispatch | なし | **新設（頭脳と手足の分離）** | shogun v1.3 |
| コンパクション対策 | なし | **CLAUDE.md復帰手順 + hook** | shogun v1.1 |
| エージェント間通信 | send-keys直接 | **ファイルキュー + ACK** | shogun v1.3 |
| フレンドリーファイア対策 | なし | **配信間隔3秒 + 順次処理** | shogun v1.3 |
| 並列レビュー | transitions記法 | **parallel + all/any集約** | takt v0.3 |
| セキュリティレビューagent | なし | **security-reviewer.md新設** | takt v0.3 |
| コスト管理 | なし | **simple/default/heavy 3段階WF** | takt GH Actions |
| `/go-light` | なし | **新設（simpleワークフロー）** | takt GH Actions |
| GitHub Actions | なし | **ensemble-action.yml（オプション）** | takt GH Actions |
| 専門家熟議 | なし | **重要判断時にペルソナ複数召喚** | shogun v1.1 |
| queue/ | なし | **ファイルベースキュー新設** | shogun v1.3 |

## 参考
- https://github.com/yohey-w/multi-agent-shogun
- https://github.com/nrslib/takt?tab=readme-ov-file
- Claude Code開発者による実践的活用術
  - https://x.com/bcherny/status/2017742743125299476?s=20
  - https://x.com/bcherny/status/2017742745365057733?s=20
  - https://x.com/bcherny/status/2017742747067945390?s=20
  - https://x.com/bcherny/status/2017742748984742078?s=20
  - https://x.com/bcherny/status/2017742750473720121?s=20
  - https://x.com/bcherny/status/2017742752566632544?s=20
  - https://x.com/bcherny/status/2017742753971769626?s=20
  - https://x.com/bcherny/status/2017742755737555434?s=20
  - https://x.com/bcherny/status/2017742757666902374?s=20
  - https://x.com/bcherny/status/2017742759218794768?s=20