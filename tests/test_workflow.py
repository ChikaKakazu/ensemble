"""ワークフロー集約ロジックのテスト"""

from pathlib import Path

import pytest
import yaml

from ensemble.workflow import aggregate_results, parse_review_results, merge_findings


class TestAggregateResults:
    """aggregate_results関数のテスト"""

    def test_all_approved_returns_true(self) -> None:
        """全員approvedの場合、all("approved")はTrueを返す"""
        results = ["approved", "approved", "approved"]
        assert aggregate_results(results, 'all("approved")') is True

    def test_all_approved_with_needs_fix_returns_false(self) -> None:
        """1つでもneeds_fixがあれば、all("approved")はFalseを返す"""
        results = ["approved", "needs_fix", "approved"]
        assert aggregate_results(results, 'all("approved")') is False

    def test_any_needs_fix_returns_true(self) -> None:
        """1つでもneeds_fixがあれば、any("needs_fix")はTrueを返す"""
        results = ["approved", "needs_fix"]
        assert aggregate_results(results, 'any("needs_fix")') is True

    def test_any_needs_fix_all_approved_returns_false(self) -> None:
        """全員approvedなら、any("needs_fix")はFalseを返す"""
        results = ["approved", "approved"]
        assert aggregate_results(results, 'any("needs_fix")') is False

    def test_empty_results_all_returns_true(self) -> None:
        """空の結果リストに対してall()はTrueを返す（vacuous truth）"""
        results: list[str] = []
        assert aggregate_results(results, 'all("approved")') is True

    def test_empty_results_any_returns_false(self) -> None:
        """空の結果リストに対してany()はFalseを返す"""
        results: list[str] = []
        assert aggregate_results(results, 'any("needs_fix")') is False

    def test_invalid_rule_returns_false(self) -> None:
        """無効なルールはFalseを返す"""
        results = ["approved"]
        assert aggregate_results(results, "invalid_rule") is False

    def test_single_quotes_in_rule(self) -> None:
        """シングルクォートでも動作する"""
        results = ["approved", "approved"]
        assert aggregate_results(results, "all('approved')") is True


class TestParseReviewResults:
    """parse_review_results関数のテスト"""

    @pytest.fixture
    def reports_dir(self, tmp_path: Path) -> Path:
        """テスト用reportsディレクトリを作成"""
        reports = tmp_path / "reports"
        reports.mkdir()
        return reports

    def test_parses_single_report(self, reports_dir: Path) -> None:
        """単一のレポートを正しくパースする"""
        report = {
            "task_id": "task-123",
            "reviewer": "reviewer",
            "result": "approved",
            "summary": "Good code",
            "findings": [],
        }
        (reports_dir / "arch-review-task-123.yaml").write_text(yaml.dump(report))

        results = parse_review_results(str(reports_dir))
        assert results == {"arch-review": "approved"}

    def test_parses_multiple_reports(self, reports_dir: Path) -> None:
        """複数のレポートを正しくパースする"""
        arch_report = {
            "task_id": "task-123",
            "reviewer": "reviewer",
            "result": "approved",
        }
        security_report = {
            "task_id": "task-123",
            "reviewer": "security-reviewer",
            "result": "needs_fix",
        }
        (reports_dir / "arch-review-task-123.yaml").write_text(yaml.dump(arch_report))
        (reports_dir / "security-review-task-123.yaml").write_text(
            yaml.dump(security_report)
        )

        results = parse_review_results(str(reports_dir))
        assert results == {"arch-review": "approved", "security-review": "needs_fix"}

    def test_empty_directory_returns_empty_dict(self, reports_dir: Path) -> None:
        """空のディレクトリは空の辞書を返す"""
        results = parse_review_results(str(reports_dir))
        assert results == {}

    def test_ignores_non_yaml_files(self, reports_dir: Path) -> None:
        """YAML以外のファイルは無視する"""
        (reports_dir / "readme.txt").write_text("This is a readme")
        report = {
            "task_id": "task-123",
            "reviewer": "reviewer",
            "result": "approved",
        }
        (reports_dir / "arch-review-task-123.yaml").write_text(yaml.dump(report))

        results = parse_review_results(str(reports_dir))
        assert results == {"arch-review": "approved"}

    def test_handles_malformed_yaml(self, reports_dir: Path) -> None:
        """不正なYAMLは警告を出してスキップする"""
        (reports_dir / "bad-review.yaml").write_text("invalid: yaml: content:")
        report = {
            "task_id": "task-123",
            "reviewer": "reviewer",
            "result": "approved",
        }
        (reports_dir / "arch-review-task-123.yaml").write_text(yaml.dump(report))

        results = parse_review_results(str(reports_dir))
        assert results == {"arch-review": "approved"}


class TestMergeFindings:
    """merge_findings関数のテスト"""

    @pytest.fixture
    def reports_dir(self, tmp_path: Path) -> Path:
        """テスト用reportsディレクトリを作成"""
        reports = tmp_path / "reports"
        reports.mkdir()
        return reports

    def test_merges_findings_from_multiple_reports(self, reports_dir: Path) -> None:
        """複数レポートのfindingsをマージする"""
        arch_report = {
            "task_id": "task-123",
            "reviewer": "reviewer",
            "result": "needs_fix",
            "findings": [
                {
                    "severity": "high",
                    "location": "src/app.py:10",
                    "description": "Bad design",
                }
            ],
        }
        security_report = {
            "task_id": "task-123",
            "reviewer": "security-reviewer",
            "result": "needs_fix",
            "findings": [
                {
                    "severity": "critical",
                    "location": "src/app.py:20",
                    "description": "SQL injection",
                }
            ],
        }
        (reports_dir / "arch-review-task-123.yaml").write_text(yaml.dump(arch_report))
        (reports_dir / "security-review-task-123.yaml").write_text(
            yaml.dump(security_report)
        )

        findings = merge_findings(str(reports_dir))

        assert len(findings) == 2
        assert any(f["severity"] == "critical" for f in findings)
        assert any(f["severity"] == "high" for f in findings)

    def test_sorts_findings_by_severity(self, reports_dir: Path) -> None:
        """findingsを重大度順にソートする"""
        report = {
            "task_id": "task-123",
            "reviewer": "reviewer",
            "result": "needs_fix",
            "findings": [
                {"severity": "low", "description": "Minor issue"},
                {"severity": "critical", "description": "Critical issue"},
                {"severity": "medium", "description": "Medium issue"},
                {"severity": "high", "description": "High issue"},
            ],
        }
        (reports_dir / "arch-review-task-123.yaml").write_text(yaml.dump(report))

        findings = merge_findings(str(reports_dir))

        severities = [f["severity"] for f in findings]
        assert severities == ["critical", "high", "medium", "low"]

    def test_empty_directory_returns_empty_list(self, reports_dir: Path) -> None:
        """空のディレクトリは空のリストを返す"""
        findings = merge_findings(str(reports_dir))
        assert findings == []

    def test_adds_source_reviewer_to_findings(self, reports_dir: Path) -> None:
        """各findingにレビュアー情報を追加する"""
        report = {
            "task_id": "task-123",
            "reviewer": "security-reviewer",
            "result": "needs_fix",
            "findings": [
                {"severity": "high", "description": "Issue"},
            ],
        }
        (reports_dir / "security-review-task-123.yaml").write_text(yaml.dump(report))

        findings = merge_findings(str(reports_dir))

        assert findings[0]["source"] == "security-review"
