"""
Ensembleログ出力モジュール

コンソール: テキスト形式（人間が読みやすい）
ファイル: JSON形式（機械可読、分析容易）
"""

from __future__ import annotations

import fcntl
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class EnsembleLogger:
    """
    Ensemble用ログ出力クラス

    コンソール: テキスト形式（人間が読みやすい）
    ファイル: JSON形式（機械可読、分析容易）
    """

    def __init__(self, name: str = "ensemble", log_dir: Path | None = None) -> None:
        """
        ロガーを初期化する

        Args:
            name: ロガー名
            log_dir: ログ出力ディレクトリ（デフォルト: logs/）
        """
        self.name = name
        self.log_dir = log_dir if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True)

    def _get_log_file(self) -> Path:
        """今日のログファイルパスを取得"""
        today = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"ensemble-{today}.log"

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """
        構造化ログを出力する

        Args:
            level: ログレベル (DEBUG, INFO, WARNING, ERROR)
            message: ログメッセージ
            **kwargs: 追加の構造化データ
        """
        now = datetime.now()

        # コンソール: テキスト形式
        time_str = now.strftime("%H:%M:%S")
        print(f"{time_str} [{level}] {message}")

        # ファイル: JSON形式
        log_entry = {
            "timestamp": now.isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        with open(self._get_log_file(), "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUGレベルでログ出力"""
        self.log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """INFOレベルでログ出力"""
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNINGレベルでログ出力"""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """ERRORレベルでログ出力"""
        self.log("ERROR", message, **kwargs)


class NDJSONLogger:
    """
    NDJSONセッションログ

    .ensemble/logs/session-{timestamp}.ndjson にイベントを追記する。
    各行が独立したJSONオブジェクト（NDJSON形式）。
    """

    # イベントタイプ定数
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    WORKER_ASSIGN = "worker_assign"
    WORKER_RELEASE = "worker_release"
    REVIEW_START = "review_start"
    REVIEW_RESULT = "review_result"
    ESCALATION = "escalation"
    LOOP_DETECTED = "loop_detected"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    DISPATCH_INSTRUCTION = "dispatch_instruction"

    def __init__(
        self, log_dir: Path | None = None, session_id: str | None = None
    ) -> None:
        """
        Args:
            log_dir: ログディレクトリ（デフォルト: .ensemble/logs/）
            session_id: セッションID（デフォルト: タイムスタンプ自動生成）
        """
        self.log_dir = log_dir if log_dir else Path(".ensemble/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if session_id:
            self.session_id = session_id
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.session_id = f"session-{timestamp}"

        self.log_file = self.log_dir / f"{self.session_id}.ndjson"
        self._session_start_time = datetime.now()

        # セッション開始イベントを記録
        self.log_event(self.SESSION_START, {"session_id": self.session_id})

    def log_event(self, event_type: str, data: dict | None = None) -> None:
        """
        イベントをNDJSON形式で追記（アトミック書き込み）

        Args:
            event_type: イベントタイプ（上記定数のいずれか）
            data: イベントデータ

        出力フォーマット:
        {"timestamp": "2026-...", "session_id": "...", "type": "task_start", "data": {...}}
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "type": event_type,
            "data": data or {},
        }

        # fcntl.flockを使用したアトミック追記
        with open(self.log_file, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def log_task_start(
        self, task_id: str, worker_id: int, files: list[str] | None = None
    ) -> None:
        """タスク開始イベント"""
        self.log_event(
            self.TASK_START,
            {"task_id": task_id, "worker_id": worker_id, "files": files or []},
        )

    def log_task_complete(
        self,
        task_id: str,
        worker_id: int,
        status: str,
        duration_seconds: float | None = None,
    ) -> None:
        """タスク完了イベント"""
        self.log_event(
            self.TASK_COMPLETE,
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "status": status,
                "duration_seconds": duration_seconds,
            },
        )

    def log_review_result(
        self, task_id: str, reviewer: str, result: str, findings_count: int = 0
    ) -> None:
        """レビュー結果イベント"""
        self.log_event(
            self.REVIEW_RESULT,
            {
                "task_id": task_id,
                "reviewer": reviewer,
                "result": result,
                "findings_count": findings_count,
            },
        )

    def log_escalation(self, worker_id: int, phase: int, reason: str = "") -> None:
        """エスカレーションイベント"""
        self.log_event(
            self.ESCALATION,
            {"worker_id": worker_id, "phase": phase, "reason": reason},
        )

    def log_loop_detected(
        self, task_id: str, iteration_count: int, max_iterations: int
    ) -> None:
        """ループ検知イベント"""
        self.log_event(
            self.LOOP_DETECTED,
            {
                "task_id": task_id,
                "iteration_count": iteration_count,
                "max_iterations": max_iterations,
            },
        )

    def get_log_path(self) -> Path:
        """現在のログファイルパスを返す"""
        return self.log_file

    def read_events(self, event_type: str | None = None) -> list[dict]:
        """
        ログファイルからイベントを読み込む（分析用）

        Args:
            event_type: フィルタ用。Noneなら全イベント
        """
        if not self.log_file.exists():
            return []

        events = []
        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event_type is None or event.get("type") == event_type:
                        events.append(event)
                except json.JSONDecodeError:
                    continue

        return events

    def get_session_summary(self) -> dict:
        """
        セッションサマリーを生成

        Returns:
            {
                "session_id": "...",
                "total_events": 25,
                "task_count": 5,
                "success_count": 4,
                "failed_count": 1,
                "escalation_count": 0,
                "duration_seconds": 300
            }
        """
        events = self.read_events()

        task_ids = set()
        success_count = 0
        failed_count = 0
        escalation_count = 0

        for event in events:
            event_type = event.get("type")
            data = event.get("data", {})

            if event_type == self.TASK_COMPLETE:
                task_id = data.get("task_id")
                if task_id:
                    task_ids.add(task_id)
                status = data.get("status", "")
                if status == "success":
                    success_count += 1
                elif status in ("failed", "error"):
                    failed_count += 1

            elif event_type == self.ESCALATION:
                escalation_count += 1

        duration_seconds = (
            datetime.now() - self._session_start_time
        ).total_seconds()

        return {
            "session_id": self.session_id,
            "total_events": len(events),
            "task_count": len(task_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "escalation_count": escalation_count,
            "duration_seconds": duration_seconds,
        }
