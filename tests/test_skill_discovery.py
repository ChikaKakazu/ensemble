"""Bottom-Up Skill Discovery のテスト"""

from pathlib import Path

import pytest

from ensemble.skill_discovery import SkillCandidate, SkillDiscoveryEngine


class TestSkillCandidate:
    """SkillCandidate のテスト"""

    def test_skill_candidate_init(self) -> None:
        """SkillCandidate初期化"""
        candidate = SkillCandidate(
            name="api-scaffold",
            reason="同パターンを3回実行",
            pattern="FastAPI endpoint creation",
            occurrence_count=3,
            source_tasks=["task-001", "task-002", "task-003"],
        )

        assert candidate.name == "api-scaffold"
        assert candidate.reason == "同パターンを3回実行"
        assert candidate.pattern == "FastAPI endpoint creation"
        assert candidate.occurrence_count == 3
        assert len(candidate.source_tasks) == 3
        assert candidate.created_at is not None

    def test_skill_candidate_to_dict(self) -> None:
        """dict変換"""
        candidate = SkillCandidate(
            name="test-pattern",
            reason="repeated 3 times",
            pattern="test pattern description",
            occurrence_count=3,
            source_tasks=["task-1", "task-2"],
        )

        data = candidate.to_dict()

        assert data["name"] == "test-pattern"
        assert data["reason"] == "repeated 3 times"
        assert data["pattern"] == "test pattern description"
        assert data["occurrence_count"] == 3
        assert data["source_tasks"] == ["task-1", "task-2"]
        assert "created_at" in data

    def test_skill_candidate_from_dict(self) -> None:
        """dict復元"""
        data = {
            "name": "restored-pattern",
            "reason": "test reason",
            "pattern": "test description",
            "occurrence_count": 5,
            "source_tasks": ["task-a", "task-b", "task-c"],
            "created_at": "2026-02-11T00:00:00",
        }

        candidate = SkillCandidate.from_dict(data)

        assert candidate.name == "restored-pattern"
        assert candidate.reason == "test reason"
        assert candidate.pattern == "test description"
        assert candidate.occurrence_count == 5
        assert candidate.source_tasks == ["task-a", "task-b", "task-c"]
        assert candidate.created_at == "2026-02-11T00:00:00"


