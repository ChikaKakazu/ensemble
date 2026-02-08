# Ensemble AI Orchestration System - Architecture Document

## 1. システム概要

Ensembleは**複数のClaude CLIインスタンスをtmuxで並列実行**し、自律的にタスクを分解・実行・レビュー・改善するAIオーケストレーションシステムです。

### 設計思想

- **階層的委譲**: Conductor（判断）→ Dispatch（伝達）→ Worker（実行）
- **ファイルベース通信**: queue/ディレクトリを介した非同期メッセージング
- **自律的改善**: タスク完了後に自動で振り返り・学習

---

## 2. システムアーキテクチャ

### 2.1 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                     Ensemble Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   [Session 1: ensemble-conductor]                                │
│   ┌─────────────────────┬─────────────────────┐                 │
│   │    Conductor        │     dashboard       │                 │
│   │    (Claude Opus)    │   (watch status)    │                 │
│   └─────────────────────┴─────────────────────┘                 │
│                           │                                       │
│                           │ ファイルベース通信 (queue/)           │
│                           ▼                                       │
│   [Session 2: ensemble-workers]                                  │
│   ┌─────────────────────┬──────────┐                             │
│   │                     │ worker-1 │                             │
│   │    Dispatch         ├──────────┤                             │
│   │   (Claude Sonnet)   │ worker-2 │                             │
│   │                     ├──────────┤                             │
│   │                     │  ...     │                             │
│   └─────────────────────┴──────────┘                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 セッション構成

Ensembleは2つの独立したtmuxセッションで動作します。

| セッション | 用途 | ペイン構成 |
|-----------|------|-----------|
| `ensemble-conductor` | 指揮・監視 | Conductor + Dashboard |
| `ensemble-workers` | 実行 | Dispatch + Worker群 |

```bash
# 2つのターミナルで同時表示
# ターミナル1
tmux attach -t ensemble-conductor

# ターミナル2
tmux attach -t ensemble-workers
```

---

## 3. エージェント定義

### 3.1 Conductor（指揮者）

| 項目 | 内容 |
|------|------|
| モデル | Claude Opus |
| 場所 | `.claude/agents/conductor.md` |
| 最重要ルール | **考えるな、委譲しろ** |

#### 責務
- ユーザーのタスクを受け取り計画立案
- タスクを分解し、実行パターン（A/B/C）を選択
- ワークフロー（simple/default/heavy）を選択
- Dispatchに指示を委譲
- 完了後の最終判断
- 自己改善フェーズをlearnerに委譲

#### 禁止事項
- 自分でコードを書く
- 自分でファイルを直接編集する
- Dispatchの仕事を奪う
- ワーカーの作業を横取りする

---

### 3.2 Dispatch（伝達役）

| 項目 | 内容 |
|------|------|
| モデル | Claude Sonnet |
| 場所 | `.claude/agents/dispatch.md` |
| 最重要ルール | **判断するな、伝達しろ** |

#### 責務
- Conductorからの指示を受信
- ワーカーペインの起動（`pane-setup.sh`実行）
- 各Workerへタスク配信
- ACK（受領確認）の待機・リトライ
- 完了報告の収集と集約
- `status/dashboard.md`の更新
- Conductorへ結果報告

#### 禁止事項
- タスクの内容を判断する
- ワーカーの作業に介入する
- コードを書く・編集する

---

### 3.3 Worker（実行者）

| 項目 | 内容 |
|------|------|
| モデル | Claude Sonnet |
| 場所 | `.claude/agents/worker.md` |
| 最重要ルール | **担当範囲を守れ** |

#### 責務
- タスクYAMLを読み込み実行
- ACKファイルを作成（受領確認）
- 指定されたファイルのみを編集
- 完了/失敗を正直に報告

#### 禁止事項
- 担当外のファイルを編集する
- 他のWorkerのタスクに介入する
- Conductorに直接報告する（必ずDispatch経由）
- 勝手に「完了」扱いにする（正直に failed 報告）

---

### 3.4 Reviewer（レビュー担当）

| 項目 | 内容 |
|------|------|
| モデル | Claude Sonnet |
| 場所 | `.claude/agents/reviewer.md` |

#### レビュー観点
- アーキテクチャ（レイヤー分離、依存関係）
- 設計パターン（適切なパターン、DRY原則）
- コード品質（可読性、命名）
- テスト（カバレッジ80%以上）

#### 結果
- `approved`: critical/highの指摘なし
- `needs_fix`: critical/highの指摘が1つ以上

---

### 3.5 Security Reviewer（セキュリティレビュー担当）

