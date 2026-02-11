# Issue #8: Anthropic C Compiler記事調査レポート

## 記事概要

**タイトル**: Building a C compiler with a team of parallel Claudes
**著者**: Nicholas Carlini (Anthropic Safeguards team)
**公開日**: 2026-02-05
**URL**: https://www.anthropic.com/engineering/building-c-compiler

### 記事の要点

- Opus 4.6 + Agent Teams で**16並列Claude**がRust製Cコンパイラを自律開発
- 約2,000 Claude Codeセッション、$20,000のAPIコスト
- 10万行のコンパイラを生成、Linux 6.9をx86/ARM/RISC-Vでビルド可能
- GCC torture test suiteで99%パス率

---

## Ensembleに活かせる知見

### 1. 自律ループ（Autonomous Loop）

**記事のアプローチ**:
```bash
#!/bin/bash
while true; do
  COMMIT=$(git rev-parse --short=6 HEAD)
  LOGFILE="agent_logs/agent_${COMMIT}.log"
  claude --dangerously-skip-permissions \
    -p "$(cat AGENT_PROMPT.md)" \
    --model claude-opus-X-Y &> "$LOGFILE"
done
```

**Ensembleとの比較**:

| 項目 | 記事のアプローチ | Ensemble現状 |
|------|-----------------|-------------|
| ループ構造 | bashの無限ループ | tmux send-keysによる手動トリガー |
| タスク選択 | エージェントが自律判断 | Conductorが事前に計画 |
| コンテキスト | 毎回リセット（新セッション） | セッション内で蓄積 |
| 並列制御 | git lock（current_tasks/） | queue/ファイルベース |
| ループ検知 | なし（無限ループ許容） | LoopDetector実装済み |

**提案**: `ensemble run --loop` モード
- Workerがタスク完了後、自動で次のタスクを取得するループモード
- `PipelineRunner`を拡張し、タスクキューから連続実行
- 各ループでgitコミット → 新セッション（コンテキストリセット）
- `LoopDetector`と組み合わせて安全にループ制御

### 2. タスクロック機構（Task Locking）

**記事のアプローチ**:
- `current_tasks/` ディレクトリにテキストファイルを書いてロック
- gitの同期で衝突を検知
- 完了後にロック解除

**Ensemble現状**:
- `queue/tasks/` → `queue/processing/` のファイル移動で管理
- `lock.py` でflockによる排他制御
- `ack.py` でACK確認

**比較**: Ensembleのロック機構はより堅牢（flock + atomic write）。
記事のgitベースロックは分散環境向きだが、単一マシンでは過剰。

**提案**: 現状維持。ただしworktree（パターンC）利用時は記事のgitベースロックが参考になる。

### 3. テスト駆動の自律開発

**記事の重要な教訓**:

> Claude will work autonomously to solve whatever problem I give it.
> So it's important that the task verifier is nearly perfect.

- **高品質テストの重要性**: テストが不完全だとClaudeが間違った問題を解く
- **CIパイプライン**: 新コミットが既存機能を壊さないことを保証
- **増分テスト**: `--fast`オプションで1%/10%サンプルを実行（コンテキスト汚染防止）

**Ensembleへの適用**:
- `simple.yaml`/`default.yaml`/`heavy.yaml` のワークフローは既にテスト戦略を含む
- **提案**: テスト結果のサマリー機能を追加
  - 長い出力をログファイルに退避
  - 集約統計（pass/fail/skip数）のみをコンテキストに表示
  - `ERROR` + 理由を1行で出力（grepしやすく）

### 4. コンテキストウィンドウ汚染への対策

**記事の教訓**:

> The test harness should not print thousands of useless bytes.
> At most, it should print a few lines of output and log all important information to a file.

**Ensembleへの適用**:
- NDJSONログ（`logger.py`）は既に実装済み
- **提案**: Worker向けの出力フィルタ
  - テスト出力を `.ensemble/logs/` に退避
  - サマリーのみをWorkerのコンテキストに表示
  - 記事と同様の `--fast` テストモード

### 5. 時間感覚の欠如への対策

**記事の教訓**:

> Claude can't tell time and, left alone, will happily spend hours running tests.

**Ensembleへの適用**:
- 3段階エスカレーション（`ack.py`）にタイムアウトは実装済み
- **提案**: タスク実行時間の上限設定
  - `PipelineRunner`の`timeout=600`（10分）は良い開始点
  - Worker毎の経過時間をダッシュボードに表示
  - 時間超過時に自動でタスク分割を提案

### 6. 並列化の課題と対策

