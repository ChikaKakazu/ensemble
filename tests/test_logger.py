"""EnsembleLogger のテスト"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ensemble.logger import EnsembleLogger


class TestEnsembleLogger:
    """EnsembleLogger のテスト"""

    def test_init_creates_log_directory(self, tmp_path: Path) -> None:
        """ログディレクトリが作成されることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)
        assert log_dir.exists()

    def test_log_writes_json_to_file(self, tmp_path: Path) -> None:
        """ファイルにJSON形式で出力されることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.log("INFO", "Test message", task_id="test-123")

        # ログファイルを確認
        log_files = list(log_dir.glob("ensemble-*.log"))
        assert len(log_files) == 1

        with open(log_files[0]) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["level"] == "INFO"
        assert entry["message"] == "Test message"
        assert entry["task_id"] == "test-123"
        assert "timestamp" in entry

    def test_log_outputs_text_to_console(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """コンソールにテキスト形式で出力されることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.log("INFO", "Console test")

        captured = capsys.readouterr()
        assert "[INFO]" in captured.out
        assert "Console test" in captured.out

    def test_log_levels(self, tmp_path: Path) -> None:
        """各ログレベルが正しく記録されることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        for level in levels:
            logger.log(level, f"Message at {level}")

        log_files = list(log_dir.glob("ensemble-*.log"))
        with open(log_files[0]) as f:
            lines = f.readlines()

        assert len(lines) == 4
        for i, level in enumerate(levels):
            entry = json.loads(lines[i])
            assert entry["level"] == level

    def test_info_shortcut(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """info() ショートカットメソッドのテスト"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.info("Info message")

        captured = capsys.readouterr()
        assert "[INFO]" in captured.out
        assert "Info message" in captured.out

    def test_error_shortcut(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """error() ショートカットメソッドのテスト"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.error("Error message")

        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "Error message" in captured.out

    def test_warning_shortcut(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """warning() ショートカットメソッドのテスト"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.warning("Warning message")

        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "Warning message" in captured.out

    def test_debug_shortcut(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """debug() ショートカットメソッドのテスト"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.debug("Debug message")

        captured = capsys.readouterr()
        assert "[DEBUG]" in captured.out
        assert "Debug message" in captured.out

    def test_log_with_multiple_kwargs(self, tmp_path: Path) -> None:
        """複数のkwargsが正しくJSONに記録されることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.log(
            "INFO",
            "Complex log",
            task_id="task-456",
            agent="conductor",
            duration_ms=1234,
        )

        log_files = list(log_dir.glob("ensemble-*.log"))
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())

        assert entry["task_id"] == "task-456"
        assert entry["agent"] == "conductor"
        assert entry["duration_ms"] == 1234

    def test_log_file_naming_includes_date(self, tmp_path: Path) -> None:
        """ログファイル名に日付が含まれることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.log("INFO", "Date test")

        log_files = list(log_dir.glob("ensemble-*.log"))
        assert len(log_files) == 1

        today = datetime.now().strftime("%Y%m%d")
        assert today in log_files[0].name

    def test_timestamp_format_is_iso(self, tmp_path: Path) -> None:
        """タイムスタンプがISO形式であることを確認"""
        log_dir = tmp_path / "logs"
        logger = EnsembleLogger(log_dir=log_dir)

        logger.log("INFO", "Timestamp test")

        log_files = list(log_dir.glob("ensemble-*.log"))
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())

        # ISO形式でパース可能であることを確認
        timestamp = entry["timestamp"]
        datetime.fromisoformat(timestamp)  # パース失敗時は例外
