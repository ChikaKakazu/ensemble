"""ダッシュボード更新ロジックのテスト"""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ensemble.dashboard import DashboardUpdater


class TestDashboardUpdater:
    """DashboardUpdater のテスト"""

    @pytest.fixture
    def updater(self, tmp_path: Path) -> DashboardUpdater:
        """テスト用アップデータを作成"""
        return DashboardUpdater(status_dir=tmp_path)

    def test_init_creates_dashboard_file(self, tmp_path: Path) -> None:
        """初期化時にダッシュボードファイルが作成されることを確認"""
        DashboardUpdater(status_dir=tmp_path)
        assert (tmp_path / "dashboard.md").exists()

    def test_update_status_writes_to_dashboard(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """ステータス更新がダッシュボードに書き込まれることを確認"""
        updater.update_status(
            phase="execute",
            current_task="Building project",
            agents={"conductor": "active", "worker-1": "busy"},
        )

        content = (tmp_path / "dashboard.md").read_text()
        assert "execute" in content
        assert "Building project" in content

    def test_update_status_includes_timestamp(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """ダッシュボードにタイムスタンプが含まれることを確認"""
        updater.update_status(phase="plan", current_task="Planning")

        content = (tmp_path / "dashboard.md").read_text()
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in content

    def test_add_log_entry_appends_to_log_section(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """ログエントリがログセクションに追加されることを確認"""
        updater.add_log_entry("Task started")
        updater.add_log_entry("Task completed")

        content = (tmp_path / "dashboard.md").read_text()
        assert "Task started" in content
        assert "Task completed" in content

    def test_set_phase_updates_phase(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """フェーズが更新されることを確認"""
        updater.set_phase("review")

        content = (tmp_path / "dashboard.md").read_text()
        assert "review" in content

    def test_set_progress_updates_progress(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """進捗が更新されることを確認"""
        updater.set_progress(completed=3, total=5)

        content = (tmp_path / "dashboard.md").read_text()
        assert "3" in content
        assert "5" in content

    def test_set_agent_status_updates_agent_table(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """エージェントステータスが更新されることを確認"""
        updater.set_agent_status("worker-1", "busy", task="Building src/main.py")

        content = (tmp_path / "dashboard.md").read_text()
        assert "worker-1" in content
        assert "busy" in content

    def test_clear_resets_dashboard(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """clearでダッシュボードがリセットされることを確認"""
        updater.add_log_entry("Some log")
        updater.set_phase("execute")

        updater.clear()

        content = (tmp_path / "dashboard.md").read_text()
        # 初期状態に戻る
        assert "idle" in content.lower() or "ready" in content.lower()

    def test_update_mode_script_not_found(
        self, tmp_path: Path
    ) -> None:
        """update-mode.shが見つからない場合もエラーにならない"""
        updater = DashboardUpdater(status_dir=tmp_path)
        # Should not raise an error
        updater.update_mode(mode="A", status="active", workers=2)

    def test_update_mode_with_all_params(
        self, updater: DashboardUpdater
    ) -> None:
        """全パラメータ指定でupdate_mode呼び出し"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            updater.update_mode(
                mode="B",
                status="active",
                workers=3,
                workflow="default",
                tasks_total=10,
                tasks_done=5,
                worktrees=2,
                teammates=4,
            )

            # subprocess.runが適切な引数で呼ばれたことを確認
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "B" in call_args
            assert "active" in call_args

    def test_update_mode_subprocess_error(
        self, updater: DashboardUpdater
    ) -> None:
        """subprocess.CalledProcessErrorでも例外にならない"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")

            # Should not raise
            updater.update_mode(mode="C", status="error")

    def test_log_entry_max_10(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """ログエントリが最大10件に制限される"""
        # Add 15 log entries
        for i in range(15):
            updater.add_log_entry(f"Log entry {i}")

        content = (tmp_path / "dashboard.md").read_text()
        # Only the last 10 should be present
        assert "Log entry 14" in content
        assert "Log entry 5" in content
        assert "Log entry 4" not in content
        assert "Log entry 0" not in content

    def test_write_dashboard_progress_format(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """進捗表示のフォーマット確認"""
        # Case 1: total=0 -> "-"
        updater.set_progress(completed=0, total=0)
        content = (tmp_path / "dashboard.md").read_text()
        # Progress column should contain "-"
        lines = content.split("\n")
        for line in lines:
            if "| idle |" in line:
                assert "| - |" in line
                break

        # Case 2: total>0 -> "completed/total"
        updater.set_progress(completed=3, total=5)
        content = (tmp_path / "dashboard.md").read_text()
        assert "3/5" in content

    def test_write_dashboard_multiple_agents(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """複数エージェントのテーブル表示"""
        updater.set_agent_status("conductor", "active", task="Planning")
        updater.set_agent_status("worker-1", "busy", task="Implementing feature")

        content = (tmp_path / "dashboard.md").read_text()
        assert "conductor" in content
        assert "active" in content
        assert "worker-1" in content
        assert "busy" in content
        assert "Planning" in content
        assert "Implementing feature" in content

    def test_update_status_with_agents(
        self, updater: DashboardUpdater, tmp_path: Path
    ) -> None:
        """update_status()でagents指定時のテスト"""
        updater.update_status(
            phase="execute",
            current_task="Building",
            agents={
                "conductor": "monitoring",
                "worker-1": "active",
                "worker-2": "idle",
            },
        )

        content = (tmp_path / "dashboard.md").read_text()
        assert "conductor" in content
        assert "monitoring" in content
        assert "worker-1" in content
        assert "active" in content
        assert "worker-2" in content
        assert "idle" in content
