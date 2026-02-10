"""
ループ検知モジュール

レビュー→修正→レビューの無限ループを自動検知し、コスト浪費を防ぐ。

参照: TAKT LoopDetector - https://github.com/anthropics/anthropic-quickstarts/tree/main/takt
"""

from __future__ import annotations

from collections import defaultdict


class LoopDetectedError(Exception):
    """ループ検知時に発生する例外"""

    def __init__(self, task_id: str, count: int, max_iterations: int) -> None:
        """
        Args:
            task_id: ループが検知されたタスクID
            count: 現在の実行回数
            max_iterations: 最大反復回数
        """
        self.task_id = task_id
        self.count = count
        self.max_iterations = max_iterations
        super().__init__(
            f"Task {task_id} exceeded max iterations ({count}/{max_iterations})"
        )


class LoopDetector:
    """
    同一タスクへの繰り返し遷移を検知

    タスクIDごとに実行回数をカウントし、閾値を超えたらループと判定する。
    """

    def __init__(self, max_iterations: int = 5) -> None:
        """
        Args:
            max_iterations: 最大反復回数（デフォルト: 5回）
        """
        self.max_iterations = max_iterations
        self.task_counts: defaultdict[str, int] = defaultdict(int)

    def record(self, task_id: str) -> bool:
        """
        タスク実行を記録し、ループを検知する

        Args:
            task_id: タスクID

        Returns:
            ループ検知ならTrue、そうでなければFalse
        """
        self.task_counts[task_id] += 1
        return self.task_counts[task_id] > self.max_iterations

    def get_count(self, task_id: str) -> int:
        """
        現在の実行回数を取得する

        Args:
            task_id: タスクID

        Returns:
            実行回数（未記録の場合は0）
        """
        return self.task_counts[task_id]

    def reset(self, task_id: str | None = None) -> None:
        """
        特定タスクまたは全タスクのカウントをリセットする

        Args:
            task_id: リセット対象のタスクID（Noneの場合は全タスク）
        """
        if task_id is None:
            self.task_counts.clear()
        else:
            if task_id in self.task_counts:
                del self.task_counts[task_id]


class CycleDetector:
    """
    遷移サイクル（review→fix→review等）を検知

    特定の遷移パターン（from_state → to_state）の繰り返し回数をカウントし、
    閾値を超えたらループと判定する。
    """

    def __init__(self, max_cycles: int = 3) -> None:
        """
        Args:
            max_cycles: 最大サイクル回数（デフォルト: 3回）
        """
        self.max_cycles = max_cycles
        self.cycle_counts: defaultdict[str, int] = defaultdict(int)

    def record_cycle(
        self, task_id: str, from_state: str, to_state: str
    ) -> bool:
        """
        遷移を記録し、閾値超過を検知する

        Args:
            task_id: タスクID
            from_state: 遷移元の状態（例: "review"）
            to_state: 遷移先の状態（例: "fix"）

        Returns:
            閾値超過ならTrue、そうでなければFalse
        """
        cycle_key = f"{task_id}:{from_state}->{to_state}"
        self.cycle_counts[cycle_key] += 1
        return self.cycle_counts[cycle_key] > self.max_cycles

    def get_cycle_count(
        self, task_id: str, from_state: str, to_state: str
    ) -> int:
        """
        特定遷移の現在回数を取得する

        Args:
            task_id: タスクID
            from_state: 遷移元の状態
            to_state: 遷移先の状態

        Returns:
            遷移回数（未記録の場合は0）
        """
        cycle_key = f"{task_id}:{from_state}->{to_state}"
        return self.cycle_counts[cycle_key]

    def reset(self, task_id: str | None = None) -> None:
        """
        特定タスクまたは全タスクのサイクルカウントをリセットする

        Args:
            task_id: リセット対象のタスクID（Noneの場合は全タスク）
        """
        if task_id is None:
            self.cycle_counts.clear()
        else:
            # 特定タスクIDに関連するサイクルをすべて削除
            keys_to_delete = [
                key for key in self.cycle_counts if key.startswith(f"{task_id}:")
            ]
            for key in keys_to_delete:
                del self.cycle_counts[key]
