"""
ファイルベースのタスクキュー

アトミック操作でタスクの配信・取得・完了報告を行う。
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ensemble.lock import atomic_claim, atomic_write


class TaskQueue:
    """
    ファイルベースのタスクキュー

    構造:
        queue/
        ├── tasks/       # 保留中のタスク
        ├── processing/  # 処理中のタスク
        └── reports/     # 完了報告
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        """
        キューを初期化する

        Args:
            base_dir: ベースディレクトリ（デフォルト: queue/）
        """
        self.base_dir = base_dir if base_dir else Path("queue")
        self.tasks_dir = self.base_dir / "tasks"
        self.processing_dir = self.base_dir / "processing"
        self.reports_dir = self.base_dir / "reports"

        # ディレクトリ作成
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        command: str,
        agent: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        タスクをキューに追加する

        Args:
            command: 実行するコマンド
            agent: 担当エージェント
            params: 追加パラメータ

        Returns:
            タスクID
        """
        task_id = self._generate_task_id()

        task = {
            "task_id": task_id,
            "command": command,
            "agent": agent,
            "params": params or {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        task_file = self.tasks_dir / f"{task_id}.yaml"
        content = yaml.dump(task, allow_unicode=True, default_flow_style=False)
        atomic_write(str(task_file), content)

        return task_id

    def claim(self) -> dict[str, Any] | None:
        """
        タスクを取得する（アトミック）

        Returns:
            タスクデータ、またはキューが空の場合None
        """
        # 最も古いタスクを取得（ファイル名でソート）
        task_files = sorted(self.tasks_dir.glob("*.yaml"))

        for task_file in task_files:
            result = atomic_claim(str(task_file), str(self.processing_dir))
            if result:
                with open(result) as f:
                    return yaml.safe_load(f)

        return None

    def complete(
        self,
        task_id: str,
        result: str,
        output: str,
        error: str | None = None,
    ) -> None:
        """
        タスク完了を報告する

        Args:
            task_id: タスクID
            result: 結果 ("success" or "error")
            output: 出力内容
            error: エラーメッセージ（エラー時のみ）
        """
        processing_file = self.processing_dir / f"{task_id}.yaml"

        # 元のタスク情報を読み込み
        if processing_file.exists():
            with open(processing_file) as f:
                task = yaml.safe_load(f)
        else:
            task = {"task_id": task_id}

        # レポート作成
        report = {
            **task,
            "result": result,
            "output": output,
            "completed_at": datetime.now().isoformat(),
        }
        if error:
            report["error"] = error

        # reportsに保存
        report_file = self.reports_dir / f"{task_id}.yaml"
        content = yaml.dump(report, allow_unicode=True, default_flow_style=False)
        atomic_write(str(report_file), content)

        # processingから削除
        if processing_file.exists():
            processing_file.unlink()

    def list_pending(self) -> list[str]:
        """
        保留中のタスクIDリストを取得する

        Returns:
            タスクIDのリスト
        """
        task_files = self.tasks_dir.glob("*.yaml")
        return [f.stem for f in task_files]

    def cleanup(self) -> None:
        """
        全てのファイルを削除する（セッション開始時用）
        """
        for dir_path in [self.tasks_dir, self.processing_dir, self.reports_dir]:
            for f in dir_path.glob("*.yaml"):
                f.unlink()

    def _generate_task_id(self) -> str:
        """ユニークなタスクIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"{timestamp}-{short_uuid}"