| 項目 | 内容 |
|------|------|
| モデル | Claude Sonnet |
| 場所 | `.claude/agents/security-reviewer.md` |

#### レビュー観点
- インジェクション脆弱性
- 認証・認可
- データ保護
- OWASP Top 10

---

### 3.6 Learner（自己改善エージェント）

| 項目 | 内容 |
|------|------|
| モデル | Claude Sonnet |
| 場所 | `.claude/agents/learner.md` |
| 最重要ルール | **観察→記録→提案** |

#### 責務
- タスク実行を客観的に分析
- ミス・手戻りの検出
- 効率化ポイントの抽出
- スキル化候補のリストアップ
- CLAUDE.md更新提案の生成

#### 出力
- `notes/{task-id}/lessons.md`
- `notes/{task-id}/skill-candidates.md`

---

### 3.7 Integrator（統合担当）

| 項目 | 内容 |
|------|------|
| モデル | Claude Sonnet |
| 場所 | `.claude/agents/integrator.md` |

#### 責務
- パターンC（worktree）使用時のブランチマージ
- コンフリクト解決（まずAI自動解決を試行）

---

## 4. 実行パターン

### 4.1 パターン一覧

| パターン | 条件 | 実行方法 | 例 |
|---------|------|---------|-----|
| **A: subagent直接** | ファイル数 ≤ 3、単純タスク | Dispatch経由で単一Worker | typo修正、単一ファイル修正 |
| **B: tmux並列** | ファイル数 4〜10、並列可能 | 複数Workerペインで並列実行 | 複数エンドポイント実装 |
| **C: worktree分離** | ファイル数 > 10、独立機能 | git worktreeで完全分離 | 認証・API・UIの同時開発 |

### 4.2 パターンB: tmux並列実行

```
1. Conductorがタスクを分解
2. queue/conductor/dispatch-instruction.yaml に指示を書く
3. Dispatchに通知
4. Dispatchがpane-setup.shでWorkerペインを起動
5. 各Workerにタスクを配信
6. 並列実行
7. 完了報告をDispatchが集約
8. Conductorに報告
```

### 4.3 パターンC: worktree分離

```
1. Conductorがworktreeでの実行を判断
2. worktree-create.shで各機能用のworktreeを作成
3. 各worktreeで独立して開発
4. 全worktree完了後、integratorがマージ
5. 相互レビュー（自分以外の変更をレビュー）
```

---

## 5. ワークフロー

### 5.1 ワークフロー一覧

| ワークフロー | レビュー回数 | 修正ループ | 最大イテレーション | コストレベル |
|-------------|------------|-----------|------------------|-------------|
| `simple.yaml` | 1回 | なし | 5 | low |
| `default.yaml` | 並列2種 | あり | 15 | medium |
| `heavy.yaml` | 並列5種 | あり | 25 | high |

### 5.2 選択基準

#### simple.yaml（低コスト）
- README/ドキュメント更新
- typo/文言修正
- 設定ファイルの微調整
- コメント追加/修正

#### default.yaml（標準）
- 新規機能の追加（標準的な規模）
- バグ修正（影響範囲が限定的）
- テストカバレッジ改善
- 小〜中規模のリファクタリング

#### heavy.yaml（高コスト）
- 認証・認可システムの変更
- 決済・課金機能の実装/変更
- セキュリティ脆弱性の修正
- アーキテクチャレベルのリファクタ
- 複数サービス間の変更

### 5.3 default.yamlのフロー

```yaml
steps:
  1. plan        → タスク分析と実行計画の策定
  2. execute     → 計画に基づき実行（並列可能）
  3. parallel_review:
     - arch-review      → アーキテクチャレビュー
     - security-review  → セキュリティレビュー
  4. improve     → 自己改善フェーズ（learner）
```

---

## 6. queue/ ディレクトリ構造

### 6.1 ディレクトリ構成

```
queue/
├── conductor/           # Conductor → Dispatch への指示
│   └── dispatch-instruction.yaml
├── tasks/               # Dispatch → Worker へのタスク
│   ├── worker-1-task.yaml
│   └── worker-2-task.yaml
├── ack/                 # Worker からの受領確認
│   └── task-001.ack
├── reports/             # Worker からの完了報告
│   ├── task-001-completed.yaml
│   └── completion-summary.yaml
└── processing/          # 処理中のタスク
```

### 6.2 ファイルフォーマット

#### dispatch-instruction.yaml（Conductor → Dispatch）

