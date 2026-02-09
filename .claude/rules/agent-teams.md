# Agent Teams ハイブリッドモード（実験的）

## 概要

Claude Code公式の **Agent Teams**（リサーチプレビュー）とEnsembleのハイブリッド統合。
**Agent Teams**は、複数のClaude Codeインスタンスをチームとして協調させる実験的機能。
1つのセッションが**Team Lead**として機能し、他の**Teammates**にタスクを分配・調整する。

**重要**: Agent Teamsはリサーチプレビュー機能であり、仕様変更の可能性がある。
従来モード（パターンB: Dispatch + Workers）は常にフォールバックとして利用可能。

### 有効化

環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 設定時に利用可能:

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

### Subagents vs Agent Teams

| 項目 | Subagents | Agent Teams |
|------|-----------|-------------|
| **コンテキスト** | 独自ウィンドウ、結果は呼び出し元に返る | 独自ウィンドウ、完全に独立 |
| **通信** | メインエージェントにのみ報告 | チームメイト同士が直接メッセージ可能 |
| **調整** | メインが全管理 | 共有タスクリストで自己調整 |
| **最適ケース** | 結果だけ欲しい集中タスク | 議論・協調が必要な複雑タスク |
| **トークンコスト** | 低い（結果要約で返す） | 高い（各メイトが独立Claude） |

**判断基準**: ワーカー同士が通信する必要があるか？
- NO → Subagents
- YES → Agent Teams

---

## アーキテクチャ

```
+---------------------------------------------------+
|         Ensemble 計画・判断層（維持）                |
|                                                     |
|  Conductor (Opus)                                   |
|    - タスク計画・分解                                |
|    - ワークフロー選択                                |
|    - 最終判断・レビュー統括                          |
|    - 自己改善（learner委譲）                         |
+---------------------------------------------------+
                      |
                      v
+---------------------------------------------------+
|     実行層（Agent Teams で置き換え）                |
|                                                     |
|  [従来モード]          [Agent Teamsモード]           |
|  Dispatch + Workers    Team Lead（自然言語指示）     |
|  ファイルキュー         共有タスクリスト              |
|  send-keys通知          TeammateIdle自動通知         |
|  panes.env管理          ~/.claude/teams/管理        |
+---------------------------------------------------+
                      |
                      v
+---------------------------------------------------+
|         Ensemble レビュー・改善層（維持）            |
|                                                     |
|  Reviewer / Security-Reviewer / Learner             |
+---------------------------------------------------+
```

### Agent Teams コンポーネント

| コンポーネント | 役割 |
|--------------|------|
| **Team lead** | メインセッション（= Conductor）。チーム作成・タスク分配・結果統合 |
| **Teammates** | 独立Claude Codeインスタンス。割り当てられたタスクを実行 |
| **Task list** | 共有タスクリスト（`~/.claude/tasks/{team-name}/`）。依存関係を自動管理 |
| **Mailbox** | エージェント間メッセージング（message/broadcast） |

### ストレージ

```
~/.claude/teams/{team-name}/config.json   # チーム設定
~/.claude/tasks/{team-name}/              # タスクリスト
```

---

## パターンD: Agent Teams実行

### 判定基準

パターンDはパターンBの代替として選択可能:
- 変更ファイル数 4〜10
- 並列可能な作業あり
- Agent Teams環境変数が有効（`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`）
- ワーカー同士の協調が必要（オプション）

### 実行フロー（自然言語ベース）

Agent Teamsは**自然言語で指示**する。API的な呼び出しではない。

