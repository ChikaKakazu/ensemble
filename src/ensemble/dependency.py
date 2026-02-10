"""
タスク依存関係の解決

タスク間の依存関係（blocked_by）を管理し、実行可能タスクをフィルタリングする。
循環依存の検知もサポート。
"""

from __future__ import annotations


class CircularDependencyError(Exception):
    """循環依存検知時の例外"""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle)}")


class DependencyResolver:
    """タスク間の依存関係を解決する"""

    def __init__(self, tasks: list[dict]):
        """
        Args:
            tasks: タスクリスト。各タスクは以下のフォーマット:
                {"id": "task-001", "blocked_by": ["task-000"], ...}
                または {"task_id": "task-001", "blocked_by": ["task-000"], ...}
        """
        # "id"または"task_id"キーをサポート
        self.tasks = {}
        for t in tasks:
            task_id = t.get("id") or t.get("task_id")
            if task_id:
                self.tasks[task_id] = t
        self.completed: set[str] = set()

    def _get_task_id(self, task: dict) -> str:
        """タスクからIDを取得（"id"または"task_id"キーをサポート）"""
        return task.get("id") or task.get("task_id") or ""

    def get_ready_tasks(self) -> list[dict]:
        """
        依存が全て解決済み（またはblocked_byなし）のタスクを返す

        Returns:
            実行可能なタスクのリスト
        """
        ready = []
        for task_id, task in self.tasks.items():
            if task_id in self.completed:
                continue
            blocked_by = set(task.get("blocked_by", []))
            if blocked_by.issubset(self.completed):
                ready.append(task)
        return ready

    def mark_completed(self, task_id: str) -> list[dict]:
        """
        タスク完了をマークし、新たに解放されたタスクを返す

        Args:
            task_id: 完了したタスクID

        Returns:
            新たに実行可能になったタスクのリスト
        """
        # 完了前の実行可能タスク
        ready_before = set(self._get_task_id(t) for t in self.get_ready_tasks())

        # 完了マーク
        self.completed.add(task_id)

        # 完了後の実行可能タスク
        ready_after = set(self._get_task_id(t) for t in self.get_ready_tasks())

        # 新たに解放されたタスク
        newly_ready_ids = ready_after - ready_before
        return [self.tasks[tid] for tid in newly_ready_ids if tid in self.tasks]

    def detect_cycles(self) -> list[list[str]]:
        """
        循環依存を検知。DFS（深さ優先探索）でサイクルを検出

        Returns:
            検出された循環のリスト。各循環は task_id のリスト
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(task_id: str, path: list[str]) -> None:
            if task_id in rec_stack:
                # 循環検出
                cycle_start = path.index(task_id)
                cycle = path[cycle_start:] + [task_id]
                cycles.append(cycle)
                return

            if task_id in visited:
                return

            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            # 依存先を探索
            task = self.tasks.get(task_id)
            if task:
                for dep_id in task.get("blocked_by", []):
                    if dep_id in self.tasks:
                        dfs(dep_id, path.copy())

            rec_stack.remove(task_id)

        for task_id in self.tasks.keys():
            if task_id not in visited:
                dfs(task_id, [])

        return cycles

    def validate(self) -> None:
        """
        全タスクの依存関係を検証。循環があればCircularDependencyError

        Raises:
            CircularDependencyError: 循環依存が検出された場合
        """
        cycles = self.detect_cycles()
        if cycles:
            # 最初の循環を報告
            raise CircularDependencyError(cycles[0])

    def get_task(self, task_id: str) -> dict | None:
        """
        タスクIDからタスクを取得

        Args:
            task_id: タスクID

        Returns:
            タスク辞書、存在しない場合はNone
        """
        return self.tasks.get(task_id)

    def get_blocked_tasks(self) -> list[dict]:
        """
        まだブロックされているタスクのリスト

        Returns:
            ブロック中タスクのリスト
        """
        blocked = []
        for task_id, task in self.tasks.items():
            if task_id in self.completed:
                continue
            blocked_by = set(task.get("blocked_by", []))
            if not blocked_by.issubset(self.completed):
                blocked.append(task)
        return blocked

    def is_all_completed(self) -> bool:
        """
        全タスクが完了したか

        Returns:
            全タスクが完了している場合True
        """
        return len(self.completed) == len(self.tasks)
