"""
tests/test_worktree.py - worktreeモジュールのテスト

TDD: テストを先に書き、実装を後から行う。
"""

import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ensemble.worktree import (
    WorktreeInfo,
    ConflictFile,
    ConflictReport,
    list_worktrees,
    detect_conflicts,
    parse_conflict_markers,
    generate_conflict_report,
    is_auto_resolvable,
    get_worktree_branch,
)


class TestWorktreeInfo:
    """WorktreeInfo データクラスのテスト"""

    def test_create_worktree_info(self):
        """WorktreeInfoを作成できる"""
        info = WorktreeInfo(
            path="/path/to/worktree",
            branch="ensemble/feature-auth",
            head="abc1234",
            is_bare=False,
        )
        assert info.path == "/path/to/worktree"
        assert info.branch == "ensemble/feature-auth"
        assert info.head == "abc1234"
        assert info.is_bare is False

    def test_worktree_info_str(self):
        """WorktreeInfoの文字列表現"""
        info = WorktreeInfo(
            path="/path/to/worktree",
            branch="ensemble/feature-auth",
            head="abc1234",
            is_bare=False,
        )
        assert "feature-auth" in str(info)


class TestConflictFile:
    """ConflictFile データクラスのテスト"""

    def test_create_conflict_file(self):
        """ConflictFileを作成できる"""
        conflict = ConflictFile(
            file_path="src/api/routes.py",
            conflict_type="both_modified",
            ours_content="line from ours",
            theirs_content="line from theirs",
            auto_resolvable=True,
        )
        assert conflict.file_path == "src/api/routes.py"
        assert conflict.conflict_type == "both_modified"
        assert conflict.auto_resolvable is True


class TestConflictReport:
    """ConflictReport データクラスのテスト"""

    def test_create_conflict_report(self):
        """ConflictReportを作成できる"""
        conflicts = [
            ConflictFile(
                file_path="src/api/routes.py",
                conflict_type="both_modified",
                ours_content="",
                theirs_content="",
                auto_resolvable=True,
            )
        ]
        report = ConflictReport(
            worktree_path="/path/to/worktree",
            branch="ensemble/feature-auth",
            main_branch="main",
            conflicts=conflicts,
            has_conflicts=True,
        )
        assert report.has_conflicts is True
        assert len(report.conflicts) == 1

    def test_to_yaml(self):
        """ConflictReportをYAML形式に変換できる"""
        conflicts = [
            ConflictFile(
                file_path="src/api/routes.py",
                conflict_type="both_modified",
                ours_content="",
                theirs_content="",
                auto_resolvable=False,
            )
        ]
        report = ConflictReport(
            worktree_path="/path/to/worktree",
            branch="ensemble/feature-auth",
            main_branch="main",
            conflicts=conflicts,
            has_conflicts=True,
        )
        yaml_str = report.to_yaml()
        assert "type: conflict" in yaml_str
        assert "ensemble/feature-auth" in yaml_str
        assert "src/api/routes.py" in yaml_str


class TestListWorktrees:
    """list_worktrees関数のテスト"""

    @patch("ensemble.worktree.subprocess.run")
    def test_list_worktrees_empty(self, mock_run):
        """worktreeがない場合は空リストを返す"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="/path/to/repo  abc1234 [main]\n",
        )
        worktrees = list_worktrees("/path/to/repo")
        # メインリポジトリのみの場合、空リストを返す（メインは除外）
        assert len(worktrees) == 0

    @patch("ensemble.worktree.subprocess.run")
    def test_list_worktrees_with_worktrees(self, mock_run):
        """複数のworktreeがある場合"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "/path/to/repo  abc1234 [main]\n"
                "/path/to/ensemble-feature-auth  def5678 [ensemble/feature-auth]\n"
                "/path/to/ensemble-feature-api  aaa9012 [ensemble/feature-api]\n"
            ),
        )
        worktrees = list_worktrees("/path/to/repo")
        assert len(worktrees) == 2
        assert worktrees[0].branch == "ensemble/feature-auth"
        assert worktrees[1].branch == "ensemble/feature-api"