```
1. Conductor が計画を立案（従来通り）
   - タスク分解
   - ワークフロー選択
   - ユーザー承認

2. Conductor（= Team Lead）が自然言語でチーム作成:
   例: 「Create an agent team to implement these 3 features in parallel.
        Use Sonnet for each teammate.」

3. Delegate Modeを有効化（推奨）:
   - Shift+Tab を押下
   - Conductorを調整専用に制限（コード変更禁止）
   - Ensembleの「Conductor = 判断のみ」思想と合致

4. 各teammateにタスクを割り当て:
   - 自然言語で指示: 「Implement authentication module in src/auth.py. Require plan approval before making changes.」
   - 共有タスクリスト（~/.claude/tasks/）に自動登録
   - 計画承認を要求（Require plan approval）すると、実装前に計画レビュー可能

5. teammateはタスクを実行:
   - 各teammateが独立して作業
   - 完了後、タスクに完了マーク（自動 or 手動）
   - ファイルロックで競合防止

6. 完了検知:
   - TeammateIdleフック: メイトがアイドルになる時に実行
   - TaskCompletedフック: タスク完了マーク時に実行
   - 共有タスクリストを監視

7. クリーンアップ:
   - 自然言語で指示: 「Clean up the team」
   - 全メイトをシャットダウンしてからクリーンアップ

8. レビュー・改善フェーズ（Ensemble独自）:
   - reviewer/security-reviewer によるコードレビュー
   - learnerによるMEMORY.md更新
```

### チーム作成の具体例

```
# Conductorの指示例（自然言語）
Create an agent team named "ensemble-task-017" with 3 teammates.
Each teammate should be based on the worker agent definition in .claude/agents/worker.md.
Use Sonnet model for all teammates.
Enable delegate mode to restrict my role to coordination only.
```

### タスク割り当ての具体例

```
# メイト1への指示（message: 1人宛）
Implement authentication module in src/auth.py.
Require plan approval before making any changes.
Follow test-driven development: write tests first, then implement.

# 全メイトへの指示（broadcast: 全員宛）
All teammates: Follow the coding standards in .claude/rules/.
```

---

## Ensemble独自の追加プロトコル

Agent Teams利用時も以下はEnsemble独自で維持:

1. **計画立案**: Conductorが計画を立て、ユーザー承認を得る
2. **ワークフロー選択**: simple/default/heavy のコスト管理
3. **レビュー**: reviewer/security-reviewer による品質チェック
4. **自己改善**: learnerによるMEMORY.md更新
5. **ダッシュボード**: status/dashboard.md の更新（Agent Teamsと並行）
6. **完了報告**: queue/reports/ へのファイル出力（Agent Teamsと並行）

---

## Delegate Mode（推奨）

**Shift+Tab** で有効化。リードを調整専用に制限（コード変更禁止）。
Ensembleの「Conductor = 判断のみ、コードは書かない」思想をネイティブに実現。

### 使用手順

1. チーム作成後、Conductorペインで **Shift+Tab** を押下
2. Delegate Modeが有効になり、Conductorはコード変更が禁止される
3. Conductorは調整・判断・レビュー承認のみ実行
4. 実際のコード変更は全てteammatesが担当

### メリット

- Ensembleの設計思想と完全に一致
- トークンコストの削減（Conductorがコード変更を試みない）
- 役割の明確化（判断 vs 実装の分離）

---

## Hooks統合（品質ゲート）

Agent Teams固有のHooksをEnsembleのレビュー・品質チェックに統合。

### TeammateIdle フック

メイトがアイドルになる時に実行。exit code 2でフィードバック送信。

**使用例（Ensembleでの活用）**:
- アイドル検知 → 即座にreviewerエージェントを起動
- コードレビュー実施
- 問題があればフィードバックを送信（exit code 2）
- メイトはフィードバックを受け取り、修正

### TaskCompleted フック

タスク完了マーク時に実行。exit code 2で完了を拒否。

**使用例（Ensembleでの活用）**:
- 完了マーク → security-reviewerエージェントを起動
- セキュリティチェック実施
- 脆弱性があれば完了を拒否（exit code 2）
- メイトは修正してから再度完了マーク

### 設定例

```bash
# .claude/hooks/TeammateIdle
#!/bin/bash
# メイトがアイドル時にレビューを自動実行
uv run ensemble review --worker $TEAMMATE_ID
exit $?
```

---

## 計画承認の活用

メイトに実装前の計画を要求可能。Ensembleの計画重視思想と合致。

### 指示例

```
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
```

### フロー

1. Teammateが計画を提出
2. Conductor（= Team Lead）が計画をレビュー
3. 承認 → 実装開始
4. 却下 → 計画を修正して再提出

### メリット

- 実装前の方向性確認
- 手戻りの削減
- Conductorの判断機会の明示化

---

