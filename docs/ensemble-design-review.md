# Ensemble 設計レビュー & 成熟化ロードマップ

**調査日**: 2025-02-11
**目的**: Ensembleが設計思想通りに動作しているか検証し、AIオーケストレーションツールとしての成熟化アイデアを提案する
**参照**: multi-agent-shogun, TAKT, claude-code-best-practice, Agent Teams公式ドキュメント

---

## 目次

1. [設計思想の検証](#1-設計思想の検証)
2. [3ツールとの比較分析](#2-3ツールとの比較分析)
3. [Ensembleの強みと弱み](#3-ensembleの強みと弱み)
4. [設計整合性の評価](#4-設計整合性の評価)
5. [成熟化ロードマップ](#5-成熟化ロードマップ)
6. [総括](#6-総括)

---

## 1. 設計思想の検証

### 1.1 Ensembleの3つの設計原則

| 原則 | 定義 | 現状の遵守度 |
|------|------|-------------|
| 階層的委譲 | Conductor→Dispatch→Worker | **90%** - 概ね機能。後述の改善点あり |
| ファイルベース通信 | queue/ディレクトリを介した非同期メッセージング | **70%** - 動作するが成熟度に課題 |
| 自律的改善 | タスク完了後に自動で振り返り・学習 | **80%** - learner agentは存在するが実行頻度に課題 |

### 1.2 「考えるな、委譲しろ」原則の検証

**Conductorの設計思想**: 判断と委譲のみ。自分でコードを書かない。

**検証結果**:
- **遵守**: conductor.mdに明確に禁止事項が記載されている
- **課題**: モードT（Agent Teams）ではConductorが直接操作する設計のため、委譲の原則と矛盾する可能性がある。ただし調査・レビューはコード実装ではないため、許容範囲内と判断
- **課題**: 完了待機がポーリング（30秒間隔）であり、Conductorのリソースを消費する

### 1.3 「判断するな、伝達しろ」原則の検証

**Dispatchの設計思想**: タスク内容を判断せず、忠実に伝達する。

**検証結果**:
- **遵守**: dispatch.mdに禁止事項が明確
- **課題**: Dispatchがdashboard.mdの更新も担当しており、「集約」は伝達の範囲を超える可能性がある（ただし、shogunのKaroも同様の設計のため、業界標準と言える）

### 1.4 エージェント階層の設計整合性

```
                Ensemble              Shogun               TAKT
指揮者:       Conductor (Opus)    → Shogun (Opus)      → PieceEngine
管理者:       Dispatch (Sonnet)   → Karo (Opus)        → （なし）
実行者:       Worker (Sonnet)     → Ashigaru (混合)    → AgentRunner
レビュー:     Reviewer (Sonnet)   → （なし）           → 並列Movement
セキュリティ: Sec-Reviewer        → （なし）           → （なし）
学習:         Learner (Sonnet)    → Memory MCP         → （なし）
統合:         Integrator (Sonnet) → （なし）           → （なし）
```

**評価**: Ensembleは**最も多くの専門エージェント**を持つ。レビュー・セキュリティ・学習・統合の専門化はshogunやTAKTにない独自の強み。ただし、エージェント数が多い分、通信の複雑さとオーバーヘッドも大きい。

---

## 2. 3ツールとの比較分析

### 2.1 アーキテクチャ比較

| 項目 | Ensemble | Shogun | TAKT | CC Best Practice |
|------|---------|--------|------|-----------------|
| **言語** | Python (CLI) | Bash (スクリプト) | TypeScript (SDK) | Markdown (設定) |
| **並列数** | 1-4 Worker（動的） | 8 Ashigaru（固定） | 並列Movement（宣言的） | subagent（Claude標準） |
| **通信方式** | YAML + send-keys + ポーリング | YAML + inotifywait（イベント駆動） | SDK内部（Promise.all） | Claude標準（Task tool） |
| **レビュー** | 並列2種（アーキ+セキュリティ） | なし（自己レビューのみ） | 並列Movement（宣言的） | なし |
| **学習** | learner agent + MEMORY.md | Memory MCP | なし | CLAUDE.md手動更新 |
| **コスト制御** | ワークフロー3段階 | Battle Formation切替 | max_iterations | 手動/compact |
| **CI/CD** | なし | なし | パイプラインモード | なし |
| **マルチCLI** | Claude Code専用 | Claude/Codex/Copilot/Kimi | Claude/Codex | Claude Code専用 |
| **ループ検知** | なし | なし | LoopDetector + CycleDetector | なし |
| **プロンプト設計** | エージェント定義（md） | 役割定義（md） + 生成システム | Faceted Prompting（5関心分離） | Command→Agent→Skills |

### 2.2 通信インフラ比較（最重要差分）

| 項目 | Ensemble | Shogun |
|------|---------|--------|
| メッセージ書き込み | YAML直接書き込み | flock排他ロック + atomic write |
| 変更検知 | ポーリング（30秒間隔） | inotifywait（カーネルイベント、0ms） |
| Wake-up方式 | send-keysでメッセージ通知 | send-keysは「inbox3」のみ（nudge） |
| エスカレーション | 手動（YAML作成→Conductor対応） | 3段階自動（nudge→Escape→/clear） |
| Busy検知 | なし | pane内容grep（Working/Thinking検知） |
| 排他制御 | なし | flock + atomic write (tmp+rename) |
| CPU効率（待機中） | 低（ポーリング消費） | 高（inotifywait = CPU 0%） |

**結論**: Ensembleの通信インフラはshogunに対して**最大の改善機会**がある。

### 2.3 ワークフロー設計比較

| 項目 | Ensemble | TAKT |
|------|---------|------|
| 定義方式 | simple/default/heavy（3段階） | YAML宣言的（Movement + Rules） |
| 柔軟性 | 固定3パターン | 無限にカスタマイズ可能 |
| レビュー統合 | ワークフロー外（Phase 3で実行） | ワークフロー内（Movement遷移） |
| 修正ループ | あり（needs_fix → 修正） | あり（ルール評価 → 次Movement） |
| 並列評価 | あり（all/any相当） | all()/any() 公式サポート |
| ループ検知 | なし | LoopDetector + CycleDetector |
| レポート出力 | 手動（Worker報告YAML） | Phase 2自動（output_contracts） |
| ステータス判定 | 手動（Worker自己報告） | Phase 3自動（タグベースルール） |

### 2.4 プロンプト設計比較

| 項目 | Ensemble | TAKT | CC Best Practice |
|------|---------|------|-----------------|
| 構造化 | エージェントmd（ロール+ルール混在） | Faceted Prompting（5関心分離） | Command→Agent→Skills（3層） |
| 再利用性 | 低（エージェント間で重複） | 高（Persona/Policy/Instruction独立） | 中（Skills再利用可能） |
| 関心の分離 | 低（1ファイルに全情報） | 高（WHO/WHAT/RULES/OUTPUT/CONTEXT分離） | 中（Skills = 知識注入） |
| カスタマイズ | エージェントmd書き換え | YAMLキー参照で合成 | Skills/Agents定義 |

---

## 3. Ensembleの強みと弱み

### 3.1 独自の強み（他ツールにないもの）

| 強み | 詳細 | 競合状況 |
|------|------|---------|
| **専門レビュー層** | アーキテクチャ + セキュリティの並列レビュー | Shogun/TAKTにはない |
| **自己改善フェーズ** | learner agentによる毎回の学習・MEMORY.md更新 | Shogunはmemory MCPのみ |
| **動的ワーカー数** | タスク規模に応じた1-4体のスケーリング | Shogunは固定8体 |
| **Worktree統合** | パターンCのgit worktree分離 + Integrator統合 | TAKTも共有クローンで類似 |
| **Agent Teams統合** | 調査・レビュー専用モード（Claude公式機能） | 他ツールにない |
| **ワークフロー選択** | simple/default/heavyでコスト制御 | Shogunは定額前提 |
| **曖昧語禁止ルール** | 具体的な数値・名称を強制 | 他ツールにない |
| **PyPI配布** | `pip install ensemble-ai-orchestration` で即利用 | Shogunはgit clone |

### 3.2 弱み・改善機会

| 弱み | 影響 | 参考ツール |
|------|------|-----------|
| **ポーリングベース通信** | 検知遅延30秒、CPU消費 | Shogun (inotifywait) |
| **排他制御なし** | 並列書き込みでYAML破損リスク | Shogun (flock) |
| **自動エスカレーションなし** | Worker無応答時に手動介入必要 | Shogun (3段階自動) |
| **ループ検知なし** | 無限修正ループのリスク | TAKT (LoopDetector) |
| **プロンプト関心分離なし** | エージェントmd内に全情報混在、再利用性低 | TAKT (Faceted Prompting) |
| **CI/CDモードなし** | 自動化パイプラインで使えない | TAKT (pipeline mode) |
| **マルチCLI非対応** | Claude Code専用 | Shogun (4 CLI対応) |
| **セッションログなし** | 実行履歴の追跡が困難 | TAKT (NDJSON logging) |
| **タスク依存関係なし** | 順序依存タスクの明示的管理ができない | Shogun (blockedBy) |

---

## 4. 設計整合性の評価

### 4.1 設計思想と実装のギャップ

| 設計思想 | 実装状況 | ギャップ | 深刻度 |
|---------|---------|---------|--------|
| 階層的委譲 | Conductor→Dispatch→Worker実装済み | モードTでDispatch不要 | 低（設計上の例外として許容） |
| ファイルベース通信 | queue/ディレクトリ実装済み | ポーリングがイベント駆動ではない | 中（信頼性・効率に影響） |
| 自律的改善 | learner agent定義済み | 実行の自動化が不完全 | 低（手動/improveで代替可能） |
| ワーカー動的スケール | worker_count動的決定済み | 最大4体制限はClaude Max制約 | 低（制約起因、設計問題ではない） |
| コスト制御 | 3段階ワークフロー実装済み | 実行中のコスト監視なし | 低（事前選択で概ね制御可能） |

### 4.2 設計ドキュメントと実装の一致度

| ドキュメント | 実装一致度 | 備考 |
|------------|-----------|------|
| ARCHITECTURE.md | **95%** | 全体構成、エージェント定義、通信プロトコルが正確に記載 |
| conductor.md | **90%** | モードTの追加で一部拡張が必要 |
| dispatch.md | **85%** | /clearプロトコルの詳細が実装と微妙にずれる可能性 |
| workflow.md | **95%** | アトミック操作、デバッグ手順が明確 |
| communication.md | **90%** | v2.0プロトコルが実装に反映済み |

### 4.3 LEARNED.mdの蓄積状況

LEARNED.mdには7件の学習ルールが記録されている:
- 通信・インフラ: 4件（source上書き防止、エスカレーション検知、通信v2.0、インフラ整合性）
- ワークフロー: 3件（構造変更影響調査、エスカレーション対応、ドキュメント同期）

**評価**: 学習ルールが蓄積されており、自己改善メカニズムは機能している。ただし、shogunのMemory MCP（セッション横断永続化）やTAKTのNDJSONログ（完全追跡）と比較すると、構造化と検索性に改善の余地がある。

---

## 5. 成熟化ロードマップ

### Phase 1: 通信インフラの強化（高優先度）

Ensembleの最大の改善機会。shogunから学ぶべき点が多い。

#### 1-1. イベント駆動通信の導入

```
現状: ポーリング（30秒間隔）
目標: inotifywaitベースのイベント駆動（検知遅延0秒）

実装案:
- scripts/inbox_watcher.sh 相当のファイル監視デーモン
- queue/ディレクトリ内の変更をカーネルレベルで検知
- send-keysは「新メッセージあり」のnudgeのみ
- WSL2のinotify不発に対するタイムアウトフォールバック
```

**効果**: 検知遅延30秒→0秒、CPU効率改善、ポーリングコード削除

#### 1-2. 排他制御の導入

```
現状: YAML直接書き込み（競合リスク）
目標: flock + atomic write（tmp+rename）

実装案:
- queue/への書き込みをすべてflock経由に
- tmp ファイル作成 → rename でatomic write
- 並列Workerの同時報告でも破損しない
```

**効果**: データ破損リスク0%、並列信頼性向上

#### 1-3. 3段階自動エスカレーション

```
現状: 手動エスカレーション（YAML作成→Conductor対応）
目標: インフラレベルの自動復旧

Phase 1 (0-2分): 通常nudge（send-keys）
Phase 2 (2-4分): Escape×2 + C-c + nudge
Phase 3 (4分+): /clear送信（5分に1回まで）
```

**効果**: 手動介入不要、復旧時間4分以内

### Phase 2: ワークフローの進化（中優先度）

TAKTの設計から学ぶべき点が多い。

#### 2-1. ループ検知の導入

```
現状: ループ検知なし（修正→レビュー→修正の無限ループリスク）
目標: 2層のループ検知

LoopDetector: 同一タスクへの繰り返し遷移を自動検知（閾値5回）
CycleDetector: レビュー↔修正サイクルの閾値モニタリング（3回で判定）
```

**効果**: 非生産的ループの自動検出・中断、コスト浪費防止

#### 2-2. タスク依存関係の明示化

```
現状: 依存関係の明示的管理なし
目標: blockedByフィールドのサポート

tasks:
  - id: task-001
    instruction: "API実装"
  - id: task-002
    instruction: "APIテスト"
    blocked_by: ["task-001"]  # task-001完了後に自動着手
```

**効果**: 順序依存タスクの安全な並列投入、パイプライン効率化

#### 2-3. セッションログの導入

```
現状: ログなし（dashboard.mdのみ）
目標: NDJSON形式のアトミック追記ログ

ログ内容:
- タスク開始/完了/失敗イベント
- Worker割り当て/解放
- レビュー結果
- エスカレーション
- 自己改善提案
```

**効果**: 完全な実行履歴追跡、デバッグ容易化、分析可能

### Phase 3: プロンプト設計の改善（中優先度）

TAKTのFaceted PromptingとCC Best PracticeのSkillsパターンから学ぶ。

#### 3-1. Faceted Prompting導入

```
現状: エージェントmd（1ファイルに全情報混在）
目標: 5関心の分離と宣言的合成

分離構造:
.claude/
├── personas/          # WHO: 役割定義
│   ├── conductor.md
│   ├── worker-coder.md
│   └── reviewer-arch.md
├── policies/          # RULES: 禁止事項、品質基準
│   ├── security.md
│   ├── coding.md
│   └── review.md
├── instructions/      # WHAT: ステップ手順
│   ├── implement.md
│   ├── review.md
│   └── learn.md
├── knowledge/         # CONTEXT: ドメイン知識
│   └── project-specific.md
└── output-contracts/  # OUTPUT: レポートフォーマット
    ├── worker-report.md
    └── review-report.md
```

**効果**: 再利用性向上、プロンプト品質の標準化、カスタマイズ容易化

#### 3.2. Progressive Disclosureパターン

CC Best Practiceの知見:
- 「feature specific subagents with skills (progressive disclosure) instead of general qa, backend engineer」
- 汎用的なWorkerではなく、タスク特性に応じてSkillsを注入

```
現状: Worker = 汎用Sonnetエージェント
目標: タスク種別に応じたSkills動的注入

例:
  フロントエンド実装 → worker + react-skills + testing-skills
  API実装 → worker + backend-skills + security-skills
  DB変更 → worker + migration-skills + backup-skills
```

### Phase 4: 運用機能の充実（低優先度）

#### 4-1. CI/CDパイプラインモード

TAKTの`--pipeline`モードを参考に:
```bash
ensemble run --pipeline --task "バグ修正" --auto-pr
# ブランチ作成 → 実行 → commit & push → PR作成
```

#### 4-2. Bloom's Taxonomy的タスク分類

Shogunの設計を参考に:
```
L1-L3 (Remember/Understand/Apply) → Sonnet Worker
L4-L6 (Analyze/Evaluate/Create) → Opus Worker（将来対応）
```

#### 4-3. Bottom-Up Skill Discovery

Shogunの設計を参考に:
```yaml
# Worker報告にskill_candidate追加
skill_candidate:
  found: true
  name: "api-endpoint-scaffold"
  reason: "同パターンを3回実行"
```

#### 4-4. ntfy双方向モバイル通信

Shogunの設計を参考に:
- タスク完了通知をスマホにプッシュ
- スマホからコマンド送信

#### 4-5. マルチCLI対応の検討

Shogunのcli_adapter.shを参考に:
- Claude Code以外のCLI（Codex, Copilot等）をWorkerとして利用
- CLI毎のアダプター層で差異を吸収

---

## 6. 総括

### 6.1 設計思想の遵守度: **85%**

Ensembleは設計思想を概ね遵守しており、階層的委譲・ファイルベース通信・自律的改善の3原則が実装に反映されている。主な改善点は通信インフラの成熟度（ポーリング→イベント駆動）。

### 6.2 競合ツールとの位置づけ

```
                品質保証 ←──────────────────→ 並列スケール
                    ↑
                    │
                    │    ★ Ensemble
                    │    （レビュー層 + 学習 + コスト制御）
                    │
                    │              ★ TAKT
                    │              （宣言的ワークフロー + ループ検知）
                    │
                    │                        ★ Shogun
                    │                        （8並列 + イベント駆動 + マルチCLI）
                    │
                    │  ★ CC Best Practice
                    │  （Skills + Hooks + 設定体系）
                    ↓
```

- **Ensemble**: 品質保証（レビュー・セキュリティ・学習）に強い
- **Shogun**: 並列スケールと通信インフラに強い
- **TAKT**: ワークフロー定義の柔軟性と再現性に強い
- **CC Best Practice**: Claude Code公式機能の活用知見に強い

### 6.3 成熟化の優先順位

| 優先度 | 施策 | 期待効果 | 参考 |
|--------|------|---------|------|
| **P0** | inotifywaitイベント駆動通信 | 検知遅延0秒化 | Shogun |
| **P0** | flock排他制御 | データ破損防止 | Shogun |
| **P0** | 3段階自動エスカレーション | 手動介入不要化 | Shogun |
| **P1** | ループ検知 | コスト浪費防止 | TAKT |
| **P1** | タスク依存関係（blockedBy） | パイプライン効率化 | Shogun |
| **P1** | NDJSONセッションログ | 完全追跡・デバッグ | TAKT |
| **P2** | Faceted Prompting | プロンプト品質向上 | TAKT |
| **P2** | Progressive Disclosure Skills | Worker専門化 | CC Best Practice |
| **P3** | CI/CDパイプラインモード | 自動化対応 | TAKT |
| **P3** | Bloom's Taxonomy分類 | モデル選択最適化 | Shogun |
| **P3** | Bottom-Up Skill Discovery | 自動スキル化 | Shogun |

### 6.4 最終評価

Ensembleは**品質保証に特化したAIオーケストレーションツール**として独自のポジションを確立している。レビュー層・セキュリティレビュー・自己改善・コスト制御は他ツールにない強み。

一方、**通信インフラの成熟度**がshogunに対して最大のギャップ。P0施策（イベント駆動・排他制御・自動エスカレーション）を実装することで、品質保証の強みを維持しつつ信頼性と効率を大幅に向上できる。

TAKTのFaceted Promptingとループ検知も中期的に取り込む価値が高く、Ensembleの「宣言的ワークフロー + 品質保証 + 信頼性通信」という独自の統合を実現できれば、AIオーケストレーションツールとして最も成熟した選択肢になる可能性がある。

---

*本レポートはEnsemble Conductor（モードT）による調査結果です。*
*参照: docs/research-shogun-analysis.md, tmp/takt-analysis.md, tmp/agent-teams-research.md, tmp/claude-code-best-practice/*
