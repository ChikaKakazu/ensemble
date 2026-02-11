"""
tests/test_utils.py - utils.pyのテスト

utils.pyの全3関数のエッジケースを含むテストを提供する。
"""

from datetime import datetime

import pytest

from ensemble.utils import deep_merge, format_timestamp, truncate_string


class TestFormatTimestamp:
    """format_timestamp のテスト"""

    def test_without_argument_returns_current_time(self) -> None:
        """引数なしの場合、現在時刻のISO8601形式を返す"""
        result = format_timestamp()
        # ISO8601形式であることを確認（基本チェック）
        assert "T" in result
        assert isinstance(result, str)
        # 現在時刻に近いことを確認（数秒以内）
        parsed = datetime.fromisoformat(result)
        now = datetime.now()
        assert abs((now - parsed).total_seconds()) < 2

    def test_with_datetime_argument_returns_formatted_string(self) -> None:
        """datetime引数を指定した場合、その時刻のISO8601形式を返す"""
        dt = datetime(2025, 2, 11, 15, 30, 45)
        result = format_timestamp(dt)
        assert result == "2025-02-11T15:30:45"

    def test_with_microseconds(self) -> None:
        """マイクロ秒を含む時刻も正しくフォーマットされる"""
        dt = datetime(2025, 2, 11, 15, 30, 45, 123456)
        result = format_timestamp(dt)
        assert result == "2025-02-11T15:30:45.123456"

    def test_midnight(self) -> None:
        """00:00:00も正しくフォーマットされる"""
        dt = datetime(2025, 1, 1, 0, 0, 0)
        result = format_timestamp(dt)
        assert result == "2025-01-01T00:00:00"

    def test_end_of_day(self) -> None:
        """23:59:59も正しくフォーマットされる"""
        dt = datetime(2025, 12, 31, 23, 59, 59)
        result = format_timestamp(dt)
        assert result == "2025-12-31T23:59:59"

    def test_leap_year_date(self) -> None:
        """閏年の2月29日も正しくフォーマットされる"""
        dt = datetime(2024, 2, 29, 12, 0, 0)
        result = format_timestamp(dt)
        assert result == "2024-02-29T12:00:00"


class TestTruncateString:
    """truncate_string のテスト"""

    def test_short_string_unchanged(self) -> None:
        """max_length以下の文字列はそのまま返る"""
        assert truncate_string("short", max_length=100) == "short"
        assert truncate_string("exactly 10", max_length=10) == "exactly 10"

    def test_long_string_truncated(self) -> None:
        """max_lengthを超える文字列は切り詰められる"""
        text = "a" * 150
        result = truncate_string(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")
        assert result == "a" * 97 + "..."

    def test_default_max_length(self) -> None:
        """max_lengthのデフォルト値は100"""
        text = "a" * 150
        result = truncate_string(text)
        assert len(result) == 100
        assert result.endswith("...")

    def test_default_suffix(self) -> None:
        """デフォルトのsuffixは '...' """
        text = "a" * 150
        result = truncate_string(text, max_length=100)
        assert result.endswith("...")

    def test_custom_suffix(self) -> None:
        """カスタムsuffixが使用される"""
        text = "a" * 150
        result = truncate_string(text, max_length=100, suffix="<more>")
        assert len(result) == 100
        assert result.endswith("<more>")
        assert result == "a" * 94 + "<more>"

    def test_empty_suffix(self) -> None:
        """空のsuffixも使用できる"""
        text = "a" * 150
        result = truncate_string(text, max_length=100, suffix="")
        assert len(result) == 100
        assert result == "a" * 100

    def test_max_length_zero(self) -> None:
        """max_length=0の境界値"""
        result = truncate_string("test", max_length=0, suffix="...")
        # utils.pyの実装: s[:max_length - len(suffix)] + suffix
        # s[:0 - 3] + "..." = s[:-3] + "..." = "t" + "..." = "t..."
        assert result == "t..."

    def test_unicode_characters(self) -> None:
        """Unicode文字も正しく切り詰められる"""
        text = "日本語" * 50  # 150文字
        result = truncate_string(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_exact_length_with_suffix(self) -> None:
        """max_lengthがちょうどsuffixの長さの場合"""
        text = "test string"
        result = truncate_string(text, max_length=3, suffix="...")
        # s[:3-3] + "..." = s[:0] + "..." = "" + "..." = "..."
        assert result == "..."

    def test_max_length_less_than_suffix(self) -> None:
        """max_lengthがsuffixより短い場合（エッジケース）"""
        text = "test string"
        result = truncate_string(text, max_length=2, suffix="...")
        # s[:2-3] + "..." = s[:-1] + "..." = "test strin" + "..."
        # 実装では s[:max_length - len(suffix)] = s[:2-3] = s[:-1]
        assert result == "test strin..."


class TestDeepMerge:
    """deep_merge のテスト"""

    def test_flat_dict_merge(self) -> None:
        """フラットな辞書のマージ"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_dict_merge(self) -> None:
        """ネストした辞書のマージ"""
        base = {"a": 1, "nested": {"x": 10, "y": 20}}
        override = {"nested": {"y": 30, "z": 40}}
        result = deep_merge(base, override)
        assert result == {"a": 1, "nested": {"x": 10, "y": 30, "z": 40}}

    def test_base_dict_unchanged(self) -> None:
        """元の辞書が変更されないことを確認"""
        base = {"a": 1, "nested": {"x": 10}}
        override = {"nested": {"x": 20}}
        original_base = base.copy()
        original_nested = base["nested"].copy()

        result = deep_merge(base, override)

        # baseが変更されていないことを確認
        assert base["a"] == original_base["a"]
        # ネストした部分も変更されていないことを確認
        assert base["nested"]["x"] == original_nested["x"]
        # 結果は期待通り
        assert result["nested"]["x"] == 20

    def test_empty_override(self) -> None:
        """空の上書き辞書のマージ（baseのコピーが返る）"""
        base = {"a": 1, "b": 2}
        override = {}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_empty_base(self) -> None:
        """空のベース辞書のマージ（overrideが返る）"""
        base = {}
        override = {"a": 1, "b": 2}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_both_empty(self) -> None:
        """両方空の辞書のマージ"""
        base = {}
        override = {}
        result = deep_merge(base, override)
        assert result == {}

    def test_deep_nested_merge(self) -> None:
        """3階層以上のネストしたマージ"""
        base = {"level1": {"level2": {"level3": {"a": 1, "b": 2}}}}
        override = {"level1": {"level2": {"level3": {"b": 3, "c": 4}}}}
        result = deep_merge(base, override)
        assert result == {"level1": {"level2": {"level3": {"a": 1, "b": 3, "c": 4}}}}

    def test_override_dict_with_non_dict(self) -> None:
        """辞書を非辞書で上書き"""
        base = {"a": {"nested": 1}}
        override = {"a": "string"}
        result = deep_merge(base, override)
        assert result == {"a": "string"}

    def test_override_non_dict_with_dict(self) -> None:
        """非辞書を辞書で上書き"""
        base = {"a": "string"}
        override = {"a": {"nested": 1}}
        result = deep_merge(base, override)
        assert result == {"a": {"nested": 1}}

    def test_mixed_types(self) -> None:
        """異なる型の値のマージ"""
        base = {"a": 1, "b": "string", "c": [1, 2, 3], "d": {"nested": True}}
        override = {"b": "new_string", "c": [4, 5], "d": {"nested": False, "new": "value"}}
        result = deep_merge(base, override)
        assert result == {
            "a": 1,
            "b": "new_string",
            "c": [4, 5],
            "d": {"nested": False, "new": "value"},
        }
