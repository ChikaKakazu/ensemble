# プロジェクト: Ensemble AI Orchestration

## 概要
このプロジェクトはEnsemble AIオーケストレーションシステムを使用しています。

## 作業再開プロトコル
1. `PROGRESS.md` を読み、現在のフェーズと次のアクションを確認
2. `PLAN.md` で詳細な計画を確認
3. 作業開始

## 基本ルール
- /go コマンドでタスクを開始する
- /go-light で軽量ワークフロー（コスト最小）
- 実行パターンはConductorが自動判定する
- 自己改善フェーズを必ず実行する

## ⚠️ コンパクション復帰プロトコル（全エージェント必須）

コンパクション後は、作業を再開する前に**必ず**以下を実行せよ:

1. **自分のペイン名を確認する**:
   ```bash
   tmux display-message -p '#W'
   ```

2. **対応するエージェント定義を読み直す**:
   - conductor → `.claude/agents/conductor.md`
   - dispatch → `.claude/agents/dispatch.md`
   - reviewer → `.claude/agents/reviewer.md`
   - （その他、自分の役割に対応するファイル）

3. **禁止事項を確認してから作業開始**

4. **現在のタスクをダッシュボードで確認**:
   ```bash
   cat status/dashboard.md
   ```

summaryの「次のステップ」を見てすぐ作業してはならぬ。
**まず自分が誰かを確認せよ。**

## 通信プロトコル
- エージェント間の指示・報告はファイルベースキュー（queue/）経由
- send-keysは「新タスクあり」の通知のみに使用
- ACKファイルで受領確認を行う

## 実行パターン
- パターンA: 単純タスク → subagentで直接実行
- パターンB: 中規模タスク → tmux多ペインで並列実行
- パターンC: 大規模タスク → git worktreeで分離 + 各worktree内並列

## 学習済みルール（自動追記）
<!-- learner agentが自動追記するセクション -->

