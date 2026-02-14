---
description: |
  軽量版。README更新やtypo修正など軽微な変更向け。
  simpleワークフローを使用し、コストを最小化する。
---

以下のタスクをsimpleワークフロー（軽量）で実行してください。

## タスク

$ARGUMENTS

## 制約

- **simpleワークフローを使用**（レビュー1回、修正ループなし）
- **tmux並列・worktree分離は使わない**（パターンAのみ）
- **自己改善フェーズは省略可**

## 実行手順

### 1. 簡易計画

- タスクの内容を確認
- 変更対象ファイルを特定
- 変更が軽微であることを確認（重要な変更なら `/go` を使うよう提案）

### 2. Dispatch経由で実行

- パターンAと同じ手順でDispatch経由でWorkerに委譲する:
  1. `queue/conductor/dispatch-instruction.yaml` に指示を書く（workflow: simple, pattern: A）
  2. Dispatchに通知:
     ```bash
     source .ensemble/panes.env
     tmux send-keys -t "$DISPATCH_PANE" '新しい指示があります。queue/conductor/dispatch-instruction.yaml を確認してください'
     tmux send-keys -t "$DISPATCH_PANE" Enter
     ```
  3. 完了報告を待機
- **注意: go-lightでも自分で実装してはならない。必ずDispatch経由。**

### 3. 簡易レビュー

- 変更内容を1回確認
- 明らかな問題がなければ完了

### 4. 完了報告

- 変更ファイルの一覧
- 変更内容の簡単な説明

## 注意事項

- このコマンドは軽微な変更専用
- 以下の場合は `/go` を使用:
  - 新機能の実装
  - 複数ファイルにまたがる変更
  - セキュリティに関わる変更
  - アーキテクチャに影響する変更
