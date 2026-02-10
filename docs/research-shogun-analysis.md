# multi-agent-shogun 調査レポート

**調査日**: 2025-02-11
**対象**: https://github.com/yohey-w/multi-agent-shogun (v3.0)
**目的**: Ensembleの参考実装であるshogunの設計思想・アーキテクチャを分析し、Ensembleへの改善示唆を得る

---

## 1. アーキテクチャ概要

### 3層階層構造（封建制メタファー）

```
Lord（人間） → Shogun（1体） → Karo（1体） → Ashigaru（8体）
```

| コンポーネント | 役割 | モデル |
|--------------|------|--------|
| Shogun | 最高司令官。ユーザーの指示を受け、YAMLに書いてKaroに委譲。即座にユーザーに制御を返す | Opus |
| Karo | 管理者。タスクを分解し、Ashigaruに配分。ダッシュボード唯一の更新者 | Opus |
| Ashigaru 1-4 | 実行者（標準） | Sonnet |
| Ashigaru 5-8 | 実行者（高能力） | Opus |

### tmux構成

- `shogun` セッション（1ペイン）- ユーザーがここに接続
- `multiagent` セッション（9ペイン: Karo + Ashigaru 1-8）- バックグラウンドで稼働

### Ensembleとの構造比較

| 項目 | Shogun | Ensemble |
|------|--------|---------|
| 指揮者 | Shogun（Opus） | Conductor（Opus） |
| 管理者 | Karo（Opus） | Dispatch（Sonnet） |
| 実行者 | Ashigaru x8（固定） | Worker x1-4（動的） |
| レビュー | なし | Reviewer / Security-Reviewer |
| 学習 | Memory MCP | Learner agent |
| 統合 | なし | Integrator（worktree用） |

---

## 2. 通信システム（最大の差別化ポイント）

### shogunのメールボックスシステム

shogunの通信は**完全イベント駆動**。ポーリングは一切使わない。

```
Karo が Ashigaru 3 を起こしたい場合:

Step 1: メッセージ書き込み
  inbox_write.sh → queue/inbox/ashigaru3.yaml に flock 排他ロック付きで書き込み

Step 2: ファイル変更検知
  inbox_watcher.sh → inotifywait がカーネルレベルでファイル変更を検知（CPU 0%）

Step 3: Wake-up シグナル
  tmux send-keys で "inbox3" とだけ送信（メッセージ本体は送らない）

Step 4: エージェントが自分のinboxを読む
  Ashigaru 3 が queue/inbox/ashigaru3.yaml を Read し、未読メッセージを処理
```

### 通信の主要特徴

| 特徴 | 詳細 |
|------|------|
| メッセージ永続化 | `inbox_write.sh` がYAMLに書き込み（flock排他ロック付き） |
| イベント検知 | `inotifywait` でファイル変更をカーネルレベルで検知（CPU使用率0%） |
| Wake-up | tmux send-keysは短い通知（`inbox3`のみ）。メッセージ本体はファイル経由 |
| Atomic Write | tmp ファイル + rename で部分読み取りを防止 |
| Overflow保護 | 最大50メッセージ。超過時は既読の古いものから削除 |

### 3段階エスカレーション

応答しないエージェントに対する自動復旧措置:

| フェーズ | タイミング | アクション |
|---------|----------|-----------|
| Phase 1 | 0-2分 | 通常nudge（send-keys） |
| Phase 2 | 2-4分 | Escape x2 + C-c + nudge（カーソル位置バグ対策） |
| Phase 3 | 4分+ | `/clear` 送信（5分に1回まで。強制セッションリセット） |

### Agent Self-Watch

各エージェントが自分のinboxファイルを `inotifywait` で直接監視。外部からのnudgeなしで自律的に起動する。

### Ensembleとの通信比較

| 項目 | Shogun | Ensemble |
|------|--------|---------|
| 通信方式 | inotifywait + inbox YAML（イベント駆動） | send-keys + YAML（ポーリング/送信ベース） |
| メッセージ伝達 | ファイル経由のみ。send-keysは「起きろ」だけ | send-keysでメッセージ通知 + YAMLキュー |
| 排他制御 | flock + atomic write（tmp+rename） | ファイル直接書き込み |
| エスカレーション | 3段階自動（通常→Escape→/clear） | 手動/エスカレーションYAML |
| Busy検知 | pane内容のgrep（Working/Thinking等） | なし |