## 表示モード設定

| モード | 説明 | 要件 |
|-------|------|------|
| **in-process** | メインターミナル内。Shift+Up/Downで切替 | なし |
| **split panes** | tmux/iTerm2で各メイトに独自ペイン | tmux or iTerm2 |
| **auto**（デフォルト） | tmux内ならsplit、それ以外はin-process | - |

### 設定方法

`.claude/settings.json`:

```json
{
  "teammateMode": "in-process"  // or "tmux" or "auto"
}
```

Ensembleでは **tmux** を推奨（既にtmuxで管理しているため）。

---

## 従来モードとの切り替え

`dispatch-instruction.yaml` の `pattern` フィールドで切り替え:

```yaml
pattern: B      # 従来のtmux並列（Dispatch + Workers）
pattern: D      # Agent Teams ハイブリッド
pattern: auto   # 環境変数に基づいて自動選択
```

Conductorが自動判定する場合:
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` が設定されている
- かつ、パターンB相当のタスク（ファイル数4〜10、並列可能）
→ パターンDを選択

---

## フォールバック

Agent Teams利用中に問題が発生した場合、自動的にパターンBにフォールバック:

### フォールバック条件

- Agent Teams環境変数が無効
- チーム作成に失敗
- タイムアウト（30分）
- TeammateのClaude起動失敗

### フォールバック手順

1. 現在のチームをクリーンアップ（`Clean up the team`）
2. パターンBにフォールバック（Dispatch + Workers）
3. 中断したタスクを従来方式で再実行
4. Conductorに原因を報告（MEMORY.md更新用）

---

## SendMessage vs send-keys 比較

| 項目 | send-keys（従来） | Agent Teams（message/broadcast） |
|------|-------------------|---------------------------|
| 信頼性 | ファイル+通知の2段構え | 自動配信（キュー付き） |
| 遅延 | 2秒間隔の手動管理 | 自動（ターン終了時配信） |
| エラー検知 | ポーリング必須 | TeammateIdle通知で自動検知 |
| コンテキスト | /clear手動管理 | 各メイトが独立管理 |
| 可視性 | tmuxペインで直接確認 | UI通知 + TaskList + tmux split panes |
| 指示方法 | コマンド実行（`tmux send-keys`） | 自然言語（`Send a message to worker-1: ...`） |

---

## 制約事項（公式）

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

---

## ベストプラクティス（公式 + Ensemble統合）

1. **十分なコンテキストを与える**: メイトはリードの会話履歴を引き継がない。スポーン時に詳細を含める
2. **タスクの適切なサイズ**: 小さすぎ→オーバーヘッド過多、大きすぎ→制御困難。1メイトあたり5-6タスクが理想
3. **メイトの完了を待つ**: リードが自分で実装し始める場合は明示的に待機指示
4. **研究・レビューから始める**: コード変更前にPRレビュー、ライブラリ調査、バグ調査から
5. **ファイル競合を避ける**: 各メイトが異なるファイルセットを担当
6. **モニタリング**: 定期的にチェックイン、うまくいかないアプローチはリダイレクト
7. **Delegate Modeを活用** (Ensemble): Conductorを調整専用に制限
8. **Hooksで品質ゲート** (Ensemble): TeammateIdle/TaskCompletedでレビュー自動化
9. **計画承認を要求** (Ensemble): 実装前に計画レビューで手戻り削減

---

## 参考: ユースケース例（公式）

### 並列コードレビュー
```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
```

### 競合仮説による調査
```
Spawn 5 agent teammates to investigate different hypotheses.
Have them talk to each other to try to disprove each other's theories.
```

---

## トラブルシューティング

| 問題 | 原因 | 解決策 |
|------|------|--------|
| チーム作成に失敗 | 環境変数未設定 | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` を確認 |
| メイトが応答しない | タスク完了マークを忘れている | 手動で完了マーク、またはタイムアウト待機 |
| ファイル競合 | 複数メイトが同じファイル編集 | タスク分解時にファイルを分離 |
| セッション再開できない | 公式制約 | パターンBで再実行 |
| 通信が遅い | in-processモードでの切替 | `teammateMode: "tmux"` に変更 |

---

*以上*
