"""学習ノート管理のテスト"""

from pathlib import Path
from datetime import datetime

import pytest

from ensemble.notes import (
    create_task_notes_dir,
    write_lessons,
    write_skill_candidates,
    write_decisions,
    read_lessons,
    read_skill_candidates,
    list_task_notes,
    get_notes_summary,
)


class TestCreateTaskNotesDir:
    """create_task_notes_dir関数のテスト"""

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """タスクノート用ディレクトリ構造を作成する"""
        notes_dir = tmp_path / "notes"
        result = create_task_notes_dir(str(notes_dir), "task-001")

        assert result.exists()
        assert result.name == "task-001"
        assert result.parent.name == "notes"

    def test_returns_existing_directory(self, tmp_path: Path) -> None:
        """既存ディレクトリは再作成せず返す"""
        notes_dir = tmp_path / "notes"
        first = create_task_notes_dir(str(notes_dir), "task-001")
        second = create_task_notes_dir(str(notes_dir), "task-001")

        assert first == second

    def test_creates_multiple_task_dirs(self, tmp_path: Path) -> None:
        """複数タスクのディレクトリを作成できる"""
        notes_dir = tmp_path / "notes"
        dir1 = create_task_notes_dir(str(notes_dir), "task-001")
        dir2 = create_task_notes_dir(str(notes_dir), "task-002")

        assert dir1.exists()
        assert dir2.exists()
        assert dir1 != dir2


class TestWriteLessons:
    """write_lessons関数のテスト"""

    @pytest.fixture
    def task_dir(self, tmp_path: Path) -> Path:
        """テスト用タスクディレクトリを作成"""
        task_dir = tmp_path / "notes" / "task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    def test_writes_lessons_file(self, task_dir: Path) -> None:
        """lessons.mdファイルを作成する"""
        lessons = {
            "successes": ["テストが全てパス", "設計がシンプル"],
            "improvements": [
                {
                    "issue": "エラーハンドリング不足",
                    "cause": "例外パターンの見落とし",
                    "solution": "エッジケーステストを先に書く",
                }
            ],
            "metrics": {
                "fix_count": 2,
                "test_failures": 1,
                "review_issues": 3,
            },
        }

        write_lessons(task_dir, "task-001", lessons)

        lessons_file = task_dir / "lessons.md"
        assert lessons_file.exists()
        content = lessons_file.read_text()
        assert "task-001" in content
        assert "テストが全てパス" in content
        assert "エラーハンドリング不足" in content

    def test_updates_existing_lessons(self, task_dir: Path) -> None:
        """既存のlessons.mdを上書きする"""
        (task_dir / "lessons.md").write_text("# Old content")

        lessons = {
            "successes": ["新しい成功"],
            "improvements": [],
            "metrics": {"fix_count": 0, "test_failures": 0, "review_issues": 0},
        }
        write_lessons(task_dir, "task-001", lessons)

        content = (task_dir / "lessons.md").read_text()
        assert "新しい成功" in content
        assert "Old content" not in content


class TestWriteSkillCandidates:
    """write_skill_candidates関数のテスト"""

    @pytest.fixture
    def task_dir(self, tmp_path: Path) -> Path:
        """テスト用タスクディレクトリを作成"""
        task_dir = tmp_path / "notes" / "task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    def test_writes_skill_candidates_file(self, task_dir: Path) -> None:
        """skill-candidates.mdファイルを作成する"""
        candidates = [
            {
                "name": "api-error-handler",
                "purpose": "APIエラーの統一ハンドリング",
                "occurrences": 5,
                "cost": "low",
                "recommended": True,
            },
            {
                "name": "config-loader",
                "purpose": "環境設定の読み込み",
                "occurrences": 2,
                "cost": "medium",
                "recommended": False,
            },
        ]

        write_skill_candidates(task_dir, candidates)

        skills_file = task_dir / "skill-candidates.md"
        assert skills_file.exists()
        content = skills_file.read_text()
        assert "api-error-handler" in content
        assert "APIエラーの統一ハンドリング" in content
        assert "YES" in content  # recommended: True

    def test_empty_candidates_writes_empty_section(self, task_dir: Path) -> None:
        """空の候補リストでも有効なファイルを作成"""
        write_skill_candidates(task_dir, [])

        skills_file = task_dir / "skill-candidates.md"
        assert skills_file.exists()
        content = skills_file.read_text()
        assert "スキル化候補" in content


