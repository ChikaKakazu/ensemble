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
| **T: Agent Teams** | 調査・レビュー・設計タスク | Agent Teams並列調査 | 並列コードレビュー、技術調査 |

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

### 4.4 モードT: Agent Teams（調査・レビュー専用）

Claude Code公式のAgent Teams機能を活用した並列調査・レビューモード。
コード実装ではなく、調査・レビュー・設計探索に特化。

#### 特徴

- **Conductor直接操作**: Dispatchやqueueは不要
- **並列調査**: 複数のteammateが独立して調査・レビュー
- **結果統合**: Conductorが各メイトの結果を収集・矛盾解消
- **議論機能**: メイト間でメッセージ交換（競合仮説の場合）

#### 適用ユースケース

| ユースケース | 説明 | 例 |
|-------------|------|-----|
| 並列コードレビュー | 複数観点での同時レビュー | セキュリティ/パフォーマンス/テストカバレッジ |
| 競合仮説によるデバッグ調査 | 異なる仮説を並列検証 | 原因A説 vs 原因B説を並列調査 |
| 技術調査・リサーチ | 複数技術/ライブラリの並列評価 | React vs Vue vs Svelte比較 |
| 新モジュール/機能の設計検討 | 異なるアプローチの並列探索 | 設計案A vs 設計案B vs 設計案C |
| クロスレイヤー変更の計画 | 観点別計画策定 | フロント/バック/テスト観点別 |

#### 実行フロー

```
1. Conductorがタスク種別を分析
   - 調査・レビュー系と判定 → モードT選択

2. 自然言語でチーム作成:
   「Create an agent team to review PR #123 from multiple perspectives.
    Spawn three teammates: security, performance, and test coverage.
    Use Sonnet for all teammates.」

3. Delegate Modeを有効化（推奨）:
   - Shift+Tab押下
   - Conductorを調整専用に制限（コード変更禁止）

4. 各teammateにタスクを割り当て:
   - 自然言語で指示
   - 共有タスクリスト（~/.claude/tasks/）に自動登録

5. Teammatesが独立作業:
   - 各teammateが異なる観点で調査・レビュー
   - 必要に応じてメイト間でメッセージ交換

6. 結果を統合:
   - Conductorが各メイトの結果を収集
   - 矛盾があれば調整・再調査
   - 最終レポートを作成

7. クリーンアップ:
   - 「Clean up the team」で終了
```

#### 使わないEnsembleコンポーネント

Agent TeamsはConductor直接操作のため、以下は不要:

- ❌ Dispatch（不要）
- ❌ queue/ディレクトリ（不要）
- ❌ send-keys通知（不要）
- ❌ pane-setup.sh（不要）
- ❌ ACKファイル（不要）
- ❌ completion-summary.yaml（不要）

#### コード実装には使わない

**重要**: モードTは調査・レビュー・設計探索専用。
コード実装タスクにはパターンA/B/Cを使用。

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

### 5.4 ループ検知
無限ループを防ぐため、2種類のループ検知機構を導入:

#### LoopDetector
- 同一タスクの繰り返し回数を記録
- デフォルト閾値: 5回
- 超過時にLoopDetectedErrorを発生

#### CycleDetector
- レビュー→修正→レビューのサイクルを検知
- デフォルト閾値: 3サイクル
- 超過時にConductorにエスカレーション

```python
from ensemble.loop_detector import LoopDetector

detector = LoopDetector(max_iterations=5)
if detector.record(task_id):
    raise LoopDetectedError(f"Task {task_id} exceeded max iterations")
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

### 6.3 タスク依存関係
`blocked_by`フィールドで順序依存タスクを管理:

```yaml
id: task-002
instruction: "APIテストを作成"
files: ["tests/test_api.py"]
blocked_by:
  - task-001  # task-001完了後に実行可能
workflow: default
```

#### DependencyResolver
- タスクグラフを構築し、依存解決済みタスクをフィルタリング
- 循環依存を検知（DFS）
- 完了時に自動的に依存タスクを解放

```python
from ensemble.dependency import DependencyResolver