class TestDetectConflicts:
    """detect_conflicts関数のテスト"""

    @patch("ensemble.worktree.subprocess.run")
    def test_no_conflicts(self, mock_run):
        """コンフリクトがない場合"""
        # merge --no-commit が成功
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        report = detect_conflicts(
            worktree_path="/path/to/worktree",
            branch="ensemble/feature-auth",
            main_branch="main",
        )
        assert report.has_conflicts is False
        assert len(report.conflicts) == 0

    @patch("ensemble.worktree.subprocess.run")
    def test_with_conflicts(self, mock_run):
        """コンフリクトがある場合"""

        def side_effect(cmd, **kwargs):
            if "merge" in cmd:
                result = MagicMock(returncode=1, stdout="", stderr="CONFLICT")
                return result
            elif "diff" in cmd and "--name-only" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="src/api/routes.py\nsrc/config/settings.py\n",
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        report = detect_conflicts(
            worktree_path="/path/to/worktree",
            branch="ensemble/feature-auth",
            main_branch="main",
        )
        assert report.has_conflicts is True
        assert len(report.conflicts) == 2


class TestParseConflictMarkers:
    """parse_conflict_markers関数のテスト"""

    def test_parse_simple_conflict(self):
        """単純なコンフリクトマーカーをパースできる"""
        content = """
def func():
<<<<<<< HEAD
    return "main"
=======
    return "feature"
>>>>>>> ensemble/feature-auth
"""
        ours, theirs = parse_conflict_markers(content)
        assert 'return "main"' in ours
        assert 'return "feature"' in theirs

    def test_no_conflict_markers(self):
        """コンフリクトマーカーがない場合"""
        content = """
def func():
    return "no conflict"
"""
        ours, theirs = parse_conflict_markers(content)
        assert ours == ""
        assert theirs == ""


class TestIsAutoResolvable:
    """is_auto_resolvable関数のテスト"""

    def test_import_additions_are_resolvable(self):
        """インポート文の追加は自動解決可能"""
        ours = "import os"
        theirs = "import sys"
        assert is_auto_resolvable("src/main.py", ours, theirs) is True

    def test_same_function_modified_not_resolvable(self):
        """同じ関数の修正は自動解決不可"""
        ours = "def process(x):\n    return x + 1"
        theirs = "def process(x):\n    return x * 2"
        assert is_auto_resolvable("src/main.py", ours, theirs) is False

    def test_config_changes_not_resolvable(self):
        """設定ファイルの同じキー変更は自動解決不可"""
        ours = "DEBUG = False"
        theirs = "DEBUG = True"
        assert is_auto_resolvable("config/settings.py", ours, theirs) is False

    def test_independent_additions_resolvable(self):
        """独立した追加は自動解決可能"""
        ours = "def func_a():\n    pass"
        theirs = "def func_b():\n    pass"
        assert is_auto_resolvable("src/utils.py", ours, theirs) is True


class TestGetWorktreeBranch:
    """get_worktree_branch関数のテスト"""

    @patch("ensemble.worktree.subprocess.run")
    def test_get_branch_name(self, mock_run):
        """worktreeのブランチ名を取得できる"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ensemble/feature-auth\n",
        )
        branch = get_worktree_branch("/path/to/worktree")
        assert branch == "ensemble/feature-auth"


class TestGenerateConflictReport:
    """generate_conflict_report関数のテスト"""

    def test_generate_yaml_report(self, tmp_path):
        """YAML形式のレポートを生成できる"""
        conflicts = [
            ConflictFile(
                file_path="src/api/routes.py",
                conflict_type="both_modified",
                ours_content="",
                theirs_content="",
                auto_resolvable=False,
            )
        ]
        report = ConflictReport(
            worktree_path="/path/to/worktree",
            branch="ensemble/feature-auth",
            main_branch="main",
            conflicts=conflicts,
            has_conflicts=True,
        )

        output_path = tmp_path / "conflict-report.yaml"
        generate_conflict_report(report, str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "type: conflict" in content
        assert "ensemble/feature-auth" in content


class TestIntegration:
    """統合テスト（実際のgitリポジトリを使用）"""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """テスト用のgitリポジトリを作成"""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        # git init
        subprocess.run(
            ["git", "init"], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # 初期コミット
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        return repo_path

    def test_list_worktrees_integration(self, git_repo):
        """実際のgitリポジトリでworktree一覧を取得"""
        worktrees = list_worktrees(str(git_repo))
        # メインリポジトリのみなので空リスト
        assert len(worktrees) == 0

    def test_worktree_create_and_list(self, git_repo):
        """worktreeを作成してリストに含まれることを確認"""
        worktree_path = git_repo.parent / "test-worktree"

        # worktree作成
        subprocess.run(
            ["git", "worktree", "add", "-b", "feature-test", str(worktree_path)],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        worktrees = list_worktrees(str(git_repo))
        assert len(worktrees) == 1
        assert worktrees[0].branch == "feature-test"

        # クリーンアップ
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_path)],
            cwd=git_repo,
            capture_output=True,
        )
