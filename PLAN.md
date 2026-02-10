# Ensemble 成熟化実装計画

**作成日**: 2025-02-11
**現在のバージョン**: 0.4.12
**参照**: docs/ensemble-design-review.md, docs/research-shogun-analysis.md

---

## 目次

1. [フェーズ概要](#1-フェーズ概要)
2. [P0: 通信インフラ強化（v0.5.0）](#2-p0-通信インフラ強化-v050)
3. [P1: ワークフロー進化（v0.6.0）](#3-p1-ワークフロー進化-v060)
4. [P2: プロンプト設計改善（v0.7.0）](#4-p2-プロンプト設計改善-v070)
5. [P3: 運用機能充実（v0.8.0）](#5-p3-運用機能充実-v080)
6. [依存関係グラフ](#6-依存関係グラフ)
7. [GitHub Issues化テンプレート](#7-github-issues化テンプレート)
8. [マイルストーン](#8-マイルストーン)

---

## 1. フェーズ概要

| フェーズ | 目的 | 期待効果 | 推定規模 | 優先度 |
|---------|------|---------|---------|--------|
| **P0: 通信インフラ強化** | shogunから学ぶ信頼性向上 | 検知遅延0秒化、CPU効率改善、手動介入不要化 | 中規模（8ファイル変更、3ファイル新規） | **最高** |
| **P1: ワークフロー進化** | TAKTから学ぶワークフロー成熟 | ループ検知、依存関係管理、実行履歴追跡 | 中規模（5ファイル変更、4ファイル新規） | 高 |
| **P2: プロンプト設計改善** | 再利用性・保守性向上 | プロンプト品質向上、カスタマイズ容易化 | 大規模（全エージェント定義を分離） | 中 |
| **P3: 運用機能充実** | 実運用向け機能拡張 | 自動化対応、モバイル通知、コスト最適化 | 小〜中規模（機能ごとに独立） | 低 |

### フェーズ間の関係

```
P0 (信頼性基盤)
    │
    ├─→ P1 (ワークフロー進化)
    │       └─→ P3-1 (CI/CD)
    │
    └─→ P2 (プロンプト設計)
            └─→ P3-2 (Skills Discovery)
```

---

## 2. P0: 通信インフラ強化（v0.5.0）

### 概要

Ensembleの最大の改善機会。shogunの通信インフラ（inotifywait、flock、3段階エスカレーション）を導入し、信頼性と効率を大幅に向上。

### 2.1 施策P0-1: イベント駆動通信の導入

#### 概要
ポーリング（30秒間隔）を廃止し、inotifywaitベースのイベント駆動通信に置き換える。

#### 背景
- **現状**: Dispatchが30秒間隔でqueue/reports/をポーリング（検知遅延30秒、CPU消費）
- **問題**: 検知遅延、CPU非効率、タスク完了時間の遅延
- **参考**: Shogun inbox_watcher.sh - カーネルレベルのファイル変更検知（検知遅延0秒、CPU 0%）

#### 変更対象ファイル
- `src/ensemble/templates/agents/dispatch.md` - ポーリングロジック削除、inotify監視追加
- `src/ensemble/templates/agents/conductor.md` - completion-summary.yaml待機をinotify監視に変更
- `.claude/agents/dispatch.md` - 同上（ローカル版）
- `.claude/agents/conductor.md` - 同上（ローカル版）

#### 新規作成ファイル
- `src/ensemble/templates/scripts/inbox_watcher.sh` - queue/ディレクトリ監視デーモン
  - `inotifywait -m -e create,modify,move queue/`
  - ファイル作成検知 → tmux send-keysで対象エージェントに通知
  - WSL2 inotify不発対策: 5秒タイムアウトフォールバック
- `src/ensemble/inbox.py` - Pythonからinotifywaitを制御するモジュール
  - subprocess経由でinbox_watcher.shを起動・管理
  - ファイル検知コールバックを登録

#### テンプレート同期
- `.claude/agents/dispatch.md` ← `src/ensemble/templates/agents/dispatch.md`
- `.claude/agents/conductor.md` ← `src/ensemble/templates/agents/conductor.md`
- `scripts/inbox_watcher.sh` ← `src/ensemble/templates/scripts/inbox_watcher.sh`（ensemble upgradeで同期）

#### 技術アプローチ

**Step 1: inbox_watcher.sh作成**
```bash
#!/bin/bash
# inotifywaitでqueue/を監視
inotifywait -m -e create,modify,move queue/ | while read path action file; do
    case "$path$file" in
        queue/reports/*.yaml)
            # Dispatchに通知
            source .ensemble/panes.env
            tmux send-keys -t "$DISPATCH_PANE" 'queue/reports/ に新しい報告があります'
            tmux send-keys -t "$DISPATCH_PANE" Enter
            ;;
        queue/reports/completion-summary.yaml)
            # Conductorに通知
            tmux send-keys -t "$CONDUCTOR_PANE" 'completion-summary.yaml を確認してください'
            tmux send-keys -t "$CONDUCTOR_PANE" Enter
            ;;
    esac
done
```

**Step 2: launch.shからinbox_watcher.shを起動**
- バックグラウンドプロセスとして起動
- PIDを.ensemble/inbox_watcher.pidに保存
- tmux終了時にkill

**Step 3: ポーリングロジック削除**
- dispatch.md: ポーリングループ削除、「通知を待つ」に変更
- conductor.md: 30秒間隔ポーリング削除、「completion-summary.yaml の通知を待つ」に変更

**Step 4: WSL2フォールバック**
- inbox_watcher.sh内で5秒タイムアウト実装
- inotifywaitが5秒以内に反応しない場合、手動でディレクトリスキャン

#### テスト方針
- **単体テスト**: inbox_watcher.shが特定パターンのファイル作成を検知することを確認
- **統合テスト**: Worker完了 → 即座にDispatch通知 → 即座にConductor通知の遅延を測定（< 1秒）
- **ストレステスト**: 10並列タスクで全通知が漏れないことを確認

#### 実行パターン
**パターンA** - 単純タスク（ファイル数3未満）

#### 依存関係
なし（独立して実装可能）

#### 推定規模
- 変更ファイル数: 4ファイル
- 新規ファイル数: 2ファイル
- 実装時間: 4-6時間

---

### 2.2 施策P0-2: flock排他制御の導入

#### 概要
queue/への並列書き込みでYAML破損を防ぐため、flockによる排他制御とatomic writeを導入。

#### 背景
- **現状**: YAML直接書き込み（競合リスク）
- **問題**: 複数Workerが同時にqueue/reports/に書き込むと、YAML破損の可能性
- **参考**: Shogun inbox_write.sh - flock + tmp+rename でatomic write

#### 変更対象ファイル
- `src/ensemble/lock.py` - flock実装を追加（現在はファイル移動のみ）
- `src/ensemble/queue.py` - atomic_write呼び出し箇所をflock経由に変更
- `src/ensemble/templates/agents/worker.md` - 報告ファイル作成をflock経由に変更指示
- `.claude/agents/worker.md` - 同上（ローカル版）

#### 新規作成ファイル
なし（既存のlock.pyを拡張）

#### テンプレート同期
- `.claude/agents/worker.md` ← `src/ensemble/templates/agents/worker.md`

#### 技術アプローチ

**Step 1: lock.pyにflock関数を追加**
```python
import fcntl
from pathlib import Path

def atomic_write_with_lock(file_path: str, content: str) -> None:
    """
    flock排他ロック + atomic write（tmp + rename）
    """
    lock_file = Path(file_path).with_suffix('.lock')
    tmp_file = Path(file_path).with_suffix('.tmp')

    with open(lock_file, 'w') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)  # 排他ロック取得

        try:
            # tmpファイルに書き込み
            tmp_file.write_text(content, encoding='utf-8')
            # atomic rename
            tmp_file.rename(file_path)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)  # ロック解放
            lock_file.unlink(missing_ok=True)
```

**Step 2: queue.pyのatomic_writeをflock版に置き換え**
```python
from ensemble.lock import atomic_write_with_lock

# enqueue(), complete() 内の atomic_write() 呼び出しを全て置き換え
atomic_write_with_lock(str(task_file), content)
```

**Step 3: worker.mdに指示追加**
- 「完了報告YAML作成時は、Pythonスクリプトからensemble.lock.atomic_write_with_lockを使用すること」
- シェルスクリプトでの直接書き込みは禁止

#### テスト方針
- **並列書き込みテスト**: 10 WorkerがI同時にreportsディレクトリに書き込み、全YAMLが正常にパース可能か確認
- **ロック競合テスト**: flock待機時間を測定（1秒以内に解放されること）

#### 実行パターン
**パターンA** - 単純タスク

#### 依存関係
なし（P0-1と独立）

#### 推定規模
- 変更ファイル数: 4ファイル
- 新規ファイル数: 0ファイル
- 実装時間: 2-3時間

---

### 2.3 施策P0-3: 3段階自動エスカレーション

#### 概要
Worker無応答時に手動介入なしで自動復旧する仕組みを導入。

#### 背景
- **現状**: ACKタイムアウト後、Dispatchが手動でエスカレーションYAMLを作成 → Conductorが手動対応
- **問題**: 手動介入が必要、復旧に時間がかかる（5分以上）
- **参考**: Shogun 3-phase escalation - 2分待機 → Escape×2+C-c → 4分後に/clear自動送信

#### 変更対象ファイル
- `src/ensemble/templates/agents/dispatch.md` - エスカレーションロジックを3段階に拡張
- `.claude/agents/dispatch.md` - 同上（ローカル版）
- `src/ensemble/ack.py` - タイムアウト判定を3段階に分離

#### 新規作成ファイル
- `src/ensemble/templates/scripts/escalate.sh` - 自動エスカレーションスクリプト
  - Phase 1 (0-2分): 通常nudge（send-keys）
  - Phase 2 (2-4分): Escape×2 + C-c + nudge
  - Phase 3 (4分+): /clear送信（5分に1回まで）

#### テンプレート同期
- `.claude/agents/dispatch.md` ← `src/ensemble/templates/agents/dispatch.md`
- `scripts/escalate.sh` ← `src/ensemble/templates/scripts/escalate.sh`

#### 技術アプローチ

**Step 1: escalate.sh作成**
```bash
#!/bin/bash
# 引数: PANE_ID, WORKER_ID, PHASE (1/2/3)
PANE_ID="$1"
WORKER_ID="$2"
PHASE="$3"

case "$PHASE" in
    1)
        # Phase 1: 通常nudge
        tmux send-keys -t "$PANE_ID" "queue/tasks/worker-${WORKER_ID}-task.yaml を確認してください"
        tmux send-keys -t "$PANE_ID" Enter
        ;;
    2)
        # Phase 2: Escape + C-c + nudge
        tmux send-keys -t "$PANE_ID" Escape
        sleep 0.5
        tmux send-keys -t "$PANE_ID" Escape
        sleep 0.5
        tmux send-keys -t "$PANE_ID" C-c
        sleep 1
        tmux send-keys -t "$PANE_ID" "queue/tasks/worker-${WORKER_ID}-task.yaml を確認してください"
        tmux send-keys -t "$PANE_ID" Enter
        ;;
    3)
        # Phase 3: /clear送信
        tmux send-keys -t "$PANE_ID" '/clear'
        tmux send-keys -t "$PANE_ID" Enter
        sleep 5
        tmux send-keys -t "$PANE_ID" "queue/tasks/worker-${WORKER_ID}-task.yaml を確認してください"
        tmux send-keys -t "$PANE_ID" Enter
        ;;
esac
```

**Step 2: dispatch.mdにエスカレーションフロー追加**
```markdown
## ACK待機フロー（3段階エスカレーション）

1. タスク配信後、60秒待機
2. ACKなし → Phase 1: escalate.sh 1を実行、さらに60秒待機
3. ACKなし → Phase 2: escalate.sh 2を実行、さらに60秒待機
4. ACKなし → Phase 3: escalate.sh 3を実行、さらに60秒待機
5. ACKなし → Conductorにエスカレーション報告
```

**Step 3: ack.pyに段階的タイムアウトを追加**
```python
def wait_for_ack_with_escalation(task_id: str, worker_id: int, pane_id: str) -> bool:
    for phase in [1, 2, 3]:
        if wait_for_ack(task_id, timeout=60):
            return True
        # escalate.sh を実行
        subprocess.run(['scripts/escalate.sh', pane_id, str(worker_id), str(phase)])
    return False  # 3段階エスカレーション全て失敗
```

#### テスト方針
- **Phase 1テスト**: Workerが30秒間応答しない状態をシミュレート、自動nudgeを確認
- **Phase 2テスト**: Workerがカーソル位置エラーで固まった状態をシミュレート、Escape+C-cで復旧を確認
- **Phase 3テスト**: Workerがコンテキスト満杯で応答しない状態をシミュレート、/clearで復旧を確認

#### 実行パターン
**パターンB** - 中規模タスク（複数Worker起動時のテストが必要）

#### 依存関係
なし（P0-1, P0-2と独立）

#### 推定規模
- 変更ファイル数: 3ファイル
- 新規ファイル数: 1ファイル
- 実装時間: 3-4時間

---

## 3. P1: ワークフロー進化（v0.6.0）

### 概要
TAKTの設計から学び、ワークフローの信頼性・追跡性を向上。

### 3.1 施策P1-1: ループ検知の導入

#### 概要
レビュー → 修正 → レビュー の無限ループを自動検知し、コスト浪費を防ぐ。

#### 背景
- **現状**: ループ検知なし（レビューで繰り返しneeds_fixが出る可能性）
- **問題**: 非生産的ループでコスト浪費、タスク完了しない
- **参考**: TAKT LoopDetector - 同一タスクへの繰り返し遷移を自動検知（閾値5回）

#### 変更対象ファイル
- `src/ensemble/workflow.py` - ループ検知ロジック追加
- `src/ensemble/templates/agents/conductor.md` - ループ検知結果に基づく判断フロー追加
- `.claude/agents/conductor.md` - 同上（ローカル版）

#### 新規作成ファイル
- `src/ensemble/loop_detector.py` - ループ検知モジュール
  - LoopDetector: 同一タスクIDへの遷移を追跡（閾値5回）
  - CycleDetector: review → fix → review サイクルを追跡（閾値3回）

#### テンプレート同期
- `.claude/agents/conductor.md` ← `src/ensemble/templates/agents/conductor.md`

#### 技術アプローチ

**Step 1: loop_detector.py作成**
```python
from collections import defaultdict

class LoopDetector:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.task_counts = defaultdict(int)

    def record(self, task_id: str) -> bool:
        """
        タスク実行を記録し、ループを検知
        Returns: ループ検知ならTrue
        """
        self.task_counts[task_id] += 1
        return self.task_counts[task_id] > self.max_iterations

class CycleDetector:
    def __init__(self, max_cycles: int = 3):
        self.max_cycles = max_cycles
        self.cycle_counts = defaultdict(int)

    def record_cycle(self, task_id: str, from_state: str, to_state: str) -> bool:
        """
        遷移サイクルを記録し、閾値超過を検知
        """
        cycle_key = f"{task_id}:{from_state}->{to_state}"
        self.cycle_counts[cycle_key] += 1
        return self.cycle_counts[cycle_key] > self.max_cycles
```

**Step 2: workflow.pyに統合**
```python
from ensemble.loop_detector import LoopDetector, CycleDetector

class WorkflowEngine:
    def __init__(self):
        self.loop_detector = LoopDetector(max_iterations=5)
        self.cycle_detector = CycleDetector(max_cycles=3)

    def execute_step(self, task_id: str, step_name: str):
        # ループ検知
        if self.loop_detector.record(task_id):
            raise LoopDetectedError(f"Task {task_id} exceeded max iterations")

        # ステップ実行...
```

**Step 3: conductor.mdにループ検知対応追加**
```markdown
## ループ検知時の対応

1. LoopDetectedErrorを受信
2. 原因分析:
   - レビュー基準が不明確か？
   - Workerの能力不足か？
   - タスク自体が実行不可能か？
3. ユーザーに報告:
   - 「タスク{task_id}が5回繰り返し、進展がありません」
   - 「推奨: タスクを分割するか、手動で介入してください」
```

#### テスト方針
- **単体テスト**: LoopDetectorが5回目で検知することを確認
- **統合テスト**: review → fix → review を3回繰り返すとCycleDetectorが発火することを確認

#### 実行パターン
**パターンA** - 単純タスク

#### 依存関係
なし（P0と独立）

#### 推定規模
- 変更ファイル数: 3ファイル
- 新規ファイル数: 1ファイル
- 実装時間: 2-3時間

---

### 3.2 施策P1-2: タスク依存関係（blockedBy）の導入

#### 概要
タスク間の依存関係を明示化し、順序依存タスクの安全な並列投入を可能にする。

#### 背景
- **現状**: 依存関係の明示的管理なし
- **問題**: 「API実装後にテスト」のような順序依存タスクを並列投入できない
- **参考**: Shogun blockedByフィールド - 依存タスク完了後に自動着手

#### 変更対象ファイル
- `src/ensemble/queue.py` - Task YAMLにblockedByフィールド追加
- `src/ensemble/templates/agents/dispatch.md` - 依存関係チェックロジック追加
- `.claude/agents/dispatch.md` - 同上（ローカル版）

#### 新規作成ファイル
- `src/ensemble/dependency.py` - 依存関係解決モジュール
  - タスクグラフ構築
  - 依存解決済みタスクのフィルタリング
  - 循環依存検知

#### テンプレート同期
- `.claude/agents/dispatch.md` ← `src/ensemble/templates/agents/dispatch.md`

#### 技術アプローチ

**Step 1: Task YAMLフォーマット拡張**
```yaml
id: task-002
instruction: "APIテストを作成"
files:
  - "tests/test_api.py"
blocked_by:
  - task-001  # task-001完了後に実行可能
workflow: default
```

**Step 2: dependency.py作成**
```python
from typing import List, Dict, Set

class DependencyResolver:
    def __init__(self, tasks: List[Dict]):
        self.tasks = {t['id']: t for t in tasks}
        self.completed = set()

    def get_ready_tasks(self) -> List[Dict]:
        """
        依存が全て解決済みのタスクを返す
        """
        ready = []
        for task_id, task in self.tasks.items():
            if task_id in self.completed:
                continue
            blocked_by = set(task.get('blocked_by', []))
            if blocked_by.issubset(self.completed):
                ready.append(task)
        return ready

    def mark_completed(self, task_id: str):
        self.completed.add(task_id)

    def detect_cycles(self) -> List[List[str]]:
        """循環依存を検知"""
        # 深さ優先探索で循環を検出
        pass
```

**Step 3: dispatch.mdに依存関係チェック追加**
```markdown
## タスク配信フロー（依存関係考慮）

1. queue/conductor/dispatch-instruction.yamlから全タスクを読み込む
2. DependencyResolverで依存解決済みタスクをフィルタ
3. フィルタ後のタスクを各Workerに配信
4. Worker完了報告受信後、dependency_resolver.mark_completed()を呼び出し
5. 新たに依存解決されたタスクがあれば、空きWorkerに配信
```

#### テスト方針
- **依存関係テスト**: task-001 → task-002 → task-003 の連鎖を正しく解決することを確認
- **循環依存テスト**: task-001 → task-002 → task-001 の循環を検知することを確認

#### 実行パターン
**パターンB** - 中規模タスク（複数Worker）

#### 依存関係
なし（P0, P1-1と独立）

#### 推定規模
- 変更ファイル数: 3ファイル
- 新規ファイル数: 1ファイル
- 実装時間: 3-4時間

---

### 3.3 施策P1-3: NDJSONセッションログの導入

#### 概要
実行履歴を完全追跡可能なNDJSON形式ログを導入。

#### 背景
- **現状**: ログなし（dashboard.mdのみ）
- **問題**: タスク実行の詳細追跡ができない、デバッグ困難
- **参考**: TAKT NDJSON logging - アトミック追記ログで全イベントを記録

#### 変更対象ファイル
なし（新規モジュール）

#### 新規作成ファイル
- `src/ensemble/logger.py` - NDJSONロガーモジュール（既存ファイルを拡張）
  - イベントタイプ: task_start, task_complete, worker_assign, review_result, escalation
  - .ensemble/logs/session-{timestamp}.ndjson に追記
- `src/ensemble/templates/agents/dispatch.md` - ログ出力指示追加
- `src/ensemble/templates/agents/conductor.md` - ログ出力指示追加

#### テンプレート同期
- `.claude/agents/dispatch.md` ← `src/ensemble/templates/agents/dispatch.md`
- `.claude/agents/conductor.md` ← `src/ensemble/templates/agents/conductor.md`

#### 技術アプローチ

**Step 1: logger.py拡張**
```python
import json
from datetime import datetime
from pathlib import Path

class NDJSONLogger:
    def __init__(self, log_dir: Path = Path('.ensemble/logs')):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.log_file = self.log_dir / f'session-{timestamp}.ndjson'

    def log_event(self, event_type: str, data: dict):
        """
        イベントをNDJSON形式で追記
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
```

**Step 2: イベントタイプ定義**
- `task_start`: タスク開始（task_id, worker_id, files）
- `task_complete`: タスク完了（task_id, status, duration）
- `worker_assign`: Worker割り当て（worker_id, task_id）
- `review_result`: レビュー結果（task_id, reviewer, result）
- `escalation`: エスカレーション（worker_id, phase, reason）
- `loop_detected`: ループ検知（task_id, iteration_count）

**Step 3: dispatch.md/conductor.mdに指示追加**
```markdown
## ログ出力（必須）

全てのイベントをNDJSONログに記録すること:
- タスク配信時: logger.log_event('task_start', {...})
- 完了報告受信時: logger.log_event('task_complete', {...})
```

#### テスト方針
- **ログ出力テスト**: タスク実行後、NDJSONログに全イベントが記録されていることを確認
- **パーステスト**: jqでログをクエリし、特定タスクの実行履歴を抽出可能か確認

#### 実行パターン
**パターンA** - 単純タスク

#### 依存関係
なし（P0, P1-1, P1-2と独立）

#### 推定規模
- 変更ファイル数: 1ファイル（logger.py拡張）
- 新規ファイル数: 0ファイル
- 実装時間: 2-3時間

---

## 4. P2: プロンプト設計改善（v0.7.0）

### 概要
TAKTのFaceted PromptingとCC Best PracticeのSkillsパターンから学び、プロンプトの再利用性・保守性を向上。

### 4.1 施策P2-1: Faceted Promptingの導入

#### 概要
エージェント定義を5つの関心（WHO/RULES/WHAT/CONTEXT/OUTPUT）に分離し、宣言的に合成。

#### 背景
- **現状**: エージェントmd（1ファイルに全情報混在）
- **問題**: 再利用性低い、プロンプト品質のバラつき、カスタマイズ困難
- **参考**: TAKT Faceted Prompting - 5関心分離と宣言的合成

#### 変更対象ファイル
- 全エージェント定義（conductor.md, dispatch.md, worker.md, reviewer.md, security-reviewer.md, integrator.md, learner.md）を分割

#### 新規作成ファイル（ディレクトリ構造）
```
.claude/
├── personas/          # WHO: 役割定義
│   ├── conductor.md
│   ├── dispatch.md
│   ├── worker-coder.md
│   ├── reviewer-arch.md
│   └── reviewer-security.md
├── policies/          # RULES: 禁止事項、品質基準
│   ├── security.md
│   ├── coding.md
│   ├── review.md
│   └── communication.md
├── instructions/      # WHAT: ステップ手順
│   ├── plan.md
│   ├── implement.md
│   ├── review.md
│   └── learn.md
├── knowledge/         # CONTEXT: ドメイン知識
│   └── project-specific.md
└── output-contracts/  # OUTPUT: レポートフォーマット
    ├── worker-report.md
    ├── review-report.md
    └── completion-summary.md
```

#### テンプレート同期
- `src/ensemble/templates/claude/` 配下に同じ構造を作成
- ensemble upgradeで同期

#### 技術アプローチ

**Step 1: 既存エージェント定義を分析し、5関心に分離**

例: worker.md → 以下に分割
- `personas/worker-coder.md`: 「あなたはWorkerです。実行者として...」
- `policies/coding.md`: 「担当範囲を守れ」「禁止事項」
- `instructions/implement.md`: 「タスク実行フロー」
- `output-contracts/worker-report.md`: 「完了報告フォーマット」

**Step 2: 合成ロジック作成**

エージェント起動時に各facetを読み込んで合成:
```python
def compose_agent_prompt(agent_name: str) -> str:
    """
    Faceted Promptingで合成
    """
    persona = read_file(f'.claude/personas/{agent_name}.md')
    policies = read_all_files('.claude/policies/')
    instructions = read_file(f'.claude/instructions/{agent_name}.md')
    knowledge = read_file('.claude/knowledge/project-specific.md')
    output_contract = read_file(f'.claude/output-contracts/{agent_name}-report.md')

    return f"""
{persona}

{policies}

{instructions}

{knowledge}

{output_contract}
"""
```

**Step 3: テンプレート作成**

conductor用の合成テンプレート:
```markdown
# Conductor Agent

{personas/conductor.md}

## Rules
{policies/communication.md}
{policies/security.md}

## Instructions
{instructions/plan.md}

## Context
{knowledge/project-specific.md}

## Output Format
{output-contracts/completion-summary.md}
```

#### テスト方針
- **合成テスト**: 分離前後でエージェントの動作が同一であることを確認
- **再利用テスト**: policies/security.mdを複数エージェントで共有し、重複がないことを確認

#### 実行パターン
**パターンC** - 大規模タスク（全エージェント定義を分割）

#### 依存関係
なし（P0, P1と独立）

#### 推定規模
- 変更ファイル数: 7ファイル（全エージェント定義）
- 新規ファイル数: 約20ファイル（5関心 × 複数エージェント）
- 実装時間: 8-10時間

---

### 4.2 施策P2-2: Progressive Disclosure Skillsの導入

#### 概要
タスク種別に応じてWorkerにSkillsを動的注入し、専門性を向上。

#### 背景
- **現状**: Worker = 汎用Sonnetエージェント
- **問題**: タスク特性に応じた専門知識が不足
- **参考**: CC Best Practice - feature specific subagents with skills

#### 変更対象ファイル
- `src/ensemble/templates/agents/worker.md` - Skills注入指示追加
- `.claude/agents/worker.md` - 同上（ローカル版）

#### 新規作成ファイル（スキル定義）
```
.claude/
└── skills/
    ├── react-frontend.md      # React/Next.js開発スキル
    ├── backend-api.md         # API実装スキル
    ├── database-migration.md  # DB変更スキル
    ├── security-audit.md      # セキュリティ監査スキル
    └── testing.md             # テスト作成スキル
```

#### テンプレート同期
- `src/ensemble/templates/claude/skills/` 配下にスキル定義を作成
- ensemble upgradeで同期

#### 技術アプローチ

**Step 1: タスク種別判定ロジック**

Conductorがタスク内容を分析し、必要なスキルを判定:
```python
def determine_skills(task: dict) -> list[str]:
    """
    タスク内容から必要なスキルを判定
    """
    files = task.get('files', [])
    skills = []

    if any('test_' in f or '_test.py' in f for f in files):
        skills.append('testing')
    if any('api/' in f or 'routes/' in f for f in files):
        skills.append('backend-api')
    if any('components/' in f or 'pages/' in f for f in files):
        skills.append('react-frontend')
    if any('migrations/' in f or 'schema.sql' in f for f in files):
        skills.append('database-migration')

    return skills
```

**Step 2: dispatch-instruction.yamlにskillsフィールド追加**
```yaml
tasks:
  - id: task-001
    instruction: "API実装"
    files: ["src/api/users.py"]
    skills:
      - backend-api
      - security-audit
```

**Step 3: Worker起動時にスキル注入**

pane-setup.sh修正:
```bash
# Skillsを環境変数で渡す
SKILLS="backend-api,security-audit"
tmux send-keys -t "$NEW_PANE" \
    "export WORKER_ID=$i SKILLS=$SKILLS && claude --agent worker"
```

worker.md修正:
```markdown
## タスク開始前

1. $SKILLS環境変数を確認
2. 各スキルの定義を読み込む:
   - .claude/skills/backend-api.md
   - .claude/skills/security-audit.md
3. スキルに基づいて作業を進める
```

#### テスト方針
- **スキル注入テスト**: Workerがスキル定義を正しく読み込むことを確認
- **専門性テスト**: react-frontendスキル注入時、React固有のベストプラクティスが適用されることを確認

#### 実行パターン
**パターンB** - 中規模タスク（複数Worker起動）

#### 依存関係
**P2-1（Faceted Prompting）** - スキル定義の構造化に依存

#### 推定規模
- 変更ファイル数: 2ファイル
- 新規ファイル数: 5ファイル（スキル定義）
- 実装時間: 4-5時間

---

## 5. P3: 運用機能充実（v0.8.0）

### 概要
実運用向けの機能拡張。各施策は独立しており、優先度に応じて選択的に実装可能。

### 5.1 施策P3-1: CI/CDパイプラインモード

#### 概要
GitHub ActionsなどのCI/CD環境で自動実行可能なモードを追加。

#### 背景
- **現状**: tmux対話環境が前提（CI/CDで使えない）
- **問題**: 自動化パイプラインに組み込めない
- **参考**: TAKT --pipelineモード - 非対話環境での実行

#### 変更対象ファイル
- `src/ensemble/cli.py` - --pipelineオプション追加
- `src/ensemble/commands/launch.py` - 非対話モード対応

#### 新規作成ファイル
- `src/ensemble/pipeline.py` - パイプライン実行モジュール
  - tmuxなしで順次実行
  - 標準出力にログ出力
  - 終了コードで成否を返す

#### テンプレート同期
なし（CLI実装のみ）

#### 技術アプローチ

**Step 1: --pipelineオプション追加**
```bash
ensemble launch --pipeline --task "バグ修正" --auto-pr
# → ブランチ作成 → 実行 → commit & push → PR作成
```

**Step 2: 非対話実行ロジック**
- tmuxセッション作成をスキップ
- subagent（Task tool）で順次実行
- 標準出力にログ出力（NDJSON）

**Step 3: 終了コード定義**
- 0: 成功
- 1: 実行エラー
- 2: レビューneeds_fix
- 3: ループ検知

#### テスト方針
- **CI環境テスト**: GitHub Actionsで実行し、成功時に0を返すことを確認
- **エラーハンドリング**: 実行エラー時に適切な終了コードを返すことを確認

#### 実行パターン
**パターンA** - 単純タスク（CI環境）

#### 依存関係
**P1-3（NDJSONログ）** - ログ出力機能に依存

#### 推定規模
- 変更ファイル数: 2ファイル
- 新規ファイル数: 1ファイル
- 実装時間: 4-5時間

---

### 5.2 施策P3-2: Bloom's Taxonomy的タスク分類

#### 概要
タスクの認知レベルに基づいてモデルを自動選択し、コスト効率を向上。

#### 背景
- **現状**: Conductor=Opus, Worker=Sonnet固定
- **問題**: 単純タスクでもSonnet使用、高度タスクでもSonnet使用
- **参考**: Shogun Bloom's Taxonomy - L1-L3=Sonnet, L4-L6=Opus

#### 変更対象ファイル
- `src/ensemble/templates/agents/conductor.md` - タスク分類ロジック追加
- `.claude/agents/conductor.md` - 同上（ローカル版）

#### 新規作成ファイル
- `src/ensemble/bloom.py` - Bloom's Taxonomy分類モジュール

#### テンプレート同期
- `.claude/agents/conductor.md` ← `src/ensemble/templates/agents/conductor.md`

#### 技術アプローチ

**Step 1: bloom.py作成**
```python
from enum import IntEnum

class BloomLevel(IntEnum):
    REMEMBER = 1    # 事実の想起、コピー
    UNDERSTAND = 2  # 説明、要約
    APPLY = 3       # 手順の実行
    ANALYZE = 4     # 比較、調査
    EVALUATE = 5    # 判断、批評
    CREATE = 6      # 設計、新しい解決策

def classify_task(instruction: str) -> BloomLevel:
    """
    タスク指示文からBloomレベルを判定
    """
    keywords = {
        BloomLevel.REMEMBER: ['コピー', 'リスト', '列挙'],
        BloomLevel.UNDERSTAND: ['説明', '要約', '言い換え'],
        BloomLevel.APPLY: ['実装', '適用', 'テスト'],
        BloomLevel.ANALYZE: ['比較', '調査', '分析'],
        BloomLevel.EVALUATE: ['判断', '評価', 'レビュー'],
        BloomLevel.CREATE: ['設計', '構築', 'アーキテクチャ']
    }

    for level, words in sorted(keywords.items(), reverse=True):
        if any(word in instruction for word in words):
            return level

    return BloomLevel.APPLY  # デフォルト

def select_model(level: BloomLevel) -> str:
    """
    BloomレベルからClaude Codeモデルを選択
    """
    if level <= BloomLevel.APPLY:
        return "sonnet"  # L1-L3: Sonnet
    else:
        return "opus"    # L4-L6: Opus
```

**Step 2: conductor.mdに分類指示追加**
```markdown
## タスク分解時の判断

1. タスク指示文をBloom's Taxonomyで分類
2. L1-L3（Remember/Understand/Apply）→ Sonnetで十分
3. L4-L6（Analyze/Evaluate/Create）→ Opus推奨
4. dispatch-instruction.yamlに worker_agent: "worker-opus" を指定
```

**Step 3: pane-setup.shにOpus対応追加**
```bash
# WORKER_AGENT環境変数が "worker-opus" の場合
if [ "$WORKER_AGENT" = "worker-opus" ]; then
    claude --agent worker --model opus
else
    claude --agent worker  # デフォルトはSonnet
fi
```

#### テスト方針
- **分類テスト**: 「APIを設計」→ L6（CREATE）、「テストを実装」→ L3（APPLY）と判定されることを確認
- **モデル選択テスト**: L6タスクでOpusが起動することを確認

#### 実行パターン
**パターンB** - 中規模タスク

#### 依存関係
なし（P0, P1, P2と独立）

#### 推定規模
- 変更ファイル数: 2ファイル
- 新規ファイル数: 1ファイル
- 実装時間: 3-4時間

---

### 5.3 施策P3-3: Bottom-Up Skill Discovery

#### 概要
Workerが繰り返し実行したパターンを検知し、スキル化候補として提案。

#### 背景
- **現状**: スキル定義は手動で作成
- **問題**: 繰り返しパターンが見逃される、スキル化のタイミングがわからない
- **参考**: Shogun Bottom-Up Skill Discovery - 同パターン3回で自動候補検出

#### 変更対象ファイル
- `src/ensemble/templates/agents/worker.md` - パターン検知指示追加
- `src/ensemble/templates/agents/learner.md` - スキル候補集約指示追加
- `.claude/agents/worker.md` - 同上（ローカル版）
- `.claude/agents/learner.md` - 同上（ローカル版）

#### 新規作成ファイル
なし（worker-report.yamlにskill_candidateフィールド追加のみ）

#### テンプレート同期
- `.claude/agents/worker.md` ← `src/ensemble/templates/agents/worker.md`
- `.claude/agents/learner.md` ← `src/ensemble/templates/agents/learner.md`

#### 技術アプローチ

**Step 1: worker.mdに指示追加**
```markdown
## タスク完了報告時

以下の場合、skill_candidateフィールドを追加:
- 同じパターンの作業を3回以上実行した
- 他のタスクでも再利用できそうな手順がある

例:
```yaml
skill_candidate:
  found: true
  name: "api-endpoint-scaffold"
  reason: "同パターンを3回実行"
  pattern: |
    1. FastAPIのエンドポイント定義
    2. Pydanticモデル作成
    3. CRUD操作実装
```

**Step 2: learner.mdに集約指示追加**
```markdown
## 自己改善フェーズ（skill候補集約）

1. 全Worker報告からskill_candidateを収集
2. 3回以上出現したパターンを抽出
3. notes/{task-id}/skill-candidates.mdに記録
4. ユーザーに提案:
   「以下のスキル化候補が見つかりました。/create-skillで作成できます」
```

**Step 3: /create-skillコマンドとの統合**

既存の/create-skillコマンドにskill-candidates.mdからテンプレート生成機能を追加。

#### テスト方針
- **パターン検知テスト**: 同じ手順を3回実行し、skill_candidateが報告されることを確認
- **集約テスト**: learnerが複数Workerの候補を集約し、重複排除することを確認

#### 実行パターン
**パターンB** - 中規模タスク（複数Worker）

#### 依存関係
**P2-2（Progressive Disclosure Skills）** - スキル定義の構造に依存

#### 推定規模
- 変更ファイル数: 2ファイル
- 新規ファイル数: 0ファイル
- 実装時間: 2-3時間

---

## 6. 依存関係グラフ

```
P0: 通信インフラ強化（v0.5.0）
├── P0-1: inotifywaitイベント駆動 ─┐
├── P0-2: flock排他制御          ─┼─→ P1: ワークフロー進化（v0.6.0）
└── P0-3: 3段階エスカレーション   ─┘      ├── P1-1: ループ検知
                                           ├── P1-2: タスク依存関係
                                           └── P1-3: NDJSONログ ─→ P3-1: CI/CD
                                                                      パイプライン
                                                                      （v0.8.0）

P2: プロンプト設計改善（v0.7.0）
├── P2-1: Faceted Prompting ─→ P2-2: Progressive Disclosure ─→ P3-3: Bottom-Up
└─────────────────────────────────────────────────────────────→ Skill Discovery
                                                                 （v0.8.0）

P3-2: Bloom's Taxonomy（v0.8.0）
└── 独立（P0, P1, P2と並行実装可能）
```

### 実装順序の推奨

#### フェーズ1（v0.5.0）
1. **P0-2（flock）** - 最も安全に導入可能、影響範囲が限定的
2. **P0-1（inotifywait）** - 通信基盤の根本改善
3. **P0-3（エスカレーション）** - P0-1の効果を最大化

#### フェーズ2（v0.6.0）
1. **P1-3（NDJSONログ）** - 独立して導入可能、後続フェーズの基盤
2. **P1-1（ループ検知）** - 独立して導入可能、すぐに効果が出る
3. **P1-2（タスク依存関係）** - 最も複雑、最後に実装

#### フェーズ3（v0.7.0）
1. **P2-1（Faceted Prompting）** - 大規模だが効果大
2. **P2-2（Progressive Disclosure）** - P2-1に依存

#### フェーズ4（v0.8.0）
- P3-1, P3-2, P3-3を必要に応じて選択的に実装

---

## 7. GitHub Issues化テンプレート

### Issue テンプレート（共通）

```markdown
## 概要
[施策の1行説明]

## 背景
- 現状: [現在の問題点]
- 参考: [shogun/TAKT/CC Best Practiceのどこから学んだか]

## 実装内容
### 変更ファイル
- [ ] `file1.py` - [変更内容]
- [ ] `file2.md` - [変更内容]

### 新規ファイル
- [ ] `new_file.py` - [役割]

## テスト計画
- [ ] 単体テスト: [テスト内容]
- [ ] 統合テスト: [テスト内容]

## 完了条件
- [ ] 全テストが通過
- [ ] ドキュメント更新（ARCHITECTURE.md, USAGE.md）
- [ ] ensemble upgradeでテンプレート同期確認

## 推定工数
[X-Y時間]

## ラベル
`priority-[high/medium/low]`, `phase-[P0/P1/P2/P3]`, `enhancement`

## マイルストーン
v0.5.0 / v0.6.0 / v0.7.0 / v0.8.0
```

### 具体例: P0-1（イベント駆動通信）

```markdown
## 概要
ポーリング（30秒間隔）を廃止し、inotifywaitベースのイベント駆動通信に置き換える

## 背景
- 現状: Dispatchが30秒間隔でqueue/reports/をポーリング（検知遅延30秒、CPU消費）
- 参考: Shogun inbox_watcher.sh - カーネルレベルのファイル変更検知（検知遅延0秒、CPU 0%）

## 実装内容
### 変更ファイル
- [ ] `src/ensemble/templates/agents/dispatch.md` - ポーリングロジック削除
- [ ] `src/ensemble/templates/agents/conductor.md` - completion-summary.yaml待機をinotify監視に変更
- [ ] `.claude/agents/dispatch.md` - 同上（ローカル版）
- [ ] `.claude/agents/conductor.md` - 同上（ローカル版）

### 新規ファイル
- [ ] `src/ensemble/templates/scripts/inbox_watcher.sh` - queue/ディレクトリ監視デーモン
- [ ] `src/ensemble/inbox.py` - Pythonからinotifywaitを制御するモジュール

## テスト計画
- [ ] 単体テスト: inbox_watcher.shが特定パターンのファイル作成を検知することを確認
- [ ] 統合テスト: Worker完了 → 即座にDispatch通知 → 即座にConductor通知の遅延を測定（< 1秒）
- [ ] ストレステスト: 10並列タスクで全通知が漏れないことを確認

## 完了条件
- [ ] 全テストが通過
- [ ] ドキュメント更新（ARCHITECTURE.md, USAGE.md, communication.md）
- [ ] ensemble upgradeでテンプレート同期確認
- [ ] WSL2環境でもinotifywaitが動作することを確認

## 推定工数
4-6時間

## ラベル
`priority-high`, `phase-P0`, `enhancement`, `communication`

## マイルストーン
v0.5.0
```

---

## 8. マイルストーン

### v0.5.0: P0完了（通信インフラ強化）

**リリース目標**: 2025年Q2

#### 達成目標
- 検知遅延: 30秒 → 0秒
- CPU効率: ポーリング消費 → 0%
- 手動介入: 必要 → 4分以内自動復旧

#### 含まれる施策
- P0-1: inotifywaitイベント駆動通信
- P0-2: flock排他制御
- P0-3: 3段階自動エスカレーション

#### テスト計画
- 全施策の統合テスト
- 長時間実行テスト（8時間）
- WSL2/Linux/macOS動作確認

#### ドキュメント更新
- ARCHITECTURE.md: 通信プロトコルv3.0追記
- communication.md: イベント駆動通信プロトコル追記
- USAGE.md: トラブルシューティング更新

---

### v0.6.0: P1完了（ワークフロー進化）

**リリース目標**: 2025年Q3

#### 達成目標
- ループ検知: 無限ループ防止
- 依存関係: 順序依存タスクの自動管理
- 実行履歴: 完全追跡可能

#### 含まれる施策
- P1-1: ループ検知
- P1-2: タスク依存関係（blockedBy）
- P1-3: NDJSONセッションログ

#### テスト計画
- ループ検知の動作確認（review → fix → review を3回繰り返す）
- 依存関係解決の動作確認（task-001 → task-002 → task-003）
- NDJSONログのパース確認（jqでクエリ）

#### ドキュメント更新
- ARCHITECTURE.md: ワークフロー進化セクション追加
- workflow.md: ループ検知・依存関係解決の説明追加
- USAGE.md: ログ分析方法追記

---

### v0.7.0: P2完了（プロンプト設計改善）

**リリース目標**: 2025年Q4

#### 達成目標
- プロンプト再利用性: 5関心分離で向上
- カスタマイズ容易性: YAMLキー参照で合成
- Worker専門化: タスク種別に応じたスキル注入

#### 含まれる施策
- P2-1: Faceted Prompting
- P2-2: Progressive Disclosure Skills

#### テスト計画
- Faceted Prompting合成テスト（分離前後で動作同一）
- Skills注入テスト（react-frontendスキルが正しく読み込まれる）

#### ドキュメント更新
- ARCHITECTURE.md: プロンプト設計セクション追加
- .claude/README.md: Faceted Promptingの説明追加
- USAGE.md: /create-skillの使い方更新

---

### v0.8.0: P3完了（運用機能充実）

**リリース目標**: 2026年Q1

#### 達成目標
- CI/CD対応: GitHub Actionsで自動実行可能
- コスト最適化: Bloom's Taxonomyでモデル自動選択
- スキル自動化: Bottom-Up Skill Discovery

#### 含まれる施策
- P3-1: CI/CDパイプラインモード
- P3-2: Bloom's Taxonomy的タスク分類
- P3-3: Bottom-Up Skill Discovery

#### テスト計画
- CI環境テスト（GitHub Actions）
- Bloom分類テスト（「設計」→ Opus、「実装」→ Sonnet）
- スキル候補検知テスト（同パターン3回で候補検出）

#### ドキュメント更新
- ARCHITECTURE.md: 運用機能セクション追加
- USAGE.md: --pipelineオプション、Bloom分類の説明追加
- README.md: v0.8.0の新機能を強調

---

## 9. 実装時の注意事項

### 9.1 インフラ整合性チェック（必須）

セッション名・ウィンドウ名・ペイン構造を変更する際は、以下の5ファイル全てを確認:

| ファイル | 確認項目 |
|---------|---------|
| src/ensemble/commands/_launch_impl.py | セッション名、ペイン分割、panes.env出力 |
| src/ensemble/templates/scripts/launch.sh | 同上（シェル版） |
| src/ensemble/templates/scripts/pane-setup.sh | セッション参照、ウィンドウ名 |
| .claude/agents/conductor.md | ASCII図、セッション説明 |
| src/ensemble/templates/agents/conductor.md | 同上（テンプレート版） |

### 9.2 テンプレート同期（必須）

- `src/ensemble/templates/` の変更は必ず `.claude/` にも反映
- `ensemble upgrade` コマンドで同期確認
- CI/CDでテンプレート同期チェックを自動化

### 9.3 ドキュメント更新（必須）

以下3ファイルを必ず同時更新:
1. **ARCHITECTURE.md** - 技術詳細
2. **USAGE.md** - 使用例
3. **README.md** - 概要

### 9.4 テスト戦略

各施策の実装時は以下の順序でテスト:
1. **単体テスト** - 新規モジュールの動作確認
2. **統合テスト** - Ensemble全体での動作確認
3. **回帰テスト** - 既存機能が壊れていないか確認

### 9.5 段階的リリース

大規模な変更（P2-1 Faceted Prompting等）は以下の戦略を推奨:
1. **実験ブランチ** - feature/faceted-promptingで開発
2. **ベータ版** - v0.7.0-beta.1としてリリース、フィードバック収集
3. **正式版** - v0.7.0としてリリース

---

## 10. 参考リンク

- **Shogun分析**: docs/research-shogun-analysis.md
- **設計レビュー**: docs/ensemble-design-review.md
- **現在のアーキテクチャ**: docs/ARCHITECTURE.md
- **学習済みルール**: LEARNED.md

---

*本実装計画はEnsemble Worker-1（task-027）によって作成されました。*
*参照: docs/ensemble-design-review.md, docs/research-shogun-analysis.md, docs/ARCHITECTURE.md*

---

## 実装状況

| フェーズ | 状態 | 実装日 |
|---------|------|--------|
| P0: 通信インフラ強化 | ✅ 完了 | 2026-02-11 |
| P1: ワークフロー進化 | ✅ 完了 | 2026-02-11 |
| P2: プロンプト設計改善 | ✅ 完了 | 2026-02-11 |
| P3: 運用機能充実 | ✅ 完了 | 2026-02-11 |

### 統計
- 総テスト数: 342
- 全体カバレッジ: 76%
- バージョン: 0.4.12 → 0.5.0