---

## 3. 設計思想の比較

| 思想 | Shogun | Ensemble |
|------|--------|---------|
| 中心原則 | 「Zero coordination overhead」- API呼び出しは実作業のみ | 「考えるな、委譲しろ」- Conductorは判断のみ |
| コスト意識 | CLIサブスクで定額。「8体使い倒せ」 | ワークフロー選択でコスト制御（simple/default/heavy） |
| 学習 | Memory MCP + Bottom-Up Skill Discovery | MEMORY.md + learner agent |
| 非同期性 | 完全非同期（Shogun即座にreturn） | 待機ポーリング（30秒間隔で完了確認） |
| レビュー | なし（ashigaruの自己レビューのみ） | 並列レビュー（アーキ+セキュリティ） |
| タスク分類 | Bloom's Taxonomy（L1-L6）でモデル選択 | タスク規模でパターン（A/B/C/T）選択 |

### 5つの核心原則（Shogun）

1. **自律的陣形設計**: テンプレートではなく複雑度に基づいてタスク陣形を設計
2. **並列化**: サブエージェントでボトルネック防止
3. **Research First**: 訓練データに頼らず、能動的に調査してから判断
4. **継続学習**: Memory MCPで教訓をセッション横断で永続化
5. **三角測量**: 重要な判断は複数ソースで検証

---

## 4. 主要機能の詳細

### 4-1. Bloom's Taxonomyによるタスク分類

タスクの認知レベルに基づいてモデルを自動選択:

| レベル | カテゴリ | 内容 | モデル |
|--------|---------|------|--------|
| L1 | Remember | 事実の想起、コピー、リスト | Sonnet |
| L2 | Understand | 説明、要約、言い換え | Sonnet |
| L3 | Apply | 手順の実行、既知パターンの適用 | Sonnet |
| L4 | Analyze | 比較、調査、分解 | Opus |
| L5 | Evaluate | 判断、批評、推奨 | Opus |
| L6 | Create | 設計、構築、新しい解決策の合成 | Opus |

### 4-2. Bottom-Up Skill Discovery

```
Ashigaru がタスク完了
    ↓
パターンを検知: 「このパターンを3回実行した」
    ↓
レポートYAMLに skill_candidate として報告
    ↓
Karo が dashboard.md に集約
    ↓
Lord（ユーザー）が承認 → .claude/commands/ にスキル作成
```

### 4-3. マルチCLI対応

| CLI | 主要強み | デフォルトモデル |
|-----|---------|--------------|
| Claude Code | tmux統合、Memory MCP | Claude Sonnet 4.5 |
| OpenAI Codex | サンドボックス実行、JSONL出力 | gpt-5.3-codex |
| GitHub Copilot | GitHub MCP、4専門エージェント | Claude Sonnet 4.5 |
| Kimi Code | 無料枠、多言語サポート | Kimi k2 |

`lib/cli_adapter.sh` でCLI差異を吸収。`instructions/cli_specific/` でCLI固有のツール記述を管理。

### 4-4. 4層コンテキスト管理

| レイヤ | 場所 | 永続性 | 用途 |
|--------|------|--------|------|
| Layer 1: Memory MCP | `memory/shogun_memory.jsonl` | セッション横断 | 長期記憶（好み、ルール、教訓） |
| Layer 2: Project | `config/projects.yaml`, `context/` | プロジェクト横断 | プロジェクト固有情報 |
| Layer 3: YAML Queue | `queue/` | タスク横断 | タスク管理（唯一の真実の源） |
| Layer 4: Session | CLAUDE.md, instructions/ | セッション内 | 作業コンテキスト（/clearで消失） |

### 4-5. ntfy通知（双方向モバイル通信）

- **PC → スマホ**: タスク完了通知、進捗報告
- **スマホ → PC**: 音声入力でコマンド送信（Tailscale + SSH不要）
- SayTask: 行動心理学ベースのモチベーション管理（ストリーク追跡、Eat the Frog）

