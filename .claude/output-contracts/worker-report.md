# Worker Report Format

Worker完了報告は以下のYAMLフォーマットで `queue/reports/${TASK_ID}.yaml` に作成する:

```yaml
task_id: task-001
status: success  # success, failed, blocked
worker_id: 1
summary: |
  実行内容の要約。
  何を実装したか、どのような結果になったかを具体的に記載。
files_modified:
  - "変更したファイル1"
  - "変更したファイル2"
files_created:
  - "新規作成したファイル1"
errors: []  # エラーがあれば記載
test_results: |
  テスト実行結果（あれば）
completed_at: "2026-02-11T02:00:00Z"
```

## 必須フィールド

- `task_id`: タスクID（文字列）
- `status`: 実行結果（success/failed/blocked）
- `worker_id`: WorkerのID（数値）
- `summary`: 実行内容の要約（文字列、具体的に）
- `files_modified`: 変更したファイルリスト（配列）
- `errors`: エラーリスト（配列、エラーがなければ空配列）
- `completed_at`: 完了日時（ISO 8601形式）

## オプションフィールド

- `files_created`: 新規作成したファイルリスト（配列）
- `test_results`: テスト実行結果（文字列）
- `executed_by`: 代理実行した場合のWorker ID（数値）

## ステータス定義

- **success**: タスクが正常に完了
- **failed**: エラーが発生し、完了できなかった
- **blocked**: 依存関係などで実行できなかった
