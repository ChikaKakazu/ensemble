"""
ダッシュボード更新モジュール

status/dashboard.md を更新してリアルタイムの進捗を表示する。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ensemble.lock import atomic_write


class DashboardUpdater:
    """
    ダッシュボード更新クラス

    Markdownファイルを更新してタスクの進捗状況を表示する。
    """

    def __init__(self, status_dir: Path | None = None) -> None:
        """
        ダッシュボードアップデータを初期化する

        Args:
            status_dir: ステータスディレクトリ（デフォルト: status/）
        """
        self.status_dir = status_dir if status_dir else Path("status")
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_path = self.status_dir / "dashboard.md"

        # 内部状態
        self._phase = "idle"
        self._current_task = ""
        self._completed = 0
        self._total = 0
        self._agents: dict[str, dict[str, str]] = {}
        self._logs: list[str] = []

        # 初期化時にダッシュボードを作成
        self._write_dashboard()

    def update_status(
        self,
        phase: str,
        current_task: str,
        agents: dict[str, str] | None = None,
    ) -> None:
        """
        ステータスを更新する

        Args:
            phase: 現在のフェーズ
            current_task: 現在のタスク
            agents: エージェントステータス {"name": "status"}
        """
        self._phase = phase
        self._current_task = current_task
        if agents:
            for name, status in agents.items():
                self._agents[name] = {"status": status, "task": ""}
        self._write_dashboard()

    def add_log_entry(self, message: str) -> None:
        """
        ログエントリを追加する

        Args:
            message: ログメッセージ
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._logs.append(f"[{timestamp}] {message}")
        # 最新10件のみ保持
        self._logs = self._logs[-10:]
        self._write_dashboard()

    def set_phase(self, phase: str) -> None:
        """
        フェーズを設定する

        Args:
            phase: フェーズ名
        """
        self._phase = phase
        self._write_dashboard()

    def set_progress(self, completed: int, total: int) -> None:
        """
        進捗を設定する

        Args:
            completed: 完了タスク数
            total: 総タスク数
        """
        self._completed = completed
        self._total = total
        self._write_dashboard()

    def set_agent_status(
        self, name: str, status: str, task: str = ""
    ) -> None:
        """
        エージェントのステータスを設定する

        Args:
            name: エージェント名
            status: ステータス
            task: 実行中のタスク
        """
        self._agents[name] = {"status": status, "task": task}
        self._write_dashboard()

    def clear(self) -> None:
        """
        ダッシュボードをリセットする
        """
        self._phase = "idle"
        self._current_task = ""
        self._completed = 0
        self._total = 0
        self._agents = {}
        self._logs = []
        self._write_dashboard()

    def _write_dashboard(self) -> None:
        """ダッシュボードファイルを書き込む"""
        now = datetime.now()

        # エージェントテーブル
        agent_rows = ""
        for name, info in self._agents.items():
            agent_rows += f"| {name} | {info['status']} | {info.get('task', '')} |\n"
        if not agent_rows:
            agent_rows = "| - | - | - |\n"

        # ログセクション
        log_section = "\n".join(self._logs) if self._logs else "(no logs)"

        # 進捗表示
        if self._total > 0:
            progress = f"{self._completed}/{self._total}"
        else:
            progress = "-"

        content = f"""# Ensemble Dashboard

**Last Updated**: {now.strftime("%Y-%m-%d %H:%M:%S")}

## Status

| Phase | Current Task | Progress |
|-------|--------------|----------|
| {self._phase} | {self._current_task} | {progress} |

## Agents

| Agent | Status | Task |
|-------|--------|------|
{agent_rows}
## Recent Logs

```
{log_section}
```
"""
        atomic_write(str(self.dashboard_path), content)
