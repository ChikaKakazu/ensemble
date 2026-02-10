# Completion Summary Format

全タスク完了報告は以下のYAMLフォーマットで `queue/completion-summary.yaml` に作成する:

```yaml
session_id: session-20260211-020000
status: success  # success, partial, failed
total_tasks: 3
completed_tasks: 3
failed_tasks: 0
summary: |
  全タスクが正常に完了しました。

  実装内容:
  - task-001: ユーザー認証APIを実装（Worker-1）
  - task-002: ユーザーAPIのテストを作成（Worker-2）
  - task-003: ドキュメント更新（Worker-1）
task_results:
  - task_id: task-001
    worker_id: 1
    status: success
    files_modified: ["src/api/auth.py", "tests/test_auth.py"]
  - task_id: task-002
    worker_id: 2
    status: success
    files_modified: ["tests/test_users.py"]
  - task_id: task-003
    worker_id: 1
    status: success
    files_modified: ["README.md"]
errors: []
completed_at: "2026-02-11T02:00:00Z"
```

## 必須フィールド

- `session_id`: セッションID（文字列）
- `status`: 全体ステータス（success/partial/failed）
- `total_tasks`: 総タスク数（数値）
- `completed_tasks`: 完了タスク数（数値）
- `failed_tasks`: 失敗タスク数（数値）
- `summary`: 全体の要約（文字列）
- `task_results`: 各タスクの結果リスト（配列）
- `errors`: エラーリスト（配列）
- `completed_at`: 完了日時（ISO 8601形式）

## ステータス定義

- **success**: 全タスクが正常に完了
- **partial**: 一部タスクが失敗したが、継続可能
- **failed**: 重大な失敗があり、全体が失敗
