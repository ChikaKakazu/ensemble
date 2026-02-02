"""ACK機構のテスト"""

import time
from pathlib import Path

import pytest

from ensemble.ack import AckManager


class TestAckManager:
    """AckManager のテスト"""

    @pytest.fixture
    def ack_manager(self, tmp_path: Path) -> AckManager:
        """テスト用ACKマネージャを作成"""
        return AckManager(ack_dir=tmp_path / "ack")

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """初期化時にディレクトリが作成されることを確認"""
        ack_dir = tmp_path / "ack"
        AckManager(ack_dir=ack_dir)
        assert ack_dir.exists()

    def test_send_creates_ack_file(
        self, ack_manager: AckManager, tmp_path: Path
    ) -> None:
        """ACKを送信するとファイルが作成されることを確認"""
        task_id = "task-123"
        agent = "worker-1"

        ack_manager.send(task_id, agent)

        ack_file = tmp_path / "ack" / f"{task_id}.ack"
        assert ack_file.exists()
        assert agent in ack_file.read_text()

    def test_wait_returns_true_when_ack_received(
        self, ack_manager: AckManager
    ) -> None:
        """ACKが受信された場合Trueを返すことを確認"""
        task_id = "task-456"

        # 別スレッドでACKを送信するシミュレーション
        ack_manager.send(task_id, "worker-1")

        result = ack_manager.wait(task_id, timeout=1.0)
        assert result is True

    def test_wait_returns_false_on_timeout(self, ack_manager: AckManager) -> None:
        """タイムアウト時にFalseを返すことを確認"""
        task_id = "task-789"

        result = ack_manager.wait(task_id, timeout=0.1)
        assert result is False

    def test_check_returns_true_if_acked(self, ack_manager: AckManager) -> None:
        """ACK済みの場合Trueを返すことを確認"""
        task_id = "task-abc"
        ack_manager.send(task_id, "worker")

        assert ack_manager.check(task_id) is True

    def test_check_returns_false_if_not_acked(self, ack_manager: AckManager) -> None:
        """未ACKの場合Falseを返すことを確認"""
        task_id = "task-xyz"

        assert ack_manager.check(task_id) is False

    def test_cleanup_removes_ack_files(
        self, ack_manager: AckManager, tmp_path: Path
    ) -> None:
        """cleanupでACKファイルが削除されることを確認"""
        ack_manager.send("task-1", "worker-1")
        ack_manager.send("task-2", "worker-2")

        ack_manager.cleanup()

        ack_dir = tmp_path / "ack"
        assert len(list(ack_dir.glob("*.ack"))) == 0

    def test_send_includes_timestamp(
        self, ack_manager: AckManager, tmp_path: Path
    ) -> None:
        """ACKファイルにタイムスタンプが含まれることを確認"""
        task_id = "task-ts"
        ack_manager.send(task_id, "worker")

        ack_file = tmp_path / "ack" / f"{task_id}.ack"
        content = ack_file.read_text()

        # ISO形式のタイムスタンプを含む
        assert "T" in content  # 簡易チェック
