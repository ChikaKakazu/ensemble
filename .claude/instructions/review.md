# Review Instructions

## コードレビューフロー

1. **レビュー対象を確認**:
   - 変更されたファイルリストを取得
   - git diffで変更内容を確認

2. **レビュー実施**:
   - アーキテクチャ観点（reviewer）:
     - 設計の妥当性
     - コードの可読性
     - テストカバレッジ
   - セキュリティ観点（security-reviewer）:
     - 脆弱性チェック
     - 認証・認可の確認
     - 入力検証

3. **レビュー結果を作成**:
   - `queue/reviews/${TASK_ID}-${REVIEWER_NAME}.yaml` を作成
   - 重要度別にfindings を記載（CRITICAL/HIGH/MEDIUM/LOW）

4. **判定**:
   - CRITICAL/HIGHがある → needs_fix
   - MEDIUMのみ → approved（コメント付き）
   - 問題なし → approved

5. **結果を報告**:
   - Dispatchまたはワークフローエンジンに報告
