# Agent Teams ハイブリッドモード（実験的）

## 概要

Claude Code公式の Agent Teams（リサーチプレビュー）とEnsembleのハイブリッド統合。
環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 設定時に利用可能。

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
|     通信・実行層（Agent Teams で置き換え可能）       |
|                                                     |
|  [従来モード]          [Agent Teamsモード]           |
|  Dispatch + Workers    TeamCreate + SendMessage     |
|  ファイルキュー         自動メッセージ配信            |
|  send-keys通知          idle通知自動                 |
|  panes.env管理          config.json自動管理          |
+---------------------------------------------------+
                      |
                      v
+---------------------------------------------------+
|         Ensemble レビュー・改善層（維持）            |
|                                                     |
|  Reviewer / Security-Reviewer / Learner             |
+---------------------------------------------------+
```

## パターンD: Agent Teams実行

### 有効化条件

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### 判定基準

パターンDはパターンBの代替として選択可能:
- 変更ファイル数 4〜10
- 並列可能な作業あり
- Agent Teams環境変数が有効

### 実行フロー

```
1. Conductor が計画を立案（従来通り）
2. TeamCreate でチームを作成:
   {
     "team_name": "ensemble-{task-id}",
     "description": "タスクの説明"
   }

3. 各タスクをTaskCreate/TaskListで登録

4. SendMessage でワーカーに直接指示:
   {
     "type": "message",
     "recipient": "worker-1",
     "content": "タスク内容",
     "summary": "タスク概要"
   }

5. ワーカーはタスク完了後にTaskUpdateで完了マーク

6. Conductor がTaskListで完了確認

7. TeamDelete でクリーンアップ
```

### Ensemble独自の追加プロトコル

Agent Teams利用時も以下はEnsemble独自で維持:

1. **計画立案**: Conductorが計画を立て、ユーザー承認を得る
2. **ワークフロー選択**: simple/default/heavy のコスト管理
3. **レビュー**: reviewer/security-reviewer による品質チェック
4. **自己改善**: learnerによるMEMORY.md更新
5. **ダッシュボード**: status/dashboard.md の更新（Agent Teamsと並行）
6. **完了報告**: queue/reports/ へのファイル出力（Agent Teamsと並行）

### 従来モードとの切り替え

```
dispatch-instruction.yaml の pattern フィールドで切り替え:

pattern: B      # 従来のtmux並列（Dispatch + Workers）
pattern: D      # Agent Teams ハイブリッド
pattern: auto   # 環境変数に基づいて自動選択
```

### 制約事項

- Agent Teamsはリサーチプレビューのため、仕様変更の可能性あり
- 従来モード（パターンB）は常にフォールバックとして利用可能
- Agent Teams障害時は自動的にパターンBにフォールバック

## SendMessage vs send-keys 比較

| 項目 | send-keys（従来） | SendMessage（Agent Teams） |
|------|-------------------|---------------------------|
| 信頼性 | ファイル+通知の2段構え | 自動配信（キュー付き） |
| 遅延 | 2秒間隔の手動管理 | 自動（ターン終了時配信） |
| エラー検知 | ポーリング必須 | idle通知で自動検知 |
| コンテキスト | /clear手動管理 | in-process自動管理 |
| 可視性 | tmuxペインで直接確認 | UI通知 + TaskList |
