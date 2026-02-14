# Ensemble 使い方ガイド

## 概要

EnsembleはClaude Codeを活用したAIオーケストレーションツールです。
タスクを渡すと、Conductor（指揮者）が自律的に計画・実行・レビュー・改善まで行います。

## インストール

### uvを使用（推奨）

```bash
# グローバルにインストール
uv tool install ensemble-claude

# またはプロジェクトに追加
uv add ensemble-claude
```

### pipを使用

```bash
pip install ensemble-claude
```

### ソースからインストール

```bash
git clone https://github.com/ChikaKakazu/ensemble.git
cd ensemble

# uvを使用
uv pip install -e .

# またはpipを使用
pip install -e .
```

## セットアップ

```bash
# プロジェクトでEnsembleを初期化
ensemble init

# エージェント定義もローカルにコピー（カスタマイズ用）
ensemble init --full

# tmuxセッションの起動
ensemble launch
```

### `ensemble init` で作成されるもの

```
your-project/
├── .ensemble/                 # Ensemble作業ディレクトリ
│   ├── queue/                 # ファイルベースキュー
│   │   ├── conductor/
│   │   ├── tasks/
│   │   ├── reports/
│   │   └── ack/
│   ├── status/
│   │   └── dashboard.md       # ダッシュボード
│   └── panes.env              # ペインID（launch時に生成）
├── CLAUDE.md                  # Ensembleセクション追記
└── .gitignore                 # Ensemble除外設定追記
```

### `ensemble init --full` で追加されるもの

```
your-project/
└── .claude/
    ├── agents/                # エージェント定義（カスタマイズ可能）
    │   ├── conductor.md
    │   ├── dispatch.md
    │   ├── worker.md
    │   ├── reviewer.md
    │   ├── security-reviewer.md
    │   ├── integrator.md
    │   └── learner.md
    └── commands/              # コマンド定義
        ├── go.md
        ├── go-light.md
        ├── status.md
        ├── review.md
        ├── improve.md
        ├── go-issue.md
        ├── create-skill.md
        ├── create-agent.md
        └── deploy.md
```

## コマンド一覧

### CLIコマンド

| コマンド | 説明 |
|---------|------|
| `ensemble init` | プロジェクトでEnsembleを初期化 |
| `ensemble init --full` | エージェント/コマンド定義もローカルにコピー |
| `ensemble init --force` | 既存ファイルを上書き |
| `ensemble launch` | 2つのtmuxセッションを起動してアタッチ |
| `ensemble launch --session NAME` | セッション名のベースを指定（NAME-conductor, NAME-workers） |
| `ensemble launch --no-attach` | セッションを起動するがアタッチしない |
| `ensemble upgrade` | テンプレートの更新を同期（agents, commands, scripts等） |
| `ensemble upgrade --dry-run` | 更新内容を確認（変更なし） |
| `ensemble upgrade --force` | ローカル変更済みファイルもバックアップ付きで上書き |
| `ensemble upgrade --diff` | 更新前にdiffを表示 |
| `ensemble --version` | バージョンを表示 |
| `ensemble --help` | ヘルプを表示 |

### `/go <タスク>` - メインコマンド

タスクを渡すとConductorが自律的に処理します。

```bash
/go ユーザー認証機能を追加して
/go 設定ファイルのバリデーション機能を実装して
```

**実行フロー:**
1. 計画策定（planモード）
2. 実行パターン選択（A/B/C）
3. 並列レビュー（アーキテクチャ + セキュリティ）
4. 自己改善（learnerによる学習記録）

### `/go-light <タスク>` - 軽量版

軽微な変更向け。simple.yamlワークフローを使用し、コストを最小化。

```bash
/go-light READMEのtypoを修正して
/go-light コメントを追加して
```

### `/status` - 進捗確認

現在の進捗状況を表示・更新します。

```bash
/status
/status update "レビュー完了"
```

### `/review [対象]` - コードレビュー

アーキテクチャレビューとセキュリティレビューを並列実行。

```bash
/review                    # 直近のコミットをレビュー
/review src/api/           # 指定ディレクトリをレビュー
```

### `/improve [task-id]` - 自己改善

学習分析を手動実行し、CLAUDE.md更新提案を生成。

```bash
/improve                   # 直近のタスクを分析
/improve task-001          # 指定タスクを分析
```

### `/go-issue [番号]` - Issue駆動開発

GitHub Issueから実装を開始。

```bash
/go-issue                  # Issue一覧から選択
/go-issue 123              # Issue #123を直接指定
```

