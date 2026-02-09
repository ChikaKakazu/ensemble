# Preview: Agent Teams Integration

**ブランチ**: `preview/agent-teams-integration`
**ステータス**: レビュー済み・マージ可能
**コミット**: 2件 / **変更ファイル**: 18件（+534行, -67行）

---

## 1. 概要

このブランチは以下の3つの機能をEnsembleに統合する:

1. **Agent Teams ハイブリッドモード（パターンD）** - Claude Code公式のAgent Teams（リサーチプレビュー）をEnsembleの実行層に統合
2. **MEMORY.md移行** - LEARNED.md から Claude Code公式の自動メモリ機能（MEMORY.md）への移行
3. **TodoWrite統合** - Workerのタスク進捗をClaude Code UIで可視化

---

## 2. Agent Teams ハイブリッドモード（パターンD）

### 設計方針

Ensembleの3層アーキテクチャを維持しつつ、**通信・実行層のみ**をAgent Teamsで置き換える。

```
+---------------------------------------------------+
|         Ensemble 計画・判断層（維持）                |
|  Conductor (Opus)                                   |
|    - タスク計画・分解                                |
|    - ワークフロー選択                                |
|    - 最終判断・レビュー統括                          |
+---------------------------------------------------+
                      |
                      v
+---------------------------------------------------+
|     通信・実行層（Agent Teams で置き換え）           |
|                                                     |
|  [従来: パターンB]        [新規: パターンD]          |
|  Dispatch + Workers       TeamCreate + SendMessage  |
|  ファイルキュー            自動メッセージ配信         |
|  send-keys通知             idle通知自動              |
+---------------------------------------------------+
                      |
                      v
+---------------------------------------------------+
|         Ensemble レビュー・改善層（維持）            |
|  Reviewer / Security-Reviewer / Learner             |
+---------------------------------------------------+
```

### パターン選択基準

| パターン | 条件 | 通信方式 |
|---------|------|---------|
| A | ファイル数 <= 3、単純タスク | subagent直接 |
| B | ファイル数 4-10、並列あり | tmux + send-keys |
| C | ファイル数 > 10、独立機能 | git worktree |
| **D（新規）** | パターンBと同条件 + `AGENT_TEAMS=1` | Agent Teams API |

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

```
1. Conductor が計画を立案（従来通り）

2. 自然言語でチーム作成を指示:
   「ensemble-{task-id}というチームを作成し、N人のteammateをspawnしてください」
   ※ API呼び出しではなく、自然言語での指示が基本

3. Delegate Modeを有効化（Shift+Tab）:
   Conductorを調整専用にし、実装はteammateに委譲

4. タスクをmessage/broadcastで分配:
   各teammateに個別にタスクを割り当て

5. TeammateIdleフック + 共有タスクリストで完了検知:
   自動的にタスク完了を検知

6. チーム削除を指示:
   「チームを削除してください」

7. レビュー・改善フェーズは従来通り（Ensemble独自プロトコル）
```

### フォールバック

Agent Teams利用中に問題が発生した場合:
1. `TeamDelete` で現在のチームをクリーンアップ
2. パターンB（Dispatch + Workers）にフォールバック
3. 中断したタスクを従来方式で再実行

### ワークフロー定義

`workflows/agent-teams.yaml` で6フェーズを定義:

| Phase | 担当 | 内容 |
|-------|------|------|
| plan | Conductor (Opus) | タスク分析・分解・ワークフロー選択・ユーザー承認 |
| execute | Agent Teams | チーム作成・ワーカーspawn・タスク配信・完了待機 |
| review | Reviewer + Security (並列) | アーキテクチャレビュー + セキュリティレビュー |
| fix_loop | Agent Teams | 修正指示・再レビュー（最大3イテレーション） |
| cleanup | Conductor | チーム削除・ダッシュボード更新・完了報告 |
| improve | Learner (Sonnet) | 実行分析・MEMORY.md更新提案 |

### SendMessage vs send-keys

| 項目 | send-keys（従来） | SendMessage（Agent Teams） |
|------|-------------------|---------------------------|
| 信頼性 | ファイル+通知の2段構え | 自動配信（キュー付き） |
| 遅延 | 2秒間隔の手動管理 | 自動（ターン終了時配信） |
| エラー検知 | ポーリング必須 | idle通知で自動検知 |
| コンテキスト | /clear手動管理 | in-process自動管理 |
| 可視性 | tmuxペインで直接確認 | UI通知 + TaskList |

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
| `.claude/agents/conductor.md` | パターンD判定基準・実行方法・フォールバック追加（+41行） |
| `.claude/agents/dispatch.md` | パターンD時の役割分担追加（+28行） |
| `.claude/agents/learner.md` | MEMORY.md移行 + メモリシステム説明追加（+38行/-8行） |
| `.claude/agents/worker.md` | TodoWriteセクション追加（+31行） |

### エージェント定義（テンプレート）

| ファイル | 変更内容 |
|---------|---------|
| `src/ensemble/templates/agents/conductor.md` | パターンD追加（簡略版、+27行） |
| `src/ensemble/templates/agents/dispatch.md` | パターンD追加（簡略版、+11行） |
| `src/ensemble/templates/agents/learner.md` | MEMORY.md移行 + メモリ説明（+27行/-7行） |
| `src/ensemble/templates/agents/worker.md` | TodoWriteセクション追加（例なし、+20行） |

### コマンド

| ファイル | 変更内容 |
|---------|---------|
| `.claude/commands/improve.md` | MEMORY.md移行（+28行/-6行） |
| `src/ensemble/templates/commands/improve.md` | MEMORY.md移行（+32行/-16行） |

### スクリプト

| ファイル | 変更内容 |
|---------|---------|
| `scripts/launch.sh` | Agent Teamsモード検出・表示（+20行/-1行） |
| `scripts/setup.sh` | MEMORY.md作成処理・移行チェック（+33行/-9行） |
| `src/ensemble/templates/scripts/launch.sh` | Agent Teamsモード検出・表示（+20行/-1行） |
| `src/ensemble/templates/scripts/setup.sh` | MEMORY.md作成処理（+26行/-7行） |

### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `.claude/rules/agent-teams.md` | Agent Teamsハイブリッドモードのルール定義（117行） |
| `.claude/settings.json` | AGENT_TEAMS環境変数追加（+3行） |
| `workflows/agent-teams.yaml` | Agent Teamsワークフロー定義（94行） |

### 設定

| ファイル | 変更内容 |
|---------|---------|
| `CLAUDE.md` | パターンD追記・MEMORY.md参照追加（+5行/-1行） |

---

## 6. レビュー所見

### 確認済み（問題なし）

- [x] 設計の一貫性: 3層構造を維持しつつAgent Teamsを実行層に統合
- [x] MEMORY.md移行: 18ファイル全てで参照先を正しく更新
- [x] フォールバック: パターンBへの自動フォールバックを明記
- [x] 後方互換性: LEARNED.mdレガシー対応あり
- [x] セキュリティ: 秘密情報の混入なし

### 更新完了事項（task-017/task-018）

| 項目 | 内容 |
|------|------|
| ✅ 公式仕様との同期 | API表記（TeamCreate等）を削除し、自然言語ベースに書き換え |
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
