"""
src/ensemble/helpers.py - ヘルパー関数

Ensemble固有のヘルパー関数を提供する。
"""

import re
from pathlib import Path


def sanitize_task_id(task_id: str) -> str:
    """
    タスクIDをサニタイズする

    Args:
        task_id: サニタイズするタスクID

    Returns:
        サニタイズされたタスクID
    """
    # 英数字、ハイフン、アンダースコアのみ許可
    return re.sub(r"[^a-zA-Z0-9\-_]", "_", task_id)


def get_queue_path(queue_type: str, base_dir: str = ".") -> Path:
    """
    キューディレクトリのパスを取得する

    Args:
        queue_type: キューの種類（tasks, reports, ack）
        base_dir: ベースディレクトリ

    Returns:
        キューディレクトリのパス
    """
    valid_types = {"tasks", "reports", "ack", "conductor"}
    if queue_type not in valid_types:
        raise ValueError(f"Invalid queue type: {queue_type}")
    return Path(base_dir) / "queue" / queue_type


def parse_worker_id(pane_name: str) -> int | None:
    """
    ペイン名からワーカーIDを抽出する

    Args:
        pane_name: ペイン名（例: "worker-1", "worker-2"）

    Returns:
        ワーカーID。抽出できない場合はNone
    """
    match = re.match(r"worker-(\d+)", pane_name)
    if match:
        return int(match.group(1))
    return None


def format_duration(seconds: float) -> str:
    """
    秒数を人間が読みやすい形式に変換する

    Args:
        seconds: 秒数

    Returns:
        "1h 23m 45s" 形式の文字列
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