### `/create-skill <name> <desc>` - Skill生成

プロジェクト固有のskillテンプレートを生成。

```bash
/create-skill my-skill "説明文"
/create-skill frontend-optimizer "Reactコンポーネントのパフォーマンス最適化"
```

### `/create-agent` - 専門Agent生成

技術スタックに応じた専門agentを自動生成。

```bash
/create-agent              # 対話形式で専門agentを作成
```

### `/deploy` - デプロイ自動化

バージョンアップ・PyPI公開を自動実行。

```bash
/deploy                    # バージョンアップ・マージ・公開を一括実行
```

### `/rpi-research <タスク>` - RPI Research

要件解析・技術調査・実現可能性評価を行う。

```bash
/rpi-research ユーザー認証機能を追加  # 調査フェーズ
```

### `/rpi-plan` - RPI Plan

詳細計画策定（アーキテクチャ設計、タスク分解）を行う。

```bash
/rpi-plan                  # 計画フェーズ
```

### `/rpi-implement` - RPI Implement

計画に基づく実装を開始（`/go`に連携）。

```bash
/rpi-implement             # 実装フェーズ
```

## 実行パターン

Conductorがタスク規模・タスク種別に応じて自動選択します。

| パターン | 条件 | 実行方法 |
|---------|------|---------:|
| A | 変更ファイル ≤ 3 | subagentで直接実行 |
| B | 変更ファイル 4〜10 | tmux並列実行 |
| C | 変更ファイル > 10、機能独立 | git worktree分離 |
| T | 調査・レビュー・設計タスク | Agent Teams並列調査 |

## ワークフロー

| ワークフロー | 用途 | レビュー | コスト |
|-------------|------|---------|--------|
| simple.yaml | ドキュメント、typo修正 | 1回 | low |
| default.yaml | 通常の機能開発 | 並列2種 | medium |
| heavy.yaml | 大規模リファクタ、セキュリティ重要 | 並列5種 | high |
| worktree.yaml | 複数機能の同時開発 | 相互レビュー | high |

## エージェント構成

```
┌─────────────┐
│  Conductor  │ ← 指揮者（計画・判断・委譲）
└──────┬──────┘
       │
  ┌────┴────┐
  ▼         ▼
┌────────┐ ┌──────────┐
│Dispatch│ │ Learner  │
└───┬────┘ └──────────┘
    │        ↑ 学習記録
    ▼
┌─────────────────────────────┐
│  Reviewer / Security-Reviewer│ ← 並列レビュー
└─────────────────────────────┘
    │
    ▼ (worktree使用時)
┌──────────┐
│Integrator│ ← 統合・マージ
└──────────┘
```

## エージェント定義の優先順位

`ensemble launch` 時、エージェント定義は以下の優先順位で解決されます:

1. **ローカルプロジェクト**: `./.claude/agents/`
2. **グローバル設定**: `~/.config/ensemble/agents/`
3. **パッケージ内蔵テンプレート**

カスタマイズしたい場合は `ensemble init --full` でローカルにコピーし、編集してください。

## 典型的な使用例

### 1. 新規プロジェクトでのセットアップ

```bash
# プロジェクトディレクトリで
cd my-project

# Ensemble初期化
ensemble init

# tmuxセッション起動（2つのセッションが作成される）
ensemble launch

# 別のターミナルでworkersセッションを監視
tmux attach -t ensemble-workers

# Conductorセッションでタスク実行
/go hello worldを出力するPythonスクリプトを作成して
```

### 2. 中規模の機能開発

```bash
# tmuxセッション起動
ensemble launch

# Conductorセッションで
/go ユーザー管理APIを実装して（CRUD + 認証）
```

### 3. 大規模リファクタ

```bash
# tmuxセッション起動
ensemble launch

# Conductorセッションで（heavy.yamlが自動選択される）
/go 認証システムをJWTからセッションベースに移行して
```

### 4. レビューのみ実行

```bash
/review src/api/
```

### 5. 学習記録の確認・改善

```bash
/improve
# → CLAUDE.md更新提案が表示される
# → 承認すると学習済みルールに追記
```

### 6. RPI Workflow（大規模機能開発向け）

Research → Plan → Implement の段階的ワークフロー:

```bash
# 1. 調査フェーズ
/rpi-research OAuth2認証機能を追加
# → 実現可能性、技術選定、リスク評価を実施
# → GO/NO-GO判定を確認

# 2. 計画フェーズ
/rpi-plan
# → 詳細なアーキテクチャ設計
# → タスク分解と実装計画

# 3. 実装フェーズ
/rpi-implement
# → 計画に基づき /go で実装開始
```

