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
- Pythonスクリプト実行時は `uv run` を使用する（例: `uv run python script.py`, `uv run pytest`）

## 実行パターン
- パターンA: 単純タスク → subagentで直接実行
- パターンB: 中規模タスク → tmux多ペインで並列実行
- パターンC: 大規模タスク → git worktreeで分離 + 各worktree内並列
- パターンD: Agent Teamsハイブリッド（実験的） → Claude Code公式Agent Teams + Ensemble計画・レビュー層

## 分割されたドキュメント

詳細なルールは `.claude/rules/` に分割されています（自動読み込み）:

| ファイル | 内容 |
|---------|------|
| `.claude/rules/workflow.md` | アトミック操作、デバッグ手順、コンパクション復帰 |
| `.claude/rules/deploy.md` | デプロイ手順 |
| `.claude/rules/communication.md` | 通信プロトコル、曖昧語禁止ルール |
| `.claude/rules/infrastructure.md` | インフラ整合性チェック、リファレンス |
| `.claude/rules/agent-teams.md` | Agent Teamsハイブリッドモード（実験的） |

学習済みルールは `MEMORY.md` を参照（Claude Code公式の自動メモリ機能と統合）。
レガシー: `LEARNED.md` も参照可（移行中）。