**記事の教訓**:
- 独立テストが多い時は並列化が容易
- 1つの巨大タスク（Linux kernel）では16エージェントが同じバグに集中
- **解決策**: GCCをオラクルとして使い、ランダムにファイルを分配

**Ensembleへの適用**:
- パターンB（tmux並列）は既にタスク分配をサポート
- **提案**: タスク重複検知機構
  - `current_tasks/` 的な仕組みをWorker間で共有
  - 同一ファイルへの同時修正を防止（現状はConductorが手動で分離）

### 7. エージェント専門化

**記事のアプローチ**:
- コード品質担当、パフォーマンス担当、ドキュメント担当など役割を分離
- 重複コード統合、設計批評など「メタタスク」も並列実行

**Ensemble現状**:
- Conductor/Dispatch/Worker/Reviewer/Security-Reviewer/Integrator/Learner の7役割
- 記事よりも体系的な役割分担が既に実装済み

**比較**: Ensembleの役割設計は記事よりも成熟している。
記事はアドホックな専門化だが、Ensembleはワークフロー組み込み。

---

## 新機能提案: セッション開始時のタスク自動追加

Issue #8の要望:
> セッションごとに、ソースコードを確認してタスクを自動で追加するとかできたら良さそう

### 提案: `ensemble scan` コマンド

セッション開始時にコードベースを分析し、タスクを自動生成:

```
ensemble scan
  ↓
1. TODO/FIXME/HACK コメントを収集
2. テストカバレッジの低いファイルを特定
3. lint/type-check 警告を収集
4. 未解決のGitHub Issueを取得
5. PROGRESS.md/PLAN.md から未完了タスクを抽出
  ↓
タスクリストを生成 → Conductorに提示
```

### 実装案

```python
# src/ensemble/scanner.py

class CodebaseScanner:
    """セッション開始時にコードベースを分析しタスクを自動生成"""

    def scan_todos(self) -> list[Task]:
        """TODO/FIXME/HACKコメントを収集"""

    def scan_test_coverage(self) -> list[Task]:
        """テストカバレッジの低いファイルを特定"""

    def scan_lint_warnings(self) -> list[Task]:
        """lint/type-check警告を収集"""

    def scan_github_issues(self) -> list[Task]:
        """未解決のGitHub Issueを取得"""

    def scan_progress(self) -> list[Task]:
        """PROGRESS.md/PLAN.mdから未完了タスクを抽出"""

    def generate_task_queue(self) -> TaskQueue:
        """全スキャン結果を統合してタスクキューを生成"""
```

### 記事との対応

記事では各Claudeが「next most obvious problem」を自律選択:

> I leave it up to each Claude agent to decide how to act.
> In most cases, Claude picks up the "next most obvious" problem.

`ensemble scan` はこれを構造化したもの:
- 記事: エージェントが自律的にREADME/進捗ファイルを読んで判断
- 提案: スキャナーが事前にタスク候補を抽出し、Conductorが優先度判定

---

## 優先度付き実装ロードマップ

| 優先度 | 提案 | 工数 | 期待効果 |
|--------|------|------|----------|
| P0 | `ensemble scan` コマンド（タスク自動生成） | 中 | セッション効率化 |
| P1 | 自律ループモード（`--loop`） | 大 | 長時間無人実行 |
| P1 | テスト出力フィルタ（コンテキスト汚染防止） | 小 | Worker品質向上 |
| P2 | タスク実行時間ダッシュボード表示 | 小 | 可視性向上 |
| P2 | タスク重複検知（Worker間） | 中 | 並列効率向上 |
| P3 | worktree用gitベースロック | 中 | パターンC安定化 |

---

## 記事とEnsembleの思想比較

| 観点 | 記事（Carlini） | Ensemble |
|------|----------------|----------|
| オーケストレーション | なし（各エージェントが自律判断） | Conductor中心の階層型 |
| 通信 | gitのみ（push/pull） | ファイルキュー + send-keys + inotifywait |
| タスク管理 | current_tasks/ ロック | queue/ + ACK + LoopDetector |
| レビュー | なし（テストのみ） | 並列レビュー（arch/security） |
| コスト管理 | なし（$20,000使用） | Bloom分類 + ワークフロー選択 |
| 自己改善 | README/進捗ファイル更新 | Learnerエージェント + MEMORY.md |

**結論**: 記事は「最小限の制約で自律性を最大化」するアプローチ。
Ensembleは「構造化された自律性」で品質とコストを管理するアプローチ。
両者は相補的であり、記事の自律ループ思想を取り入れつつ、
Ensembleの品質管理フレームワーク内で安全に実行する方向が最適。

---

*調査完了: 2025-02-11*
*調査者: Conductor (Issue #8)*