## tmuxセッションの構成

`ensemble launch` で起動されるセッション（**2つの独立したセッション**）:

### セッション1: `{name}-conductor`（ユーザー操作用 + ダッシュボード）

```
┌─────────────────────┬───────────────────┐
│                     │                   │
│      Conductor      │     Dashboard     │
│    (claude CLI)     │  (watch dashboard)│
│                     │                   │
│ ユーザーが /go を   │  進捗をリアルタイム │
│ 入力する場所        │  で監視           │
│                     │                   │
└─────────────────────┴───────────────────┘
```

### セッション2: `{name}-workers`（作業用）

初期状態:
```
┌─────────────────────┬───────────────────┐
│                     │                   │
│      Dispatch       │   Worker Area     │
│    (claude CLI)     │   (placeholder)   │
│                     │                   │
└─────────────────────┴───────────────────┘
```

Worker 2名追加後:
```
┌─────────────────────┬──────────┐
│                     │ worker-1 │
│      Dispatch       ├──────────┤
│                     │ worker-2 │
└─────────────────────┴──────────┘
```

Worker 4名追加後:
```
┌─────────────────────┬──────────┐
│                     │ worker-1 │
│                     ├──────────┤
│      Dispatch       │ worker-2 │
│                     ├──────────┤
│                     │ worker-3 │
│                     ├──────────┤
│                     │ worker-4 │
└─────────────────────┴──────────┘
```

### セッションへの接続

2つの独立したセッションなので、**2つのターミナルウィンドウ**で同時に監視できます。

```bash
# ターミナル1: Conductorセッション（操作 + ダッシュボード監視）
tmux attach -t ensemble-conductor

# ターミナル2: Workersセッション（Dispatch + Workers）
tmux attach -t ensemble-workers
```

### ペイン構成

**Conductorセッション（左60% : 右40%）**:
- **Conductor**: 指揮者エージェント（Opusモデル、思考トークン無効）
- **Dashboard**: ダッシュボード表示（5秒間隔で自動更新）

**Workersセッション（左60% : 右40%）**:
- **Dispatch**: タスク配信エージェント（Sonnetモデル）
- **Worker Area**: ワーカー用（`./scripts/pane-setup.sh` で追加、最大4名）

## 新機能（v0.4.9+）

### Hooks通知

エージェント作業完了時・エラー発生時にターミナルベルで通知します。

- **Stop hook**: エージェント作業完了時に音声通知
- **PostToolUseFailure hook**: エラー発生時に音声通知（2回）
- 複数ペイン監視の認知負荷を軽減

設定: `.claude/settings.json` の `hooks.Stop`, `hooks.PostToolUseFailure`

### Status Line

Conductorペインに現在の状態を常時表示します。

- gitブランチ
- セッション状態（Conductor, Workers）
- Worker数

出力例: `⎇ main | C:✓ W:✓ | Workers: 2`

設定: `.claude/settings.json` の `statusLine`

### CLAUDE.md行数チェック

CLAUDE.mdが150行を超えると警告します（Claude Code Best Practiceに基づく）。

- pre-commit hook: コミット時に自動チェック
- hookify: `.claude/hooks/scripts/check-claude-md-lines.sh`

詳細なルールは `.claude/rules/` に分割することを推奨。

---

## 新機能（v0.5.0）

### Agent Teamsモード（T）- 調査・レビュー専用

並列調査・レビュー・設計探索に特化したモード。Claude Code公式のAgent Teams機能を活用します。

**適用ケース:**
- 並列コードレビュー（セキュリティ/パフォーマンス/テストカバレッジの同時レビュー）
- 競合仮説によるデバッグ調査（異なる仮説を並列検証）
- 技術調査・リサーチ（複数技術/ライブラリの並列評価）
- 新モジュール/機能の設計検討（異なるアプローチの並列探索）

**使用方法:**

```bash
# 自動判定（Conductorが調査・レビュータスクと判断）
/go このバグの原因を調査して

# 強制指定
/go --teams PR #123を複数観点でレビューして
```

**特徴:**
- Conductorが直接Agent Teamsを操作（Dispatch/queue不要）
- 複数のteammateが独立して調査・レビュー
- 結果を統合して最終レポート作成
- コード実装には使用しない（パターンA/B/Cを使用）

### ensemble pipeline コマンド

CI/CDパイプラインモードで非対話実行:

