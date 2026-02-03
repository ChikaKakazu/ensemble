"""
src/ensemble/utils.py - ユーティリティ関数

汎用的なユーティリティ関数を提供する。
"""

from datetime import datetime
from typing import Any


def format_timestamp(dt: datetime | None = None) -> str:
    """
    日時をISO8601形式の文字列に変換する

    Args:
        dt: 変換する日時。Noneの場合は現在時刻

    Returns:
        ISO8601形式の文字列
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    文字列を指定した長さに切り詰める

    Args:
        s: 切り詰める文字列
        max_length: 最大長
        suffix: 切り詰め時に追加する接尾辞

    Returns:
        切り詰められた文字列
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    2つの辞書を深くマージする

    Args:
        base: ベースとなる辞書
        override: 上書きする辞書

    Returns:
        マージされた辞書
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
