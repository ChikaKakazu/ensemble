# Review Report Format

レビュー結果は以下のYAMLフォーマットで `queue/reviews/${TASK_ID}-${REVIEWER_NAME}.yaml` に作成する:

```yaml
task_id: task-001
reviewer: reviewer-arch  # reviewer-arch, reviewer-security など
status: approved  # approved, needs_fix
summary: |
  レビュー結果の要約。
  主要な問題点や承認理由を記載。
findings:
  - severity: CRITICAL  # CRITICAL, HIGH, MEDIUM, LOW
    category: security  # security, architecture, performance, etc.
    file: "src/api/auth.py"
    line: 42
    description: "認証トークンがハードコード されています"
    recommendation: "環境変数から読み込むように修正してください"
  - severity: MEDIUM
    category: code_quality
    file: "src/api/users.py"
    line: 15
    description: "エラーハンドリングが不足しています"
    recommendation: "try-except ブロックを追加してください"
reviewed_at: "2026-02-11T02:00:00Z"
```

## 必須フィールド

- `task_id`: タスクID（文字列）
- `reviewer`: レビュアー名（文字列）
- `status`: レビュー結果（approved/needs_fix）
- `summary`: レビュー結果の要約（文字列）
- `findings`: 発見事項リスト（配列）
- `reviewed_at`: レビュー日時（ISO 8601形式）

## Finding フォーマット

- `severity`: 重要度（CRITICAL/HIGH/MEDIUM/LOW）
- `category`: カテゴリ（security/architecture/performance/code_quality など）
- `file`: 対象ファイル（文字列）
- `line`: 対象行番号（数値、オプション）
- `description`: 問題の説明（文字列）
- `recommendation`: 推奨対応（文字列）

## ステータス定義

- **approved**: レビュー通過（MEDIUMレベル以下の問題のみ、またはなし）
- **needs_fix**: 修正が必要（CRITICAL または HIGH の問題あり）
