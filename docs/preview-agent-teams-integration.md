# Preview: Agent Teams Mode Integration

**ブランチ**: `preview/agent-teams-integration`
**ステータス**: レビュー済み・マージ可能
**変更ファイル**: 20件

---

## 1. 概要

このブランチは以下の3つの機能をEnsembleに統合する:

1. **Agent Teamsモード（調査・レビュー専用）** - Claude Code公式のAgent Teams（リサーチプレビュー）を調査・レビュータスクに活用
2. **MEMORY.md移行** - LEARNED.md から Claude Code公式の自動メモリ機能（MEMORY.md）への移行
3. **TodoWrite統合** - Workerのタスク進捗をClaude Code UIで可視化

**重要**: Agent Teamsはパターン（A/B/C）とは**別軸**のモード。コード実装には使わず、調査・レビューに特化。

---

## 2. Agent Teamsモード（調査・レビュー専用）

### 設計方針

Agent Teamsはパターン（A/B/C）とは**別軸**のモード。コード実装には使わず、以下のタスクに特化:

- **技術調査**: ライブラリ比較、アーキテクチャ検討
- **レビュー**: PR並列レビュー、セキュリティ監査
- **計画策定**: 複数の視点から計画を練る

**実装パターンとの違い**:

| 項目 | パターンA/B/C | Agent Teamsモード |
|------|---------------|-------------------|
| 目的 | コード実装 | 調査・レビュー |
| Dispatch | 使用 | 不使用 |
| queue | 使用 | 不使用 |
| 操作 | Dispatch経由 | Conductor直接 |

### ユースケース

1. **技術調査**: 複数のライブラリを並列調査して比較レポート
2. **PR並列レビュー**: セキュリティ・パフォーマンス・テストの3視点で同時レビュー
3. **アーキテクチャ検討**: 複数の設計案を並列で検証
4. **バグ調査**: 複数の仮説を並列で検証

### パターン選択基準

### 有効化

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

または `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### 実行フロー（自然言語ベース）

ConductorがTeam Leadとして直接操作。Dispatch/queue不要。

```
1. 自然言語でチーム作成:
   「Create an agent team to research X technology.
    Spawn 3 teammates to investigate different aspects.」

2. Delegate Modeを有効化（推奨）:
   Conductorを調整専用にする

3. タスクをmessage/broadcastで分配:
   各teammateに調査・レビュータスクを割り当て

4. 完了検知:
   TeammateIdleフック + 共有タスクリストで自動検知

5. チーム削除:
   「Clean up the team」

