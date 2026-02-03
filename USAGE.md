# Ensemble 使い方ガイド

## 概要

EnsembleはClaude Codeを活用したAIオーケストレーションツールです。
タスクを渡すと、Conductor（指揮者）が自律的に計画・実行・レビュー・改善まで行います。

## インストール

### uvを使用（推奨）

```bash
# グローバルにインストール
uv tool install ensemble-ai

# またはプロジェクトに追加
uv add ensemble-ai
```

### pipを使用

```bash
pip install ensemble-ai
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
        └── improve.md
```

## コマンド一覧

### CLIコマンド

| コマンド | 説明 |
|---------|------|
| `ensemble init` | プロジェクトでEnsembleを初期化 |
| `ensemble init --full` | エージェント/コマンド定義もローカルにコピー |
| `ensemble init --force` | 既存ファイルを上書き |
| `ensemble launch` | tmuxセッションを起動してアタッチ |
| `ensemble launch --session NAME` | セッション名を指定 |
| `ensemble launch --no-attach` | セッションを起動するがアタッチしない |
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

## 実行パターン

Conductorがタスク規模に応じて自動選択します。

| パターン | 条件 | 実行方法 |
|---------|------|---------:|
| A | 変更ファイル ≤ 3 | subagentで直接実行 |
| B | 変更ファイル 4〜10 | tmux並列実行 |
| C | 変更ファイル > 10、機能独立 | git worktree分離 |

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

# tmuxセッション起動
ensemble launch

# Conductorペインでタスク実行
/go hello worldを出力するPythonスクリプトを作成して
```

### 2. 中規模の機能開発

```bash
# tmuxセッション起動
ensemble launch

# Conductorウィンドウで
/go ユーザー管理APIを実装して（CRUD + 認証）
```

### 3. 大規模リファクタ

```bash
# tmuxセッション起動
ensemble launch

# Conductorウィンドウで（heavy.yamlが自動選択される）
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

## tmuxセッションの構成

`ensemble launch` で起動されるセッション:

```
┌─────────────────────────┬─────────────────────┐
│                         │     Dashboard       │
│       Conductor         │  (watch dashboard)  │
│     (claude CLI)        ├─────────────────────┤
│                         │     Dispatch        │
│                         │    (claude CLI)     │
└─────────────────────────┴─────────────────────┘
```

- **Conductor**: 指揮者エージェント（メイン操作ペイン）
- **Dashboard**: ダッシュボード表示（自動更新）
- **Dispatch**: タスク配信エージェント

## 注意事項

- Conductorは「考えるな、委譲しろ」の原則で動作
- 計画→承認→実行の順序を守る
- セキュリティに関わる変更は自動的にheavy.yamlが選択される
- 学習記録は `.ensemble/notes/` に累積され、削除されない
- `.ensemble/queue/` と `.ensemble/panes.env` は `.gitignore` に追加される