```yaml
type: start_workers  # or start_worktree
worker_count: 2
worker_agent: worker  # デフォルト。create-agentで生成した専門agentも指定可能
tasks:
  - id: task-001
    instruction: "タスクの説明"
    files: ["file1.py", "file2.py"]
  - id: task-002
    instruction: "タスクの説明"
    files: ["file3.py"]
created_at: "2026-02-03T10:00:00Z"
workflow: default
pattern: B
```

#### worker-N-task.yaml（Dispatch → Worker）

```yaml
id: task-001
instruction: "タスクの説明"
files:
  - "対象ファイル1"
  - "対象ファイル2"
workflow: default
created_at: "2026-02-03T10:00:00Z"
```

#### task-XXX-completed.yaml（Worker → Dispatch）

```yaml
task_id: task-001
status: success  # success, failed, blocked
worker_id: 1
summary: "実行内容の要約"
files_modified:
  - "変更したファイル"
errors: []
completed_at: "2026-02-03T10:30:00Z"
```

#### completion-summary.yaml（Dispatch → Conductor）

```yaml
workflow_id: dispatch-instruction-xxx
completed_at: "2026-02-03T11:00:00Z"
status: all_completed
total_tasks: 2
completed_tasks: 2
failed_tasks: 0
task_summary:
  - task_id: task-001
    worker: worker-1
    status: completed
  - task_id: task-002
    worker: worker-2
    status: completed
```

---

## 7. 通信プロトコル

### 7.1 全体フロー

```
Conductor
    │ queue/conductor/dispatch-instruction.yaml を書く
    │ tmux send-keys で Dispatch に通知
    ▼
Dispatch
    │ 指示を読む
    │ pane-setup.sh でWorkerペイン起動
    │ queue/tasks/worker-N-task.yaml を書く
    │ tmux send-keys で各Workerに通知
    ▼
Worker
    │ タスクYAMLを読む
    │ queue/ack/task-XXX.ack を作成（受領確認）
    │ タスク実行
    │ queue/reports/task-XXX-completed.yaml を書く
    │ tmux send-keys で Dispatch に通知
    ▼
Dispatch
    │ 全Workerの報告を収集
    │ status/dashboard.md を更新
    │ queue/reports/completion-summary.yaml を作成
    │ tmux send-keys で Conductor に通知
    ▼
Conductor
    │ 結果を確認
    │ ユーザーに報告
    │ learner に自己改善を委譲
    ▼
完了
```

### 7.2 tmux send-keysプロトコル

#### 必須ルール

```bash
# ❌ 禁止パターン
tmux send-keys -t pane "メッセージ" Enter  # 1行で送ると処理されないことがある
tmux send-keys -t ensemble:main.2 'message'  # ペイン番号は設定依存

# ✅ 正規プロトコル（2回分割 + ペインID）
source .ensemble/panes.env
tmux send-keys -t "$WORKER_1_PANE" 'メッセージ'
tmux send-keys -t "$WORKER_1_PANE" Enter
```

#### 複数Workerへの送信

```bash
source .ensemble/panes.env

# ワーカー1に送信
tmux send-keys -t "$WORKER_1_PANE" 'タスクを確認してください'
tmux send-keys -t "$WORKER_1_PANE" Enter
sleep 2  # フレンドリーファイア防止

# ワーカー2に送信
tmux send-keys -t "$WORKER_2_PANE" 'タスクを確認してください'
tmux send-keys -t "$WORKER_2_PANE" Enter
```

### 7.3 ACK（受領確認）プロトコル

- Workerがタスクを受け取ったら `queue/ack/task-XXX.ack` を作成
- Dispatchは60秒タイムアウト、最大3回リトライ
- 3回失敗 → エスカレーション

### 7.4 /clearプロトコル

Workerのコンテキスト蓄積を防止するための仕組み。

#### いつ送るか
- タスク完了報告受信後、次タスク割当前

#### 送信手順

```bash
# 1. 次タスクYAMLを先に書き込む
# 2. /clear を送信
source .ensemble/panes.env
tmux send-keys -t "$WORKER_1_PANE" '/clear'
sleep 1
tmux send-keys -t "$WORKER_1_PANE" Enter

# 3. Worker復帰を待つ（約5秒）
sleep 5

# 4. タスク読み込み指示を送る
tmux send-keys -t "$WORKER_1_PANE" 'queue/tasks/にタスクがあります。確認して実行してください。'
sleep 1
tmux send-keys -t "$WORKER_1_PANE" Enter
```

#### スキップ条件
- 短タスク連続（推定5分以内）
- 同一ファイル群の連続タスク
- Workerのコンテキストがまだ軽量（タスク2件目以内）

