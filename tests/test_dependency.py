"""タスク依存関係解決のテスト"""

from pathlib import Path

import pytest

from ensemble.dependency import CircularDependencyError, DependencyResolver
from ensemble.queue import TaskQueue


class TestDependencyResolver:
    """DependencyResolver のテスト"""

    def test_no_dependencies(self) -> None:
        """blocked_byなしのタスクは即実行可能"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2"},
            {"id": "task-003", "command": "test 3"},
        ]
        resolver = DependencyResolver(tasks)

        ready = resolver.get_ready_tasks()

        assert len(ready) == 3
        assert set(t["id"] for t in ready) == {"task-001", "task-002", "task-003"}

    def test_simple_dependency(self) -> None:
        """task-001→task-002の単純依存"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2", "blocked_by": ["task-001"]},
        ]
        resolver = DependencyResolver(tasks)

        # 初期状態: task-001のみ実行可能
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-001"

        # task-001完了後: task-002が実行可能
        resolver.mark_completed("task-001")
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-002"

    def test_chain_dependency(self) -> None:
        """task-001→task-002→task-003の連鎖"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2", "blocked_by": ["task-001"]},
            {"id": "task-003", "command": "test 3", "blocked_by": ["task-002"]},
        ]
        resolver = DependencyResolver(tasks)

        # 初期状態: task-001のみ実行可能
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-001"

        # task-001完了後: task-002が実行可能
        resolver.mark_completed("task-001")
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-002"

        # task-002完了後: task-003が実行可能
        resolver.mark_completed("task-002")
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-003"

    def test_parallel_with_dependency(self) -> None:
        """並列タスク + 依存タスクの混合"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2"},
            {"id": "task-003", "command": "test 3", "blocked_by": ["task-001", "task-002"]},
        ]
        resolver = DependencyResolver(tasks)

        # 初期状態: task-001, task-002が実行可能
        ready = resolver.get_ready_tasks()
        assert len(ready) == 2
        assert set(t["id"] for t in ready) == {"task-001", "task-002"}

        # task-001完了後: task-002のみ（task-003はまだブロック中）
        resolver.mark_completed("task-001")
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-002"

        # task-002完了後: task-003が実行可能
        resolver.mark_completed("task-002")
        ready = resolver.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0]["id"] == "task-003"

    def test_mark_completed_unlocks(self) -> None:
        """完了マークで新タスクが解放される"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2", "blocked_by": ["task-001"]},
        ]
        resolver = DependencyResolver(tasks)

        # task-001を完了マーク
        newly_ready = resolver.mark_completed("task-001")

        # task-002が新たに解放される
        assert len(newly_ready) == 1
        assert newly_ready[0]["id"] == "task-002"

    def test_circular_dependency_detection(self) -> None:
        """task-001→task-002→task-001の循環検知"""
        tasks = [
            {"id": "task-001", "command": "test 1", "blocked_by": ["task-002"]},
            {"id": "task-002", "command": "test 2", "blocked_by": ["task-001"]},
        ]
        resolver = DependencyResolver(tasks)

        cycles = resolver.detect_cycles()

        assert len(cycles) > 0
        # 循環が検出されていることを確認
        # 循環は ["task-001", "task-002", "task-001"] のような形式
        assert any("task-001" in cycle and "task-002" in cycle for cycle in cycles)

    def test_validate_raises_on_cycle(self) -> None:
        """validate()がCircularDependencyErrorを発生"""
        tasks = [
            {"id": "task-001", "command": "test 1", "blocked_by": ["task-003"]},
            {"id": "task-002", "command": "test 2", "blocked_by": ["task-001"]},
            {"id": "task-003", "command": "test 3", "blocked_by": ["task-002"]},
        ]
        resolver = DependencyResolver(tasks)

        with pytest.raises(CircularDependencyError) as exc_info:
            resolver.validate()

        # エラーメッセージに循環が含まれることを確認
        assert "Circular dependency detected" in str(exc_info.value)
        assert len(exc_info.value.cycle) > 0

    def test_get_blocked_tasks(self) -> None:
        """ブロック中タスクのリスト取得"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2", "blocked_by": ["task-001"]},
            {"id": "task-003", "command": "test 3", "blocked_by": ["task-001"]},
        ]
        resolver = DependencyResolver(tasks)

        # 初期状態: task-002, task-003がブロック中
        blocked = resolver.get_blocked_tasks()
        assert len(blocked) == 2
        assert set(t["id"] for t in blocked) == {"task-002", "task-003"}

        # task-001完了後: ブロックなし
        resolver.mark_completed("task-001")
        blocked = resolver.get_blocked_tasks()
        assert len(blocked) == 0

    def test_is_all_completed(self) -> None:
        """全完了判定"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2"},
        ]
        resolver = DependencyResolver(tasks)

        # 初期状態: 未完了
        assert not resolver.is_all_completed()

        # task-001完了
        resolver.mark_completed("task-001")
        assert not resolver.is_all_completed()

        # task-002完了
        resolver.mark_completed("task-002")
        assert resolver.is_all_completed()

    def test_nonexistent_dependency(self) -> None:
        """存在しないタスクへの依存（警告/エラー）"""
        tasks = [
            {"id": "task-001", "command": "test 1", "blocked_by": ["task-999"]},
        ]
        resolver = DependencyResolver(tasks)

        # 存在しないタスクへの依存の場合、task-001は永遠にブロック状態
        ready = resolver.get_ready_tasks()
        assert len(ready) == 0

        blocked = resolver.get_blocked_tasks()
        assert len(blocked) == 1
        assert blocked[0]["id"] == "task-001"

    def test_get_task(self) -> None:
        """タスクIDからタスクを取得"""
        tasks = [
            {"id": "task-001", "command": "test 1"},
            {"id": "task-002", "command": "test 2"},
        ]
        resolver = DependencyResolver(tasks)

        # 存在するタスク
        task = resolver.get_task("task-001")
        assert task is not None
        assert task["id"] == "task-001"

        # 存在しないタスク
        task = resolver.get_task("task-999")
        assert task is None


class TestQueueWithDependency:
    """TaskQueueの依存関係対応テスト"""

    def test_queue_enqueue_with_dependency(self, tmp_path: Path) -> None:
        """TaskQueue.enqueue_with_dependency()のblocked_by対応確認"""
        queue = TaskQueue(base_dir=tmp_path / "queue")

        # blocked_by付きでタスクを追加
        task_id_1 = queue.enqueue_with_dependency(
            "test command 1", "test-agent-1", blocked_by=[]
        )
        task_id_2 = queue.enqueue_with_dependency(
            "test command 2", "test-agent-2", blocked_by=[task_id_1]
        )

        # タスクファイルが作成されていることを確認
        task_file_1 = queue.tasks_dir / f"{task_id_1}.yaml"
        task_file_2 = queue.tasks_dir / f"{task_id_2}.yaml"
        assert task_file_1.exists()
        assert task_file_2.exists()

        # blocked_byが正しく保存されていることを確認
        import yaml

        with open(task_file_2) as f:
            task_2 = yaml.safe_load(f)
        assert "blocked_by" in task_2
        assert task_id_1 in task_2["blocked_by"]

    def test_queue_get_ready_tasks(self, tmp_path: Path) -> None:
        """TaskQueue.get_ready_tasks()の動作確認"""
        queue = TaskQueue(base_dir=tmp_path / "queue")

        # 3つのタスクを追加（task-2はtask-1に依存）
        task_id_1 = queue.enqueue_with_dependency(
            "test command 1", "test-agent-1", blocked_by=[]
        )
        task_id_2 = queue.enqueue_with_dependency(
            "test command 2", "test-agent-2", blocked_by=[task_id_1]
        )
        task_id_3 = queue.enqueue_with_dependency(
            "test command 3", "test-agent-3", blocked_by=[]
        )

        # 初期状態: task-1, task-3が実行可能
        ready = queue.get_ready_tasks(completed_task_ids=[])
        assert len(ready) == 2
        assert set(t["task_id"] for t in ready) == {task_id_1, task_id_3}

        # task-1完了後: task-2も実行可能
        ready = queue.get_ready_tasks(completed_task_ids=[task_id_1])
        assert len(ready) == 2
        assert set(t["task_id"] for t in ready) == {task_id_2, task_id_3}
