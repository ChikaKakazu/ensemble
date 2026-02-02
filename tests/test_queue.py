"""キュー操作のテスト"""

import yaml
from pathlib import Path

import pytest

from ensemble.queue import TaskQueue


class TestTaskQueue:
    """TaskQueue のテスト"""

    @pytest.fixture
    def queue(self, tmp_path: Path) -> TaskQueue:
        """テスト用キューを作成"""
        return TaskQueue(base_dir=tmp_path)

    def test_init_creates_directories(self, tmp_path: Path) -> None:
        """初期化時にディレクトリが作成されることを確認"""
        queue = TaskQueue(base_dir=tmp_path)

        assert (tmp_path / "tasks").exists()
        assert (tmp_path / "processing").exists()
        assert (tmp_path / "reports").exists()

    def test_enqueue_creates_task_file(self, queue: TaskQueue, tmp_path: Path) -> None:
        """タスクをキューに追加するとファイルが作成されることを確認"""
        task_id = queue.enqueue(
            command="build",
            agent="coder",
            params={"target": "src/main.py"},
        )

        task_file = tmp_path / "tasks" / f"{task_id}.yaml"
        assert task_file.exists()

        with open(task_file) as f:
            task = yaml.safe_load(f)

        assert task["task_id"] == task_id
        assert task["command"] == "build"
        assert task["agent"] == "coder"
        assert task["params"]["target"] == "src/main.py"
        assert task["status"] == "pending"

    def test_enqueue_returns_unique_task_id(self, queue: TaskQueue) -> None:
        """各タスクにユニークなIDが割り当てられることを確認"""
        id1 = queue.enqueue(command="task1", agent="agent1")
        id2 = queue.enqueue(command="task2", agent="agent2")
        id3 = queue.enqueue(command="task3", agent="agent3")

        assert id1 != id2 != id3

    def test_claim_returns_task_and_moves_file(
        self, queue: TaskQueue, tmp_path: Path
    ) -> None:
        """claimでタスクを取得しファイルが移動することを確認"""
        task_id = queue.enqueue(command="test", agent="worker")

        task = queue.claim()

        assert task is not None
        assert task["task_id"] == task_id
        assert task["command"] == "test"

        # tasksにはもうない
        assert not (tmp_path / "tasks" / f"{task_id}.yaml").exists()
        # processingに移動
        assert (tmp_path / "processing" / f"{task_id}.yaml").exists()

    def test_claim_returns_none_if_queue_empty(self, queue: TaskQueue) -> None:
        """キューが空の場合Noneを返すことを確認"""
        task = queue.claim()
        assert task is None

    def test_complete_moves_to_reports(
        self, queue: TaskQueue, tmp_path: Path
    ) -> None:
        """completeで結果がreportsに保存されることを確認"""
        task_id = queue.enqueue(command="test", agent="worker")
        queue.claim()

        queue.complete(task_id, result="success", output="Build completed")

        # processingからは削除
        assert not (tmp_path / "processing" / f"{task_id}.yaml").exists()
        # reportsに保存
        report_file = tmp_path / "reports" / f"{task_id}.yaml"
        assert report_file.exists()

        with open(report_file) as f:
            report = yaml.safe_load(f)

        assert report["task_id"] == task_id
        assert report["result"] == "success"
        assert report["output"] == "Build completed"

    def test_complete_with_error_result(
        self, queue: TaskQueue, tmp_path: Path
    ) -> None:
        """エラー結果を保存できることを確認"""
        task_id = queue.enqueue(command="test", agent="worker")
        queue.claim()

        queue.complete(task_id, result="error", output="Build failed", error="Timeout")

        report_file = tmp_path / "reports" / f"{task_id}.yaml"
        with open(report_file) as f:
            report = yaml.safe_load(f)

        assert report["result"] == "error"
        assert report["error"] == "Timeout"

    def test_list_pending_returns_task_ids(self, queue: TaskQueue) -> None:
        """保留中のタスクIDリストを取得できることを確認"""
        id1 = queue.enqueue(command="task1", agent="agent1")
        id2 = queue.enqueue(command="task2", agent="agent2")

        pending = queue.list_pending()

        assert id1 in pending
        assert id2 in pending
        assert len(pending) == 2

    def test_list_pending_excludes_claimed_tasks(self, queue: TaskQueue) -> None:
        """claimされたタスクはlist_pendingに含まれないことを確認"""
        id1 = queue.enqueue(command="task1", agent="agent1")
        id2 = queue.enqueue(command="task2", agent="agent2")

        queue.claim()  # id1をclaim

        pending = queue.list_pending()

        assert len(pending) == 1

    def test_cleanup_removes_all_files(self, queue: TaskQueue, tmp_path: Path) -> None:
        """cleanupで全ファイルが削除されることを確認"""
        queue.enqueue(command="task1", agent="agent1")
        queue.enqueue(command="task2", agent="agent2")
        task = queue.claim()
        if task:
            queue.complete(task["task_id"], result="success", output="done")

        queue.cleanup()

        assert len(list((tmp_path / "tasks").glob("*.yaml"))) == 0
        assert len(list((tmp_path / "processing").glob("*.yaml"))) == 0
        assert len(list((tmp_path / "reports").glob("*.yaml"))) == 0