---

## 8. コマンド一覧

### 8.1 CLIコマンド

| コマンド | 説明 |
|---------|------|
| `ensemble init` | プロジェクトをEnsemble用に初期化 |
| `ensemble launch` | 2つのtmuxセッションを起動 |
| `ensemble upgrade` | テンプレートの更新を同期（agents, commands, scripts） |

### 8.2 Skillコマンド（Claude内で使用）

| コマンド | 説明 |
|---------|------|
| `/go タスク` | タスクを自動判定で実行（メインコマンド） |
| `/go --simple タスク` | パターンA強制（subagent直接） |
| `/go --parallel タスク` | パターンB強制（tmux並列） |
| `/go --worktree タスク` | パターンC強制（git worktree） |
| `/go-light タスク` | 軽量ワークフロー（simple.yaml使用） |
| `/go-issue [番号]` | GitHub Issueから実装開始 |
| `/create-skill <name> <desc>` | プロジェクト固有のskillテンプレートを生成 |
| `/create-agent` | 技術スタックに応じた専門agentを自動生成 |
| `/status` | 現在の進捗状況を表示 |
| `/review` | 手動でコードレビューを実行 |
| `/improve` | 手動で自己改善を実行 |
| `/deploy` | バージョンアップ・PyPI公開を自動実行 |
| `/clear` | Workerのコンテキストをクリア |

---

## 9. ディレクトリ構造

### 9.1 プロジェクト構造

```
project/
├── .claude/
│   └── agents/              # エージェント定義（ローカル優先）
│       ├── conductor.md
│       ├── dispatch.md
│       ├── worker.md
│       ├── reviewer.md
│       ├── security-reviewer.md
│       ├── integrator.md
│       └── learner.md
├── .ensemble/
│   ├── panes.env            # ペインID（自動生成）
│   └── status/
│       └── dashboard.md     # ダッシュボード
├── queue/                   # メッセージキュー
│   ├── conductor/
│   ├── tasks/
│   ├── ack/
│   ├── reports/
│   └── processing/
├── notes/                   # 学習ノート
│   └── {task-id}/
│       ├── lessons.md
│       └── skill-candidates.md
├── status/
│   └── dashboard.md         # ダッシュボード
└── CLAUDE.md                # プロジェクト指示
```

### 9.2 panes.env（自動生成）

```bash
# Ensemble pane IDs (auto-generated)
# Session names
CONDUCTOR_SESSION=ensemble-conductor
WORKERS_SESSION=ensemble-workers

# Pane IDs (use these with tmux send-keys -t)
CONDUCTOR_PANE=%0
DASHBOARD_PANE=%1
DISPATCH_PANE=%2
WORKER_AREA_PANE=%3

# After workers are added:
WORKER_1_PANE=%4
WORKER_2_PANE=%5
WORKER_COUNT=2
```

---

## 10. 制約事項

### 10.1 Claude Max制限
- **5並列制限**: Conductor用1 + Worker最大4
- **Extended Thinking無効**: `MAX_THINKING_TOKENS=0`
- **Python 3.11+必須**: pyproject.tomlで `requires-python = ">=3.11"` と指定

### 10.2 共通禁止事項
- ペイン番号（main.0, main.1等）の使用 → ペインIDを使え
- 曖昧な表現での報告 → 具体的な数値を使え

### 10.3 曖昧語禁止ルール

| 禁止表現 | 代替表現の例 |
|---------|-------------|
| 多発 | 3回発生 |
| 一部 | src/api/auth.py の 45-52行目 |
| 適宜 | 5分後に再確認 |
| 概ね | 87% |
| いくつか | 4件 |
| しばらく | 30秒後 |

---

## 11. トラブルシューティング

### 11.1 通信が届かない場合
1. `tmux send-keys`が2回分割になっているか確認
2. ペインIDが正しいか確認（`source .ensemble/panes.env`）
3. ターゲットペインがアクティブか確認

### 11.2 Workerが応答しない場合
1. ACKタイムアウト後、Dispatchが自動リトライ（最大3回）
2. 3回失敗 → エスカレーション
3. Dispatchはポーリングでフォールバック

### 11.3 コンテキスト逼迫
- Worker: `/clear`を使用
- Conductor/Dispatch: `/compact`を自己判断で実行

---

## 12. 参考リンク

- エージェント定義: `.claude/agents/`
- ワークフロー定義: `src/ensemble/templates/workflows/`
- スクリプト: `src/ensemble/templates/scripts/`
- 起動実装: `src/ensemble/commands/_launch_impl.py`
