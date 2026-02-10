# Implement Instructions (Worker)

## タスク実行フロー

1. **自分のWorker IDを確認**:
   ```bash
   echo $WORKER_ID
   ```

2. **タスクYAMLを読み込む**:
   - `queue/tasks/worker-${WORKER_ID}-task.yaml` を確認
   - タスクが存在しない → 待機
   - タスクが存在する → 次のステップへ

3. **ACKファイルを作成**（受領確認）:
   ```bash
   echo "ack" > queue/ack/${TASK_ID}.ack
   ```

4. **タスクを実行**:
   - 参照ファイルを全て読む
   - 実装を行う
   - テストを実行
   - 結果を確認

5. **完了報告を作成**:
   - `queue/reports/${TASK_ID}.yaml` を作成
   - status: success/failed/blocked を設定

6. **Dispatchに通知**（2回分割 + ペインID）:
   ```bash
   source .ensemble/panes.env
   tmux send-keys -t "$DISPATCH_PANE" 'タスク${TASK_ID}完了'
   tmux send-keys -t "$DISPATCH_PANE" Enter
   ```

7. **待機**:
   - 「タスク完了。待機中。」と表示
   - 処理を停止し、次の入力を待つ

## エラー発生時の対応

1. エラー内容を完了報告に記載
2. status を failed に設定
3. Dispatchに報告
4. 自分で解決しようとしない（Conductorにエスカレーション）

## subagent活用

- ファイル数 >= 3 かつ依存関係が低い → subagent並列実行を検討
- 各subagentの結果を集約して確認
- エラーが発生した場合は順次実行に切り替え