class TestWriteDecisions:
    """write_decisions関数のテスト"""

    @pytest.fixture
    def task_dir(self, tmp_path: Path) -> Path:
        """テスト用タスクディレクトリを作成"""
        task_dir = tmp_path / "notes" / "task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    def test_writes_decisions_file(self, task_dir: Path) -> None:
        """decisions.mdファイルを作成する"""
        decisions = [
            {
                "timestamp": "2024-01-15T10:30:00",
                "context": "データベース選択",
                "decision": "PostgreSQLを採用",
                "rationale": "JSONBサポートとスケーラビリティ",
            }
        ]

        write_decisions(task_dir, "task-001", decisions)

        decisions_file = task_dir / "decisions.md"
        assert decisions_file.exists()
        content = decisions_file.read_text()
        assert "PostgreSQLを採用" in content
        assert "JSONBサポート" in content

    def test_appends_to_existing_decisions(self, task_dir: Path) -> None:
        """既存のdecisions.mdに追記する"""
        existing = "# 決定ログ\n\n## 既存の決定\n- 古い決定"
        (task_dir / "decisions.md").write_text(existing)

        decisions = [
            {
                "timestamp": "2024-01-15T11:00:00",
                "context": "新しい決定",
                "decision": "Redisを追加",
                "rationale": "キャッシュ用",
            }
        ]

        write_decisions(task_dir, "task-001", decisions, append=True)

        content = (task_dir / "decisions.md").read_text()
        assert "古い決定" in content
        assert "Redisを追加" in content


class TestReadLessons:
    """read_lessons関数のテスト"""

    @pytest.fixture
    def task_dir(self, tmp_path: Path) -> Path:
        """テスト用タスクディレクトリを作成"""
        task_dir = tmp_path / "notes" / "task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    def test_reads_lessons_content(self, task_dir: Path) -> None:
        """lessons.mdの内容を読み込む"""
        content = "# タスク: task-001\n\n## 成功したこと\n- テスト成功"
        (task_dir / "lessons.md").write_text(content)

        result = read_lessons(task_dir)

        assert result is not None
        assert "テスト成功" in result

    def test_returns_none_for_missing_file(self, task_dir: Path) -> None:
        """ファイルが存在しない場合はNoneを返す"""
        result = read_lessons(task_dir)
        assert result is None


class TestReadSkillCandidates:
    """read_skill_candidates関数のテスト"""

    @pytest.fixture
    def task_dir(self, tmp_path: Path) -> Path:
        """テスト用タスクディレクトリを作成"""
        task_dir = tmp_path / "notes" / "task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    def test_reads_skill_candidates_content(self, task_dir: Path) -> None:
        """skill-candidates.mdの内容を読み込む"""
        content = "# スキル化候補\n\n## 候補1: api-handler"
        (task_dir / "skill-candidates.md").write_text(content)

        result = read_skill_candidates(task_dir)

        assert result is not None
        assert "api-handler" in result

    def test_returns_none_for_missing_file(self, task_dir: Path) -> None:
        """ファイルが存在しない場合はNoneを返す"""
        result = read_skill_candidates(task_dir)
        assert result is None


class TestListTaskNotes:
    """list_task_notes関数のテスト"""

    def test_lists_all_task_directories(self, tmp_path: Path) -> None:
        """全タスクディレクトリをリストする"""
        notes_dir = tmp_path / "notes"
        (notes_dir / "task-001").mkdir(parents=True)
        (notes_dir / "task-002").mkdir(parents=True)
        (notes_dir / "task-003").mkdir(parents=True)

        result = list_task_notes(str(notes_dir))

        assert len(result) == 3
        assert "task-001" in result
        assert "task-002" in result
        assert "task-003" in result

    def test_returns_empty_list_for_empty_dir(self, tmp_path: Path) -> None:
        """空のディレクトリは空のリストを返す"""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()

        result = list_task_notes(str(notes_dir))
        assert result == []

    def test_returns_empty_list_for_nonexistent_dir(self, tmp_path: Path) -> None:
        """存在しないディレクトリは空のリストを返す"""
        result = list_task_notes(str(tmp_path / "nonexistent"))
        assert result == []

    def test_ignores_files(self, tmp_path: Path) -> None:
        """ファイルは無視してディレクトリのみ返す"""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "task-001").mkdir()
        (notes_dir / "readme.md").write_text("readme")

        result = list_task_notes(str(notes_dir))

        assert result == ["task-001"]


class TestGetNotesSummary:
    """get_notes_summary関数のテスト"""

    def test_returns_summary_of_all_notes(self, tmp_path: Path) -> None:
        """全ノートの要約を返す"""
        notes_dir = tmp_path / "notes"
        task1 = notes_dir / "task-001"
        task1.mkdir(parents=True)
        (task1 / "lessons.md").write_text("# Lessons for task-001")
        (task1 / "skill-candidates.md").write_text("# Skills")

        task2 = notes_dir / "task-002"
        task2.mkdir(parents=True)
        (task2 / "lessons.md").write_text("# Lessons for task-002")

        result = get_notes_summary(str(notes_dir))

        assert len(result) == 2
        assert result["task-001"]["has_lessons"] is True
        assert result["task-001"]["has_skill_candidates"] is True
        assert result["task-002"]["has_lessons"] is True
        assert result["task-002"]["has_skill_candidates"] is False

    def test_returns_empty_dict_for_empty_dir(self, tmp_path: Path) -> None:
        """空のディレクトリは空の辞書を返す"""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()

        result = get_notes_summary(str(notes_dir))
        assert result == {}
