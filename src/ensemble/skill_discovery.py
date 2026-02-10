"""
Bottom-Up Skill Discovery

Workerが繰り返し実行したパターンを検知し、スキル化候補として提案する。
"""

from __future__ import annotations

import yaml
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SkillCandidate:
    """
    スキル化候補

    Attributes:
        name: スキル名候補（例: "api-endpoint-scaffold"）
        reason: スキル化を提案する理由
        pattern: 繰り返しパターンの説明
        occurrence_count: 出現回数
        source_tasks: このパターンが検出されたタスクIDのリスト
        created_at: 候補が作成された日時
    """

    name: str
    reason: str
    pattern: str
    occurrence_count: int = 1
    source_tasks: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """dict変換"""
        return {
            "name": self.name,
            "reason": self.reason,
            "pattern": self.pattern,
            "occurrence_count": self.occurrence_count,
            "source_tasks": self.source_tasks,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SkillCandidate:
        """dict復元"""
        return cls(
            name=data["name"],
            reason=data["reason"],
            pattern=data["pattern"],
            occurrence_count=data.get("occurrence_count", 1),
            source_tasks=data.get("source_tasks", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


class SkillDiscoveryEngine:
    """
    Bottom-Up Skill Discovery エンジン

    Workerが繰り返し実行したパターンを検知し、閾値を超えたらスキル化候補として提案する。
    """

    def __init__(
        self, threshold: int = 3, candidates_dir: Path | None = None
    ) -> None:
        """
        Args:
            threshold: パターン出現の閾値（デフォルト: 3回）
            candidates_dir: 候補保存ディレクトリ（デフォルト: .ensemble/skill-candidates/）
        """
        self.threshold = threshold
        self.candidates_dir = (
            candidates_dir
            if candidates_dir
            else Path(".ensemble/skill-candidates")
        )
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

        # パターン名 → (出現回数, ソースタスクリスト)
        self._pattern_counts: dict[str, tuple[int, list[str]]] = defaultdict(
            lambda: (0, [])
        )

        # 閾値超過した候補
        self._candidates: dict[str, SkillCandidate] = {}

    def record_pattern(
        self, task_id: str, pattern_name: str, pattern_description: str
    ) -> SkillCandidate | None:
        """
        パターン出現を記録し、閾値超過時にSkillCandidateを返す

        Args:
            task_id: タスクID
            pattern_name: パターン名（例: "api-endpoint-scaffold"）
            pattern_description: パターンの説明

        Returns:
            閾値超過時にSkillCandidate、未満ならNone
        """
        # 現在の出現回数とソースタスクを取得
        current_count, source_tasks = self._pattern_counts.get(
            pattern_name, (0, [])
        )

        # 出現回数とソースタスクを更新
        new_count = current_count + 1
        new_source_tasks = source_tasks + [task_id]
        self._pattern_counts[pattern_name] = (new_count, new_source_tasks)

        # 閾値到達判定
        if new_count >= self.threshold:
            # 既に候補として登録済みか確認
            if pattern_name in self._candidates:
                # 既存候補を更新
                candidate = self._candidates[pattern_name]
                candidate.occurrence_count = new_count
                candidate.source_tasks = new_source_tasks
            else:
                # 新規候補を作成
                candidate = SkillCandidate(
                    name=pattern_name,
                    reason=f"同パターンを{new_count}回実行",
                    pattern=pattern_description,
                    occurrence_count=new_count,
                    source_tasks=new_source_tasks,
                )
                self._candidates[pattern_name] = candidate

            return candidate

        return None

    def process_worker_report(self, report: dict) -> SkillCandidate | None:
        """
        Worker報告からskill_candidateフィールドを抽出・処理

        Args:
            report: Worker完了報告（YAMLをdictに変換したもの）

        Returns:
            閾値超過時にSkillCandidate、未満またはskill_candidateなしならNone
        """
        skill_candidate_data = report.get("skill_candidate")
        if not skill_candidate_data:
            return None

        if not skill_candidate_data.get("found"):
            return None

        task_id = report.get("task_id", "unknown")
        pattern_name = skill_candidate_data.get("name", "unnamed-pattern")
        pattern_description = skill_candidate_data.get("pattern", "")

        return self.record_pattern(task_id, pattern_name, pattern_description)

    def get_all_candidates(self) -> list[SkillCandidate]:
        """
        閾値超過した全候補を返す

        Returns:
            SkillCandidateのリスト
        """
        return list(self._candidates.values())

    def get_pending_patterns(self) -> dict[str, int]:
        """
        閾値未満のパターンとその出現回数

        Returns:
            パターン名 → 出現回数のdict
        """
        pending = {}
        for pattern_name, (count, _) in self._pattern_counts.items():
            if count < self.threshold:
                pending[pattern_name] = count

        return pending

    def save_candidates(self) -> None:
        """候補をYAMLファイルに保存"""
        candidates_file = self.candidates_dir / "candidates.yaml"

        # tupleをリスト形式に変換（YAML safe_load対応）
        pending_patterns_serializable = {}
        for pattern_name, (count, tasks) in self._pattern_counts.items():
            pending_patterns_serializable[pattern_name] = {
                "count": count,
                "tasks": tasks,
            }

        candidates_data = {
            "threshold": self.threshold,
            "candidates": [c.to_dict() for c in self._candidates.values()],
            "pending_patterns": pending_patterns_serializable,
            "updated_at": datetime.now().isoformat(),
        }

        with open(candidates_file, "w") as f:
            yaml.dump(candidates_data, f, allow_unicode=True, sort_keys=False)

    def load_candidates(self) -> None:
        """保存済み候補を読み込み"""
        candidates_file = self.candidates_dir / "candidates.yaml"
        if not candidates_file.exists():
            return

        with open(candidates_file) as f:
            data = yaml.safe_load(f)

        if not data:
            return

        # 閾値を復元
        self.threshold = data.get("threshold", 3)

        # 候補を復元
        self._candidates = {}
        for candidate_data in data.get("candidates", []):
            candidate = SkillCandidate.from_dict(candidate_data)
            self._candidates[candidate.name] = candidate

        # pending_patternsを復元
        self._pattern_counts = defaultdict(lambda: (0, []))
        for pattern_name, pattern_data in data.get("pending_patterns", {}).items():
            if isinstance(pattern_data, dict):
                # 新しいフォーマット（count + tasks）
                count = pattern_data.get("count", 0)
                tasks = pattern_data.get("tasks", [])
                self._pattern_counts[pattern_name] = (count, tasks)
            elif isinstance(pattern_data, int):
                # 古いフォーマット（countのみ）
                self._pattern_counts[pattern_name] = (pattern_data, [])
            else:
                # 不明なフォーマット
                self._pattern_counts[pattern_name] = (0, [])

    def generate_skill_template(self, candidate: SkillCandidate) -> str:
        """
        スキル定義テンプレート生成

        Args:
            candidate: スキル候補

        Returns:
            マークダウン形式のスキル定義テンプレート
        """
        template = f"""# {candidate.name.replace('-', ' ').title()} Skill

## 概要
{candidate.reason}

## パターン

{candidate.pattern}

## 適用例

以下のタスクで使用されました:
{chr(10).join(f'- {task_id}' for task_id in candidate.source_tasks)}

## 使い方

（ここにスキルの詳細な使用方法を記載）

## ベストプラクティス

- （ベストプラクティス1）
- （ベストプラクティス2）

## 注意事項

- （注意事項1）
- （注意事項2）

---

*このスキル定義は、{candidate.occurrence_count}回の出現パターンから自動生成されました。*
*作成日時: {candidate.created_at}*
"""
        return template