6. 結果を統合して計画/レビュー報告に反映
```

### Ensemble連携

Agent Teams実行後、結果をEnsembleのワークフローに統合:

1. 調査結果を分析
2. 計画に反映（パターン選択、技術選定）
3. レビュー結果をユーザーに報告
4. 必要に応じてパターンA/B/Cで実装開始

### Delegate Mode（推奨）

**Shift+Tab** で有効化。Conductorを調整専用に制限（コード変更禁止）。
Ensembleの「Conductor = 判断のみ、コードは書かない」思想をネイティブに実現。

- チーム作成後、Conductorペインで **Shift+Tab** を押下
- Conductorはコード変更が禁止され、調整・判断・レビュー承認のみ実行
- 実際のコード変更は全てteammatesが担当

**詳細**: `.claude/rules/agent-teams.md` 参照

### Hooks統合（品質ゲート）

Agent Teams固有のHooksをEnsembleのレビュー・品質チェックに統合。

- **TeammateIdle**: メイトがアイドル時に実行 → reviewerを自動起動
- **TaskCompleted**: タスク完了マーク時に実行 → security-reviewerでチェック

exit code 2でフィードバック送信または完了拒否が可能。

**詳細**: `.claude/rules/agent-teams.md` 参照

### 計画承認の活用

メイトに実装前の計画を要求可能（"Require plan approval"）。
Ensembleの計画重視思想と合致。

1. Teammateが計画を提出
2. Conductor（= Team Lead）が計画をレビュー
3. 承認 → 実装開始 / 却下 → 計画修正

**詳細**: `.claude/rules/agent-teams.md` 参照

### 表示モード設定

| モード | 説明 | 要件 |
|-------|------|------|
| **in-process** | メインターミナル内。Shift+Up/Downで切替 | なし |
| **split panes** | tmux/iTerm2で各メイトに独自ペイン | tmux or iTerm2 |
| **auto**（デフォルト） | tmux内ならsplit、それ以外はin-process | - |

Ensembleでは **tmux** を推奨（既にtmuxで管理しているため）。

**詳細**: `.claude/rules/agent-teams.md` 参照

---

## 3. MEMORY.md移行

### 背景

- 従来: `LEARNED.md` に学習済みルールを蓄積
- 新規: Claude Code公式の自動メモリ機能 `MEMORY.md` に統合
- `MEMORY.md` は毎ターン自動的にシステムプロンプトに注入される

### 変更内容

| 対象 | 変更 |
|------|------|
| learner.md（実・テンプレート） | 追記先を LEARNED.md → MEMORY.md に変更 |
| improve.md（実・テンプレート） | 提案・適用先を MEMORY.md に変更 |
| setup.sh（実・テンプレート） | MEMORY.md 作成処理に置換、`memory/` ディレクトリ作成 |
| CLAUDE.md | MEMORY.md参照 + LEARNED.mdレガシー注記 |

### メモリの階層

| レベル | パス | 用途 |
|--------|------|------|
| プロジェクト | `MEMORY.md` | 主要な学習済みルール（200行以内） |
| トピック別 | `memory/` 配下 | 詳細なトピック別メモ |
| レガシー | `LEARNED.md` | 移行中（参照可） |

### 移行ガイドライン

- `MEMORY.md` は200行以内に保つ（Claude Codeの制限）
- 詳細な内容は `memory/` 配下にトピック別ファイルを作成
- 時系列ではなくセマンティックに整理
- 既存の `LEARNED.md` がある場合、setup.sh が移行を促すメッセージを表示

---

## 4. TodoWrite統合

### 概要

Claude Code の `TodoWrite` ツールをWorkerのタスク進捗管理に活用。

### ルール

1. 常に **1つだけ** `in_progress` にする（複数同時進行は禁止）
2. 完了前に新しいタスクを開始しない
3. `activeForm` には進行形で記述（例: "Fixing authentication bug"）

### 位置づけ

- **UI表示用のオプション機能**（ファイルベース報告は引き続き必須）
- 通信不安定時はスキップ可

---

## 5. 変更ファイル一覧

### エージェント定義（実ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `.claude/agents/conductor.md` | Agent Teamsモード（T）追加（調査・レビュー専用） |
| `.claude/agents/dispatch.md` | パターンD削除（Agent Teamsは実装パターンではない） |
| `.claude/agents/learner.md` | MEMORY.md移行 + メモリシステム説明追加 |
| `.claude/agents/worker.md` | TodoWriteセクション追加 |

### エージェント定義（テンプレート）

| ファイル | 変更内容 |
|---------|---------|
| `src/ensemble/templates/agents/conductor.md` | Agent Teamsモード（T）追加（調査・レビュー専用） |
| `src/ensemble/templates/agents/dispatch.md` | パターンD削除 |
| `src/ensemble/templates/agents/learner.md` | MEMORY.md移行 + メモリ説明 |
| `src/ensemble/templates/agents/worker.md` | TodoWriteセクション追加 |

### コマンド

| ファイル | 変更内容 |
|---------|---------|
| `.claude/commands/improve.md` | MEMORY.md移行（+28行/-6行） |
| `src/ensemble/templates/commands/improve.md` | MEMORY.md移行（+32行/-16行） |

### スクリプト

| ファイル | 変更内容 |
|---------|---------|
| `scripts/launch.sh` | Agent Teamsモード検出・表示（調査・レビュー専用） |
| `scripts/setup.sh` | MEMORY.md作成処理・移行チェック |
| `src/ensemble/templates/scripts/launch.sh` | Agent Teamsモード検出・表示（調査・レビュー専用） |
| `src/ensemble/templates/scripts/setup.sh` | MEMORY.md作成処理 |

### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `.claude/rules/agent-teams.md` | Agent Teamsモード（T）のルール定義（調査・レビュー専用、400行超） |
| `.claude/settings.json` | AGENT_TEAMS環境変数追加 |
| `workflows/agent-teams.yaml` | Agent Teamsワークフロー定義（宣言的定義） |

### 設定

| ファイル | 変更内容 |
|---------|---------|
| `CLAUDE.md` | Agent Teamsモード（T）追記・MEMORY.md参照追加 |

---

## 6. レビュー所見

### 確認済み（問題なし）

- [x] 設計の明確化: Agent Teamsを「調査・レビュー専用モード」として再定義
- [x] MEMORY.md移行: 18ファイル全てで参照先を正しく更新
- [x] 実装との分離: コード実装はパターンA/B/C、調査・レビューはAgent Teamsモード（T）
- [x] 後方互換性: LEARNED.mdレガシー対応あり
- [x] セキュリティ: 秘密情報の混入なし

### 更新完了事項（task-017～task-020）

| 項目 | 内容 |
|------|------|
| ✅ 公式仕様との同期 | API表記（TeamCreate等）を削除し、自然言語ベースに書き換え（task-017/018） |
| ✅ モード再定義 | 「パターンD」→「Agent Teamsモード（T）」調査・レビュー専用に再定義（task-019/020） |
| ✅ Delegate Mode追加 | Conductorを調整専用に制限する機能を統合 |
| ✅ Hooks統合 | TeammateIdle/TaskCompletedフックで品質ゲートを実装 |
| ✅ 計画承認追加 | Require plan approvalで実装前のレビューを可能に |
| ✅ 表示モード追加 | in-process/split panes/autoの設定方法を記載 |
| ✅ 制約事項拡充 | 公式9項目の制約事項を全て記載 |

### 残存する注意点

| 重要度 | 内容 |
|--------|------|
| INFO | Agent Teamsはリサーチプレビュー機能。仕様変更の可能性あり |
| INFO | workflows/agent-teams.yamlは宣言的定義。パースするランタイムコードは未実装（他workflowも同様） |
| INFO | テンプレート版は簡略版。詳細は実ファイル（.claude/agents/）および .claude/rules/agent-teams.md を参照 |

---

## 7. 制約事項（公式）

Agent Teamsの公式制約事項を全て記載（2025年2月時点）:

1. **セッション再開不可**: `/resume`でin-processメイトは復元されない
2. **タスクステータスのラグ**: メイトがタスク完了マークを忘れることがある
3. **シャットダウンが遅い**: メイトは現在のリクエスト完了を待つ
4. **1セッション1チーム**: 新チーム前にクリーンアップ必須
5. **ネスト不可**: メイトは自分のチーム/メイトを作れない
6. **リーダー固定**: チーム作成セッションがリーダー
7. **権限はスポーン時に継承**: 後から個別変更は可能だがスポーン時には不可
8. **splitペインはtmux/iTerm2必須**: VS Code、Windows Terminal、Ghostty非対応
9. **仕様変更の可能性**: リサーチプレビュー機能のため、将来の仕様変更あり

**Ensemble特有の注意点**:
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` の設定が必要（デフォルトは無効）
- 従来のパターンB（tmux並列）は常にフォールバックとして利用可能
- Delegate Modeの活用を推奨（Conductorを調整専用に）
- Hooksで品質ゲートを実装（TeammateIdle/TaskCompleted）

**詳細**: `.claude/rules/agent-teams.md` 参照
