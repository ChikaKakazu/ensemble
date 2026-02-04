---
description: |
  Ensembleのメインコマンド。タスクを渡すとConductorが
  自律的に計画・実行・レビュー・改善まで行う。

  使用例:
    /go タスク内容              - 自動判定
    /go --simple タスク内容     - パターンA強制（subagent直接）
    /go --parallel タスク内容   - パターンB強制（tmux並列）
    /go --worktree タスク内容   - パターンC強制（git worktree）
---

以下のタスクをEnsembleのConductorとして実行してください。

## 入力

$ARGUMENTS

## オプション解析

入力から以下のオプションを検出してください:

| オプション | 効果 |
|-----------|------|
| `--simple` | パターンAを強制（subagentで直接実行） |
| `--parallel` | パターンBを強制（tmux並列実行） |
| `--worktree` | パターンCを強制（git worktree分離） |
| オプションなし | タスク内容から自動判定 |

オプションが指定された場合、計画策定時のパターン判定をスキップし、指定されたパターンで実行してください。

## 実行手順

### Phase 1: 計画策定

1. **planモードに切り替え**、以下を策定:
   - タスクの全体像と成功基準
   - タスク分解（サブタスク一覧）
   - コスト見積もり → ワークフロー選択（simple/default/heavy/worktree）
   - 実行パターンの選択（オプション指定がない場合のみ自動判定）:
     - **パターンA**: 変更ファイル ≤ 3 → subagentで直接実行（takt方式）
     - **パターンB**: 変更ファイル 4〜10、並列可能 → tmux多ペイン（shogun方式）
     - **パターンC**: 機能独立、変更ファイル > 10 → git worktree分離（shogun方式）
   - 必要なskills/agents/MCPの確認

2. **計画をユーザーに確認**し、承認を得る

### Phase 2: 実行

3. パターンに応じて実行:

   **パターンA（単一Worker）**:
   - Dispatch経由でWorker1つで実行
   - Conductorは計画・判断・委譲のみ
   - 軽量タスクでも設計思想を遵守

   **パターンB（shogun方式）**:
   1. `queue/conductor/dispatch-instruction.yaml` に指示を書く
   2. `tmux send-keys -t ensemble:main.1 "新しい指示があります"` でDispatchに通知
   3. Dispatchがpane-setup.shでワーカーペインを起動
   4. 各ワーカーにタスクYAMLを配信
   5. 完了報告を待機

   **パターンC（shogun方式 + worktree）**:
   1. `queue/conductor/dispatch-instruction.yaml` に指示を書く（type: worktree）
   2. Dispatchがworktree-create.shでworktreeを作成
   3. 各worktreeでワーカーを起動
   4. 統合・相互レビュー後に完了

4. 実行中は `status/dashboard.md` を都度更新（Dispatchが担当）

### 完了待機（全パターン共通）

Dispatchへの委譲後、ポーリングで完了を待機:

```bash
# 完了待機（30秒間隔）
while [ ! -f "queue/reports/completion-summary.yaml" ]; do
  sleep 30
done
```

完了検知後:
1. completion-summary.yaml を読み込み
2. Phase 3（レビュー）へ進む

### Phase 3: レビュー

5. 全サブタスク完了後、並列レビューを実行:
   - **アーキテクチャレビュー**: コード構造、依存関係、命名規則
   - **セキュリティレビュー**: インジェクション、認証、データ保護

6. レビュー結果の集約:
   - `all("approved")` → 次のフェーズへ
   - `any("needs_fix")` → 修正ループ

### Phase 4: 自己改善

7. learner agentに委譲し、以下を実行:
   - ミスの記録とCLAUDE.md更新提案
   - Skills候補の検出
   - ワークフロー改善案

### Phase 5: 完了報告

8. 完了報告:
   - 成果物の一覧
   - 変更ファイルの一覧
   - 残課題（あれば）

## 注意事項

- Conductorは「考えるな、委譲しろ」の原則に従う
- 自分でコードを書かない
- 計画→承認→実行の順序を守る
- dashboard.mdを常に最新に保つ
