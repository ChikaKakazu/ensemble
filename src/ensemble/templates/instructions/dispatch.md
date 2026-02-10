# Dispatch Instructions

## タスク配信フロー

1. **Conductorからの指示を受領**:
   - `queue/conductor/dispatch-instruction.yaml` を確認

2. **タスクを各Workerに配信**:
   - Worker数を確認（.ensemble/panes.env から WORKER_COUNT を取得）
   - 各Workerに1タスクずつ配信
   - `queue/tasks/worker-N-task.yaml` を作成

3. **Workerに通知**（2回分割 + ペインID）:
   ```bash
   source .ensemble/panes.env
   tmux send-keys -t "$WORKER_N_PANE" 'queue/tasks/worker-N-task.yaml を確認してください'
   tmux send-keys -t "$WORKER_N_PANE" Enter
   ```

4. **ACK待機**（3段階エスカレーション）:
   - Phase 1 (0-2分): 通常待機
   - Phase 2 (2-4分): Escape×2 + C-c + nudge
   - Phase 3 (4分+): /clear送信

5. **完了報告を収集**:
   - `queue/reports/` をポーリングまたはsend-keys通知で検知
   - 全Worker完了を待つ

6. **completion-summary.yaml作成**:
   - 全Workerの結果を集約
   - status: success/partial/failed を設定

7. **Conductorに通知**（2回分割 + ペインID）:
   ```bash
   source .ensemble/panes.env
   tmux send-keys -t "$CONDUCTOR_PANE" '全タスク完了。completion-summary.yamlをご確認ください'
   tmux send-keys -t "$CONDUCTOR_PANE" Enter
   ```

## エスカレーション対応

- ACKタイムアウト → 3段階エスカレーション自動実行
- Worker失敗 → Conductorに報告、判断を仰ぐ
