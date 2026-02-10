# Integrate Instructions

## Worktreeマージフロー（パターンC用）

1. **全Worktreeブランチを確認**:
   ```bash
   git worktree list
   ```

2. **各ブランチを順次マージ**:
   - mainブランチに移動
   - 各Worktreeブランチをマージ
   - コンフリクト検知

3. **コンフリクト解決**:
   - 自動解決可能（import追加など）→ 自動マージ
   - 手動解決必要 → Conductorに報告

4. **統合テスト実行**:
   - 全テストを実行
   - 失敗があれば報告

5. **Worktreeクリーンアップ**:
   ```bash
   git worktree remove <path>
   ```

6. **統合結果を報告**:
   - conflict-report.yaml を作成
   - Conductorに報告
