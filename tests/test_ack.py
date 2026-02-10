"""ACK機構のテスト"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestAckManagerEscalation:
    """AckManager の3段階エスカレーション機能のテスト"""

    @pytest.fixture
    def ack_manager(self, tmp_path: Path) -> AckManager:
        """テスト用ACKマネージャを作成"""
        return AckManager(ack_dir=tmp_path / "ack")

    def test_wait_with_escalation_immediate_ack(
        self, ack_manager: AckManager
    ) -> None:
        """Phase 1前にACK受信する場合のテスト"""
        task_id = "task-immediate"

        # 事前にACKを送信
        ack_manager.send(task_id, "worker-1")

        with patch("subprocess.run") as mock_run:
            success, phase = ack_manager.wait_with_escalation(
                task_id=task_id,
                worker_id=1,
                pane_id="%3",
                phase_timeout=0.1,
                max_phases=3,
            )

            # エスカレーション不要でACK受信成功
            assert success is True
            assert phase == 0
            # escalate.shは呼ばれない
            mock_run.assert_not_called()

    def test_wait_with_escalation_phase1_ack(
        self, ack_manager: AckManager
    ) -> None:
        """Phase 1 nudge後にACK受信する場合のテスト"""
        task_id = "task-phase1"

        with patch("subprocess.run") as mock_run:
            # Phase 1エスカレーション後、ACKを送信
            def send_ack_after_phase1(args, **kwargs):
                if "1" in args:  # Phase 1判定
                    ack_manager.send(task_id, "worker-1")

            mock_run.side_effect = send_ack_after_phase1

            success, phase = ack_manager.wait_with_escalation(
                task_id=task_id,
                worker_id=1,
                pane_id="%3",
                phase_timeout=0.1,
                max_phases=3,
            )

            # Phase 1でACK受信成功
            assert success is True
            assert phase == 1
            # escalate.shが1回呼ばれた
            assert mock_run.call_count == 1

    def test_wait_with_escalation_all_phases_fail(
        self, ack_manager: AckManager
    ) -> None:
        """全フェーズ失敗の場合のテスト"""
        task_id = "task-allfail"

        with patch("subprocess.run") as mock_run:
            success, phase = ack_manager.wait_with_escalation(
                task_id=task_id,
                worker_id=2,
                pane_id="%4",
                phase_timeout=0.1,
                max_phases=3,
            )

            # 全フェーズ失敗
            assert success is False
            assert phase == 3
            # escalate.shが3回呼ばれた（Phase 1, 2, 3）
            assert mock_run.call_count == 3

    def test_escalate_script_exists(self) -> None:
        """escalate.shの存在確認"""
        escalate_script = Path("src/ensemble/templates/scripts/escalate.sh")
        assert (
            escalate_script.exists()
        ), f"escalate.sh not found at {escalate_script}"

    def test_escalate_script_executable(self) -> None:
        """escalate.shの実行権限確認"""
        escalate_script = Path("src/ensemble/templates/scripts/escalate.sh")
        if escalate_script.exists():
            import os

            assert os.access(
                escalate_script, os.X_OK
            ), f"escalate.sh is not executable"
