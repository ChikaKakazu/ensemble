"""
ACK（受領確認）機構

タスク配信の確認をファイルベースで行う。
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from ensemble.lock import atomic_write


class AckManager:
    """
    ACK管理クラス

    タスク配信後、エージェントからの受領確認を管理する。
    """

    def __init__(self, ack_dir: Path | None = None) -> None:
        """
        ACKマネージャを初期化する

        Args:
            ack_dir: ACKファイル保存ディレクトリ（デフォルト: queue/ack/）
        """
        self.ack_dir = ack_dir if ack_dir else Path("queue/ack")
        self.ack_dir.mkdir(parents=True, exist_ok=True)

    def send(self, task_id: str, agent: str) -> None:
        """
        ACKを送信する

        Args:
            task_id: タスクID
            agent: ACKを送信したエージェント名
        """
        ack_file = self.ack_dir / f"{task_id}.ack"
        content = f"{agent}\n{datetime.now().isoformat()}\n"
        atomic_write(str(ack_file), content)

    def wait(self, task_id: str, timeout: float = 30.0, interval: float = 0.1) -> bool:
        """
        ACKを待機する

        Args:
            task_id: タスクID
            timeout: タイムアウト秒数
            interval: ポーリング間隔

        Returns:
            ACK受信時True、タイムアウト時False
        """
        ack_file = self.ack_dir / f"{task_id}.ack"
        elapsed = 0.0

        while elapsed < timeout:
            if ack_file.exists():
                return True
            time.sleep(interval)
            elapsed += interval

        return False

    def check(self, task_id: str) -> bool:
        """
        ACKが存在するか確認する

        Args:
            task_id: タスクID

        Returns:
            ACK存在時True
        """
        ack_file = self.ack_dir / f"{task_id}.ack"
        return ack_file.exists()

    def cleanup(self) -> None:
        """
        全てのACKファイルを削除する
        """
        for ack_file in self.ack_dir.glob("*.ack"):
            ack_file.unlink()