```bash
ensemble pipeline --task "タスク内容"
```

### Faceted Promptingのカスタマイズ

エージェント定義を5つの関心に分離してカスタマイズ:

```bash
# 新しいポリシーを追加
cat > .claude/policies/custom.md << 'EOF'
# Custom Policy
- プロジェクト固有のルール
EOF

# Conductorを再合成
python -c "
from ensemble.faceted import FacetedPromptComposer
composer = FacetedPromptComposer()
prompt = composer.compose('conductor')
print(prompt)
"
```

### スキル定義の追加方法

```bash
# /create-skill コマンドでスキルテンプレートを生成
/create-skill react-optimization "Reactコンポーネントのパフォーマンス最適化"

# 生成された .claude/skills/react-optimization.md を編集
# dispatch-instruction.yamlでWorkerに注入:
worker_skills:
  - "react-optimization"
```

### NDJSONログの分析方法

セッションログを分析:

```bash
# タスク完了数をカウント
jq -s 'map(select(.event == "task_complete")) | length' .ensemble/logs/session-*.ndjson

# 失敗タスクを抽出
jq -s 'map(select(.event == "task_complete" and .status == "failed"))' .ensemble/logs/session-*.ndjson

# Worker別の処理時間
jq -s 'group_by(.worker_id) | map({worker: .[0].worker_id, count: length})' .ensemble/logs/session-*.ndjson
```

### ループ検知の動作説明

無限ループを自動検知して停止:

- **LoopDetector**: 同一タスク5回繰り返しで検知
- **CycleDetector**: レビュー→修正→レビューのサイクル3回で検知
- 検知時はConductorにエスカレーション、ユーザーに報告

### Bloom分類の動作説明

タスクの認知レベルに基づいてモデルを自動選択:

```python
# 「認証システムを設計」→ L6 CREATE → Opus推奨
from ensemble.bloom import classify_and_recommend
result = classify_and_recommend("認証システムを設計")
# => {"level": 6, "level_name": "CREATE", "recommended_model": "opus"}
```

- L1-L3（Remember/Understand/Apply）→ Sonnet
- L4-L6（Analyze/Evaluate/Create）→ Opus

---

## アップグレード

### パッケージ本体の更新

Ensembleのコアロジック（自律ループ、パイプライン、スキャナ等）はPythonパッケージに含まれます。
パッケージの更新には `pip` または `uv` を使用してください。

```bash
# uvを使用（推奨）
uv tool upgrade ensemble-claude
# or プロジェクト依存として
uv add --upgrade ensemble-claude

# pipを使用
pip install --upgrade ensemble-claude
```

### テンプレートファイルの更新

エージェント定義やコマンド定義（`.claude/` 配下）は `ensemble upgrade` で更新します。

```bash
# 更新可能なファイルを確認（変更なし）
ensemble upgrade --dry-run

# 差分を確認してから適用
ensemble upgrade --diff

# 適用（ローカル未変更のファイルのみ）
ensemble upgrade

# ローカル変更済みファイルも含めて強制更新（バックアップ作成）
ensemble upgrade --force
```

**更新対象カテゴリ:**

| カテゴリ | パス | 説明 |
|---------|------|------|
| agents | .claude/agents/*.md | エージェント定義 |
| commands | .claude/commands/*.md | スラッシュコマンド |
| scripts | .claude/scripts/*.sh | シェルスクリプト |
| workflows | .claude/workflows/*.yaml | ワークフロー定義 |
| instructions | .claude/instructions/*.md | フェーズ指示 |
| policies | .claude/policies/*.md | ポリシー |
| personas | .claude/personas/*.md | ペルソナ定義 |
| rules | .claude/rules/*.md | ルール |
| hooks | .claude/hooks/scripts/*.sh | フック |
| settings | .claude/settings.json | 設定 |

**注意:**
- ローカルで変更したファイルはデフォルトでスキップされます（`--force`で上書き可能、バックアップ自動作成）
- `ensemble init --full` を実行していないプロジェクトでは `ensemble upgrade` は動作しません
- `.gitignore` やPythonコアロジックの更新はパッケージ更新（`pip install --upgrade`）で反映されます

---

## 注意事項

- Conductorは「考えるな、委譲しろ」の原則で動作
- 計画→承認→実行の順序を守る
- セキュリティに関わる変更は自動的にheavy.yamlが選択される
- 学習記録は `.ensemble/notes/` に累積され、削除されない
- `.ensemble/queue/` と `.ensemble/panes.env` は `.gitignore` に追加される
