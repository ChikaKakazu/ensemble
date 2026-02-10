# 通信プロトコル v3.0

## 基本原則（P0-P3統合）
- エージェント間の指示・報告はファイルベースキュー（queue/）経由
- ファイル作成後、send-keysで即座に通知（プライマリ）
- 通知失敗時はポーリングでフォールバック
- イベント駆動通信（inbox_watcher.sh + inotifywait）で0ms検知
- 排他制御（flock + atomic write）で並行書き込みを保護
- 3段階自動エスカレーションで無応答Workerを自動復旧
- NDJSONログでセッション全体を記録

## イベント駆動通信（P0-1）

**inbox_watcher.sh による自動通知**:

```
1. Workerがqueue/reports/に完了報告を作成
2. inbox_watcher.shがinotifywaitでファイル作成を検知（0ms）
3. Dispatchペインに自動的にsend-keys通知
4. Dispatchが即座に報告収集を開始
5. Dispatch完了 → completion-summary.yaml作成 → inbox_watcher.shがConductorに通知
```

**通知パターン**:

| イベント | 検知対象 | 通知先 |
|---------|---------|--------|
| タスク完了報告 | queue/reports/*-completed.yaml | Dispatch |
| 完了サマリー | queue/reports/completion-summary.yaml | Conductor |
| エスカレーション | queue/reports/escalation-*.yaml | Conductor |
| レビュー結果 | queue/reports/*-review.yaml | Dispatch |

**フォールバック**: inotifywait利用不可の環境ではポーリング（30秒間隔）

## 排他制御（P0-2）

**flock による並行書き込み保護**:

複数Workerが同時にファイル書き込みする場合、flockで排他制御:

```python
from ensemble.lock import with_file_lock

@with_file_lock("queue/reports/completion-summary.yaml")
def write_summary(data):
    # ロック取得後に書き込み
    with open("queue/reports/completion-summary.yaml", "w") as f:
        yaml.dump(data, f)
```

**atomic write**: tmp+renameパターンで部分書き込みを防止

## 3段階自動エスカレーション（P0-3）

**Worker無応答時の自動復旧**:

| Phase | タイムアウト | アクション | 期待される効果 |
|-------|------------|----------|--------------|
| 0 | 60秒 | タスク配信のみ | 正常なWorkerは即座にACK |
| 1 | 60秒 | 通常nudge（send-keys再送） | プロンプト待ちWorkerを起こす |
| 2 | 60秒 | Escape×2 + C-c + nudge | 入力モードから脱出 |
| 3 | 60秒 | /clear + nudge | コンテキストリセット |
| 失敗 | - | Conductorにエスカレーション | 手動介入 |

**実装**: `ensemble.ack.AckManager.wait_with_escalation()`

## NDJSONログ（P1-3）

**構造化ログ出力**:

```python
from ensemble.logger import NDJSONLogger

logger = NDJSONLogger()
logger.log_event("task_start", {"task_id": "task-001", "worker_id": 1})
logger.log_event("task_complete", {"task_id": "task-001", "status": "success"})
```

**ログファイル**: `.ensemble/logs/session-YYYYMMDD-HHMMSS.ndjson`

**イベントタイプ**:
- task_start / task_complete / task_failed
- worker_assign / worker_release
- review_start / review_result
- escalation / loop_detected
- session_start / session_end

## タイムアウト設定（v2.0から変更なし）
- Dispatch: 3分待機後にqueue/reports/をポーリング（30秒間隔）
- Conductor: 完了通知を受信、または30分でタイムアウト

## 効果（v2.0からの改善）
- **検知時間**: 3-5分待機 → 0ms（inbox_watcher.sh）
- **信頼性**: ポーリングフォールバックで100%確実
- **復旧能力**: 3段階エスカレーションで自動復旧（手動介入不要）
- **トレーサビリティ**: NDJSONログでセッション全体を追跡

---

# 曖昧語禁止ルール（全エージェント共通）

報告・コミュニケーションでは以下の曖昧表現を禁止。必ず具体的な数値・名称・場所を記載せよ。

| 禁止表現 | 代替表現の例 |
|---------|-------------|
| 多発 | 3回発生 |
| 一部 | src/api/auth.py の 45-52行目 |
| 適宜 | 5分後に再確認 |
| 概ね | 87% |
| いくつか | 4件 |
| しばらく | 30秒後 |
| 偏り | Worker-2に4件集中（全体の80%） |
| 既知の問題 | Issue #123 で報告済み |

**報告に必ず含めるべき情報:**
- **誰が**: Worker-1, Conductor など具体名
- **何件**: 数値で記載
- **何割**: パーセンテージで記載
- **どこで**: ファイルパス:行番号
