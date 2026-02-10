"""NDJSONLogger のテスト"""

import json
import threading
import time
from pathlib import Path

import pytest

from ensemble.logger import NDJSONLogger


class TestNDJSONLogger:
    """NDJSONLogger の基本機能テスト"""

    @pytest.fixture
    def logger(self, tmp_path: Path) -> NDJSONLogger:
        """テスト用NDJSONロガーを作成"""
        return NDJSONLogger(log_dir=tmp_path / "logs", session_id="test-session")

    def test_log_event_creates_file(self, logger: NDJSONLogger, tmp_path: Path) -> None:
        """ログファイルが作成されることを確認"""
        logger.log_event("test_event", {"key": "value"})

        log_file = tmp_path / "logs" / "test-session.ndjson"
        assert log_file.exists()

    def test_log_event_ndjson_format(
        self, logger: NDJSONLogger, tmp_path: Path
    ) -> None:
        """各行がvalid JSONであることを確認"""
        logger.log_event("event1", {"key1": "value1"})
        logger.log_event("event2", {"key2": "value2"})

        log_file = tmp_path / "logs" / "test-session.ndjson"
        with open(log_file) as f:
            lines = f.readlines()

        # 各行が valid JSON
        for line in lines:
            line = line.strip()
            if line:
                event = json.loads(line)  # エラーなく解析できる
                assert "timestamp" in event
                assert "session_id" in event
                assert "type" in event
                assert "data" in event

    def test_log_task_start(self, logger: NDJSONLogger) -> None:
        """task_startイベントの内容確認"""
        logger.log_task_start(
            task_id="task-001", worker_id=1, files=["file1.py", "file2.py"]
        )

        events = logger.read_events(event_type=NDJSONLogger.TASK_START)
        # session_start + task_start の2イベントがあるはず
        task_start_events = [
            e for e in events if e["data"].get("task_id") == "task-001"
        ]
        assert len(task_start_events) == 1

        event = task_start_events[0]
        assert event["type"] == NDJSONLogger.TASK_START
        assert event["data"]["task_id"] == "task-001"
        assert event["data"]["worker_id"] == 1
        assert event["data"]["files"] == ["file1.py", "file2.py"]

    def test_log_task_complete(self, logger: NDJSONLogger) -> None:
        """task_completeイベントの内容確認"""
        logger.log_task_complete(
            task_id="task-002", worker_id=2, status="success", duration_seconds=120.5
        )

        events = logger.read_events(event_type=NDJSONLogger.TASK_COMPLETE)
        assert len(events) == 1

        event = events[0]
        assert event["type"] == NDJSONLogger.TASK_COMPLETE
        assert event["data"]["task_id"] == "task-002"
        assert event["data"]["worker_id"] == 2
        assert event["data"]["status"] == "success"
        assert event["data"]["duration_seconds"] == 120.5

    def test_log_review_result(self, logger: NDJSONLogger) -> None:
        """review_resultイベントの内容確認"""
        logger.log_review_result(
            task_id="task-003",
            reviewer="reviewer-1",
            result="approved",
            findings_count=0,
        )

        events = logger.read_events(event_type=NDJSONLogger.REVIEW_RESULT)
        assert len(events) == 1

        event = events[0]
        assert event["type"] == NDJSONLogger.REVIEW_RESULT
        assert event["data"]["task_id"] == "task-003"
        assert event["data"]["reviewer"] == "reviewer-1"
        assert event["data"]["result"] == "approved"
        assert event["data"]["findings_count"] == 0

    def test_log_escalation(self, logger: NDJSONLogger) -> None:
        """escalationイベントの内容確認"""
        logger.log_escalation(worker_id=1, phase=2, reason="timeout")

        events = logger.read_events(event_type=NDJSONLogger.ESCALATION)
        assert len(events) == 1

        event = events[0]
        assert event["type"] == NDJSONLogger.ESCALATION
        assert event["data"]["worker_id"] == 1
        assert event["data"]["phase"] == 2
        assert event["data"]["reason"] == "timeout"

    def test_log_loop_detected(self, logger: NDJSONLogger) -> None:
        """loop_detectedイベントの内容確認"""
        logger.log_loop_detected(
            task_id="task-004", iteration_count=6, max_iterations=5
        )

        events = logger.read_events(event_type=NDJSONLogger.LOOP_DETECTED)
        assert len(events) == 1

        event = events[0]
        assert event["type"] == NDJSONLogger.LOOP_DETECTED
        assert event["data"]["task_id"] == "task-004"
        assert event["data"]["iteration_count"] == 6
        assert event["data"]["max_iterations"] == 5

    def test_read_events_all(self, logger: NDJSONLogger) -> None:
        """全イベント読み込み"""
        logger.log_task_start(task_id="task-001", worker_id=1)
        logger.log_task_complete(
            task_id="task-001", worker_id=1, status="success", duration_seconds=60.0
        )
        logger.log_review_result(
            task_id="task-001", reviewer="reviewer-1", result="approved"
        )

        events = logger.read_events()
        # session_start + task_start + task_complete + review_result = 4イベント
        assert len(events) >= 4

    def test_read_events_filtered(self, logger: NDJSONLogger) -> None:
        """イベントタイプフィルタ"""
        logger.log_task_start(task_id="task-001", worker_id=1)
        logger.log_task_complete(
            task_id="task-001", worker_id=1, status="success", duration_seconds=60.0
        )
        logger.log_escalation(worker_id=1, phase=1)

        # task_startのみ取得
        task_start_events = logger.read_events(event_type=NDJSONLogger.TASK_START)
        # session_startの分もあるので、task_startのみを抽出
        task_starts = [
            e for e in task_start_events if e["data"].get("task_id") == "task-001"
        ]
        assert len(task_starts) == 1

        # escalationのみ取得
        escalation_events = logger.read_events(event_type=NDJSONLogger.ESCALATION)
        assert len(escalation_events) == 1

    def test_get_session_summary(self, logger: NDJSONLogger) -> None:
        """サマリー生成テスト"""
        logger.log_task_start(task_id="task-001", worker_id=1)
        logger.log_task_complete(
            task_id="task-001", worker_id=1, status="success", duration_seconds=60.0
        )
        logger.log_task_start(task_id="task-002", worker_id=2)
        logger.log_task_complete(
            task_id="task-002", worker_id=2, status="failed", duration_seconds=30.0
        )
        logger.log_escalation(worker_id=2, phase=1)

        summary = logger.get_session_summary()

        assert summary["session_id"] == "test-session"
        assert summary["total_events"] >= 6  # session_start + 5イベント
        assert summary["task_count"] == 2  # task-001, task-002
        assert summary["success_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["escalation_count"] == 1
        assert summary["duration_seconds"] >= 0

    def test_concurrent_logging(self, tmp_path: Path) -> None:
        """並列ログ書き込みテスト（threadingで10スレッド同時書き込み）"""
        logger = NDJSONLogger(log_dir=tmp_path / "logs", session_id="concurrent-test")

        def log_events(thread_id: int, count: int = 10):
            for i in range(count):
                logger.log_event(
                    "thread_event", {"thread_id": thread_id, "event_num": i}
                )
                time.sleep(0.001)  # 少し待機してレース条件を誘発

        # 10スレッドで同時にログ書き込み
        threads = []
        for i in range(10):
            t = threading.Thread(target=log_events, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 全イベントが書き込まれていることを確認
        events = logger.read_events(event_type="thread_event")
        assert len(events) == 100  # 10スレッド × 10イベント

        # 各スレッドのイベントが正しく記録されていることを確認
        for thread_id in range(10):
            thread_events = [
                e for e in events if e["data"].get("thread_id") == thread_id
            ]
            assert len(thread_events) == 10

    def test_unicode_support(self, logger: NDJSONLogger) -> None:
        """日本語データのログ出力"""
        logger.log_event("日本語イベント", {"メッセージ": "こんにちは", "数値": 123})

        events = logger.read_events(event_type="日本語イベント")
        assert len(events) == 1

        event = events[0]
        assert event["type"] == "日本語イベント"
        assert event["data"]["メッセージ"] == "こんにちは"
        assert event["data"]["数値"] == 123

    def test_get_log_path(self, logger: NDJSONLogger, tmp_path: Path) -> None:
        """ログファイルパスの取得"""
        log_path = logger.get_log_path()
        assert log_path == tmp_path / "logs" / "test-session.ndjson"

    def test_session_id_auto_generation(self, tmp_path: Path) -> None:
        """session_id自動生成"""
        logger = NDJSONLogger(log_dir=tmp_path / "logs")
        assert logger.session_id.startswith("session-")
        assert len(logger.session_id) > 10  # タイムスタンプが含まれる

    def test_empty_data_handling(self, logger: NDJSONLogger) -> None:
        """dataがNoneの場合の処理"""
        logger.log_event("empty_event", None)

        events = logger.read_events(event_type="empty_event")
        assert len(events) == 1
        assert events[0]["data"] == {}
