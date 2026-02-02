"""ダッシュボード更新ロジックのテスト"""

from datetime import datetime
from pathlib import Path

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
