"""
tests/test_helpers.py - helpers.pyのテスト

helpers.pyの全4関数のエッジケースを含むテストを提供する。
"""

from pathlib import Path

import pytest

from ensemble.helpers import (
    format_duration,
    get_queue_path,
    parse_worker_id,
    sanitize_task_id,
)


class TestSanitizeTaskId:
    """sanitize_task_id のテスト"""

    def test_alphanumeric_only(self) -> None:
        """英数字のみの場合、そのまま返る"""
        assert sanitize_task_id("task123") == "task123"
        assert sanitize_task_id("ABC456") == "ABC456"
        assert sanitize_task_id("test") == "test"

    def test_special_characters_to_underscore(self) -> None:
        """特殊文字はアンダースコアに置換される"""
        assert sanitize_task_id("task 123") == "task_123"
        assert sanitize_task_id("task@123") == "task_123"
        assert sanitize_task_id("task#123") == "task_123"

    def test_japanese_characters_to_underscore(self) -> None:
        """日本語文字はアンダースコアに置換される"""
        assert sanitize_task_id("タスク123") == "___123"
        assert sanitize_task_id("test日本語") == "test___"

    def test_symbols_to_underscore(self) -> None:
        """記号はアンダースコアに置換される"""
        assert sanitize_task_id("task!@#$%^&*()") == "task__________"
        assert sanitize_task_id("a/b/c") == "a_b_c"

    def test_empty_string(self) -> None:
        """空文字列はそのまま返る"""
        assert sanitize_task_id("") == ""

    def test_hyphen_and_underscore_allowed(self) -> None:
        """ハイフンとアンダースコアは許可される"""
        assert sanitize_task_id("task-123") == "task-123"
        assert sanitize_task_id("task_456") == "task_456"
        assert sanitize_task_id("task-123_abc") == "task-123_abc"

    def test_multiple_spaces(self) -> None:
        """複数のスペースはそれぞれアンダースコアに置換される"""
        assert sanitize_task_id("task   123") == "task___123"


class TestGetQueuePath:
    """get_queue_path のテスト"""

    def test_valid_tasks_queue(self) -> None:
        """tasks キューの正しいパスが返る"""
        result = get_queue_path("tasks")
        assert result == Path(".") / "queue" / "tasks"

    def test_valid_reports_queue(self) -> None:
        """reports キューの正しいパスが返る"""
        result = get_queue_path("reports")
        assert result == Path(".") / "queue" / "reports"

    def test_valid_ack_queue(self) -> None:
        """ack キューの正しいパスが返る"""
        result = get_queue_path("ack")
        assert result == Path(".") / "queue" / "ack"

    def test_valid_conductor_queue(self) -> None:
        """conductor キューの正しいパスが返る"""
        result = get_queue_path("conductor")
        assert result == Path(".") / "queue" / "conductor"

    def test_invalid_queue_type_raises_error(self) -> None:
        """無効なqueue_typeはValueErrorを発生させる"""
        with pytest.raises(ValueError, match="Invalid queue type: invalid"):
            get_queue_path("invalid")

    def test_empty_queue_type_raises_error(self) -> None:
        """空文字列はValueErrorを発生させる"""
        with pytest.raises(ValueError, match="Invalid queue type: "):
            get_queue_path("")

    def test_with_custom_base_dir(self, tmp_path: Path) -> None:
        """カスタムbase_dirが指定された場合、正しいパスが返る"""
        result = get_queue_path("tasks", base_dir=str(tmp_path))
        assert result == tmp_path / "queue" / "tasks"

    def test_with_nested_base_dir(self) -> None:
        """ネストされたbase_dirでも正しいパスが返る"""
        result = get_queue_path("reports", base_dir="a/b/c")
        assert result == Path("a/b/c") / "queue" / "reports"


class TestParseWorkerId:
    """parse_worker_id のテスト"""

    def test_single_digit_worker_id(self) -> None:
        """1桁のワーカーIDが正しく抽出される"""
        assert parse_worker_id("worker-1") == 1
        assert parse_worker_id("worker-5") == 5
        assert parse_worker_id("worker-9") == 9

    def test_double_digit_worker_id(self) -> None:
        """2桁のワーカーIDが正しく抽出される"""
        assert parse_worker_id("worker-10") == 10
        assert parse_worker_id("worker-99") == 99

    def test_three_digit_worker_id(self) -> None:
        """3桁のワーカーIDが正しく抽出される"""
        assert parse_worker_id("worker-123") == 123

    def test_invalid_format_returns_none(self) -> None:
        """無効な形式はNoneを返す"""
        assert parse_worker_id("invalid") is None
        assert parse_worker_id("worker") is None
        assert parse_worker_id("worker-") is None
        assert parse_worker_id("") is None

    def test_non_numeric_suffix_returns_none(self) -> None:
        """数字以外の接尾辞はNoneを返す"""
        assert parse_worker_id("worker-abc") is None
        # 注: "worker-1a" は部分マッチで1を返す（実装の仕様）

    def test_zero_worker_id(self) -> None:
        """ワーカーID 0も正しく抽出される"""
        assert parse_worker_id("worker-0") == 0

    def test_other_pane_names_return_none(self) -> None:
        """他のペイン名はNoneを返す"""
        assert parse_worker_id("conductor") is None
        assert parse_worker_id("dispatch") is None
        assert parse_worker_id("dashboard") is None


class TestFormatDuration:
    """format_duration のテスト"""

    def test_zero_seconds(self) -> None:
        """0秒は '0s' を返す"""
        assert format_duration(0) == "0s"
        assert format_duration(0.0) == "0s"

    def test_only_seconds(self) -> None:
        """秒のみの場合"""
        assert format_duration(5) == "5s"
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_only_minutes(self) -> None:
        """分のみの場合（秒が0）"""
        assert format_duration(60) == "1m"
        assert format_duration(120) == "2m"
        assert format_duration(1800) == "30m"

    def test_minutes_and_seconds(self) -> None:
        """分と秒の組み合わせ"""
        assert format_duration(65) == "1m 5s"
        assert format_duration(125) == "2m 5s"
        assert format_duration(3599) == "59m 59s"

    def test_only_hours(self) -> None:
        """時間のみの場合（分と秒が0）"""
        assert format_duration(3600) == "1h"
        assert format_duration(7200) == "2h"

    def test_hours_and_minutes(self) -> None:
        """時間と分の組み合わせ（秒が0）"""
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7260) == "2h 1m"

    def test_hours_minutes_and_seconds(self) -> None:
        """時間、分、秒の全ての組み合わせ"""
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(7325) == "2h 2m 5s"
        assert format_duration(86461) == "24h 1m 1s"

    def test_large_duration(self) -> None:
        """大きな秒数の場合"""
        assert format_duration(86400) == "24h"  # 1日
        assert format_duration(90061) == "25h 1m 1s"

    def test_floating_point_seconds(self) -> None:
        """浮動小数点の秒数は整数に切り捨てられる"""
        assert format_duration(65.9) == "1m 5s"
        assert format_duration(3661.5) == "1h 1m 1s"