resolver = DependencyResolver(tasks)
ready_tasks = resolver.get_ready_tasks()  # 実行可能タスク
resolver.mark_completed(task_id)  # 完了マーク
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

### 7.5 イベント駆動通信
send-keys通知（プライマリ）+ ポーリング（フォールバック）のハイブリッド方式:

#### inbox_watcher.sh
- inotifywaitでqueue/reports/を監視
- ファイル作成を検知したら即座にsend-keys通知
- 通知失敗時はポーリングで補完

#### flock排他制御
- `atomic_write_with_lock()`でYAML破損を防止
- fcntl.flockによる排他ロック（5秒タイムアウト）
- 3回リトライ

#### 3段階自動エスカレーション
- Phase 1 (0-2分): 通常nudge
- Phase 2 (2-4分): Escape×2 + C-c + nudge
- Phase 3 (4分+): /clear送信（5分に1回まで）

### 7.6 NDJSONセッションログ
全実行履歴を.ensemble/logs/session-{timestamp}.ndjsonに記録:

```json
{"timestamp": "2026-02-11T10:00:00Z", "event": "task_start", "task_id": "task-001", "worker_id": 1}
{"timestamp": "2026-02-11T10:05:00Z", "event": "task_complete", "task_id": "task-001", "status": "success"}
```

#### イベントタイプ
- task_start, task_complete, worker_assign
- review_result, escalation, loop_detected

#### 分析例
```bash
# タスク完了数をカウント
jq -s 'map(select(.event == "task_complete")) | length' session-*.ndjson

# 失敗タスクを抽出
jq -s 'map(select(.event == "task_complete" and .status == "failed"))' session-*.ndjson
```

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

### 8.3 Faceted Prompting
エージェント定義を5つの関心に分離し、宣言的に合成:

| 関心 | ディレクトリ | 内容 |
|------|------------|------|
| WHO | personas/ | 役割定義 |
| RULES | policies/ | 禁止事項・品質基準 |
| WHAT | instructions/ | 手順・フロー |
| CONTEXT | knowledge/ | ドメイン知識 |
| OUTPUT | output-contracts/ | レポートフォーマット |

```python
from ensemble.faceted import FacetedPromptComposer

composer = FacetedPromptComposer()
prompt = composer.compose("conductor")  # 各facetを合成
```

### 8.4 Progressive Disclosure Skills
タスク種別に応じてWorkerにSkillsを動的注入:

```yaml
# dispatch-instruction.yaml
worker_skills:
  - "react-frontend"    # React/Next.js開発スキル
  - "backend-api"       # API実装スキル
  - "testing"           # テスト作成スキル
```

SkillManagerが該当スキルを読み込み、Workerに注入。

### 8.5 CLIコマンド追加
| コマンド | 説明 |
|---------|------|
| `ensemble pipeline` | CI/CDパイプラインモード（非対話） |

### 8.6 Bloom's Taxonomy分類
タスクの認知レベルに基づいてモデルを自動選択:

| レベル | 説明 | モデル |
|--------|------|--------|
| L1 - Remember | 事実の想起、コピー | sonnet |
| L2 - Understand | 説明、要約 | sonnet |
| L3 - Apply | 手順の実行、実装 | sonnet |
| L4 - Analyze | 比較、調査、分析 | opus |
| L5 - Evaluate | 判断、批評、レビュー | opus |
| L6 - Create | 設計、新しい解決策 | opus |

```python
from ensemble.bloom import classify_and_recommend

result = classify_and_recommend("認証システムを設計")
# => {"level": 6, "level_name": "CREATE", "recommended_model": "opus"}
```

### 8.7 Bottom-Up Skill Discovery
Workerが繰り返し実行したパターンを検知し、スキル化候補として提案:

- 同パターン3回検出でスキル候補として記録
- learnerが候補を集約し、Conductorに提案
- 承認後にskillテンプレートを自動生成

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