class TestSkillDiscoveryEngine:
    """SkillDiscoveryEngine のテスト"""

    @pytest.fixture
    def engine(self, tmp_path: Path) -> SkillDiscoveryEngine:
        """テスト用エンジンを作成"""
        return SkillDiscoveryEngine(
            threshold=3, candidates_dir=tmp_path / "candidates"
        )

    def test_record_pattern_below_threshold(
        self, engine: SkillDiscoveryEngine
    ) -> None:
        """閾値未満でNone"""
        result1 = engine.record_pattern(
            "task-001", "pattern-a", "description of pattern A"
        )
        assert result1 is None

        result2 = engine.record_pattern(
            "task-002", "pattern-a", "description of pattern A"
        )
        assert result2 is None

        # 2回出現だが閾値（3）未満
        pending = engine.get_pending_patterns()
        assert pending["pattern-a"] == 2

    def test_record_pattern_at_threshold(
        self, engine: SkillDiscoveryEngine
    ) -> None:
        """閾値到達でSkillCandidate返却"""
        engine.record_pattern("task-001", "pattern-b", "description B")
        engine.record_pattern("task-002", "pattern-b", "description B")
        result = engine.record_pattern("task-003", "pattern-b", "description B")

        # 閾値到達（3回目）
        assert result is not None
        assert isinstance(result, SkillCandidate)
        assert result.name == "pattern-b"
        assert result.occurrence_count == 3
        assert result.reason == "同パターンを3回実行"

    def test_record_pattern_tracks_source_tasks(
        self, engine: SkillDiscoveryEngine
    ) -> None:
        """ソースタスクの追跡"""
        engine.record_pattern("task-001", "pattern-c", "desc C")
        engine.record_pattern("task-002", "pattern-c", "desc C")
        result = engine.record_pattern("task-003", "pattern-c", "desc C")

        assert result is not None
        assert result.source_tasks == ["task-001", "task-002", "task-003"]

    def test_process_worker_report_with_candidate(
        self, engine: SkillDiscoveryEngine
    ) -> None:
        """skill_candidateフィールドあり"""
        report1 = {
            "task_id": "task-001",
            "skill_candidate": {
                "found": True,
                "name": "api-pattern",
                "pattern": "API endpoint creation steps",
            },
        }
        report2 = {
            "task_id": "task-002",
            "skill_candidate": {
                "found": True,
                "name": "api-pattern",
                "pattern": "API endpoint creation steps",
            },
        }
        report3 = {
            "task_id": "task-003",
            "skill_candidate": {
                "found": True,
                "name": "api-pattern",
                "pattern": "API endpoint creation steps",
            },
        }

        result1 = engine.process_worker_report(report1)
        assert result1 is None  # 閾値未満

        result2 = engine.process_worker_report(report2)
        assert result2 is None  # 閾値未満

        result3 = engine.process_worker_report(report3)
        assert result3 is not None  # 閾値到達
        assert result3.name == "api-pattern"
        assert result3.occurrence_count == 3

    def test_process_worker_report_without_candidate(
        self, engine: SkillDiscoveryEngine
    ) -> None:
        """skill_candidateフィールドなし→None"""
        report = {"task_id": "task-001", "status": "success"}

        result = engine.process_worker_report(report)
        assert result is None

    def test_get_all_candidates(self, engine: SkillDiscoveryEngine) -> None:
        """閾値超過候補の一覧"""
        # パターンAを3回記録（閾値到達）
        engine.record_pattern("task-001", "pattern-a", "desc A")
        engine.record_pattern("task-002", "pattern-a", "desc A")
        engine.record_pattern("task-003", "pattern-a", "desc A")

        # パターンBを2回記録（閾値未満）
        engine.record_pattern("task-004", "pattern-b", "desc B")
        engine.record_pattern("task-005", "pattern-b", "desc B")

        candidates = engine.get_all_candidates()
        assert len(candidates) == 1  # パターンAのみ
        assert candidates[0].name == "pattern-a"

    def test_get_pending_patterns(self, engine: SkillDiscoveryEngine) -> None:
        """閾値未満パターンの一覧"""
        engine.record_pattern("task-001", "pattern-x", "desc X")
        engine.record_pattern("task-002", "pattern-y", "desc Y")
        engine.record_pattern("task-003", "pattern-y", "desc Y")

        pending = engine.get_pending_patterns()
        assert pending["pattern-x"] == 1
        assert pending["pattern-y"] == 2

    def test_save_and_load_candidates(
        self, engine: SkillDiscoveryEngine, tmp_path: Path
    ) -> None:
        """保存・読み込みの往復テスト"""
        # パターンを3回記録（閾値到達）
        engine.record_pattern("task-001", "saved-pattern", "desc saved")
        engine.record_pattern("task-002", "saved-pattern", "desc saved")
        engine.record_pattern("task-003", "saved-pattern", "desc saved")

        # 保存
        engine.save_candidates()

        # 新しいエンジンを作成して読み込み
        new_engine = SkillDiscoveryEngine(
            threshold=3, candidates_dir=tmp_path / "candidates"
        )
        new_engine.load_candidates()

        # 候補が復元されていることを確認
        candidates = new_engine.get_all_candidates()
        assert len(candidates) == 1
        assert candidates[0].name == "saved-pattern"
        assert candidates[0].occurrence_count == 3

    def test_generate_skill_template(
        self, engine: SkillDiscoveryEngine
    ) -> None:
        """テンプレート生成（マークダウン形式確認）"""
        candidate = SkillCandidate(
            name="template-test",
            reason="test reason",
            pattern="test pattern description",
            occurrence_count=3,
            source_tasks=["task-1", "task-2", "task-3"],
        )

        template = engine.generate_skill_template(candidate)

        # マークダウン形式の確認
        assert "# Template Test Skill" in template
        assert "## 概要" in template
        assert "test reason" in template
        assert "## パターン" in template
        assert "test pattern description" in template
        assert "## 適用例" in template
        assert "task-1" in template
        assert "task-2" in template
        assert "task-3" in template
        assert "3回の出現パターン" in template

    def test_custom_threshold(self, tmp_path: Path) -> None:
        """カスタム閾値（threshold=5）"""
        engine = SkillDiscoveryEngine(
            threshold=5, candidates_dir=tmp_path / "candidates"
        )

        # 4回記録（閾値5未満）
        for i in range(1, 5):
            result = engine.record_pattern(f"task-{i}", "pattern-z", "desc Z")
            assert result is None

        # 5回目で閾値到達
        result = engine.record_pattern("task-5", "pattern-z", "desc Z")
        assert result is not None
        assert result.occurrence_count == 5