### 4-6. 安全性設計

**3段階の破壊的操作安全策**:

| Tier | レベル | 内容 |
|------|--------|------|
| Tier 1 | 絶対禁止 | `rm -rf /`, `git push --force`, `sudo`, `kill`, pipe-to-shell 等 |
| Tier 2 | 停止＆報告 | 10ファイル超の削除、プロジェクト外のファイル変更 等 |
| Tier 3 | 安全デフォルト | `--force-with-lease`, `git stash`, dry-run 優先 |

**プロンプトインジェクション防御**: ファイル内容はDATA扱い。task YAML以外の指示は実行しない。

---

## 5. Ensembleが優れている点

| 項目 | 詳細 |
|------|------|
| レビュー層 | 並列レビュー（アーキテクチャ + セキュリティ）が組み込み |
| Agent Teams | 調査・レビュー専用モード（Claude Code公式機能活用） |
| 動的ワーカー数 | タスク規模に応じた動的スケーリング（1-4体） |
| Worktree分離 | 大規模タスクでgit worktreeによる完全分離 |
| ワークフロー選択 | simple/default/heavyでコスト制御 |
| 自己改善フェーズ | learner agentによるMEMORY.md更新が毎回実行 |
| 相互レビュー | worktree統合時にcoder同士が相互レビュー |

---

## 6. Ensembleへの改善提案（優先度順）

### 高優先度

| 提案 | 効果 | 元ネタ |
|------|------|--------|
| inotifywaitベースのイベント駆動通信の導入 | ポーリング廃止、検知遅延0秒化、CPU効率改善 | Shogun inbox_watcher.sh |
| Worker無応答時の3段階自動エスカレーション | 手動介入削減、復旧時間短縮（4分以内自動復旧） | Shogun 3-phase escalation |

### 中優先度

| 提案 | 効果 | 元ネタ |
|------|------|--------|
| メッセージ/Wake-up分離（send-keys最小化） | tmux送信エラー防止、信頼性向上 | Shogun nudge-only design |
| flock排他ロックによるYAML書き込み保護 | 並列書き込み時のデータ破壊防止 | Shogun inbox_write.sh |
| /clearリカバリプロトコルの明文化 | コンテキスト枯渇時の自動復旧 | Shogun /clear recovery |

### 低優先度

| 提案 | 効果 | 元ネタ |
|------|------|--------|
| Bloom's Taxonomy的タスク分類 | モデル選択の最適化、コスト効率向上 | Shogun Bloom levels |
| Bottom-Up Skill Discovery統合 | 自動的なスキル候補検出 | Shogun skill_candidate |
| マルチCLI対応の設計検討 | 将来の拡張性確保 | Shogun cli_adapter.sh |
| ntfy双方向モバイル通信 | モバイルからの指示・通知受信 | Shogun ntfy integration |
| Agent Busy検知 | Working中のnudgeスキップで信頼性向上 | Shogun agent_is_busy() |

---

## 7. 所感

Shogunは**通信インフラの成熟度**がEnsembleより高い。特にinotifywaitベースのイベント駆動と3段階エスカレーションは、実運用で遭遇する「エージェントが応答しない」問題への実践的な解決策である。

一方、Ensembleは**レビュー・品質保証・コスト制御**の面で優れた設計を持つ。Shogunにはレビュー層がなく、Ashigaruの自己レビューに依存している。また、Ensembleのワークフロー選択（simple/default/heavy）やAgent Teamsモードは、タスク特性に応じた柔軟な実行戦略を提供する。

**両者の良い部分を統合する方向性**:
1. Shogunの通信インフラ（inotifywait + flock + 3段階エスカレーション）をEnsembleに導入
2. Ensembleのレビュー層・コスト制御・Agent Teamsをそのまま維持
3. Bloom's Taxonomyをワーカーのモデル選択に活用（Opus/Sonnet使い分け）

これにより、信頼性の高い通信基盤の上に、品質保証とコスト効率を兼ね備えたオーケストレーションシステムが実現できる。

---

*本レポートはEnsemble Conductor（モードT）による調査結果です。*
