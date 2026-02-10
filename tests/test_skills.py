"""Skills管理のテスト"""

from pathlib import Path

import pytest

from ensemble.skills import SkillManager


class TestSkillManager:
    """SkillManager のテスト"""

    @pytest.fixture
    def skill_manager(self, tmp_path: Path) -> SkillManager:
        """テスト用SkillManagerを作成"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # テスト用スキル定義を作成
        (skills_dir / "testing.md").write_text("# Testing Skill\nTest content")
        (skills_dir / "backend-api.md").write_text(
            "# Backend API Skill\nAPI content"
        )

        return SkillManager(skills_dir=skills_dir)

    def test_determine_skills_from_files(self) -> None:
        """ファイルパスから必要なスキルを判定"""
        manager = SkillManager()

        # テストファイル
        skills = manager.determine_skills(files=["tests/test_user.py"])
        assert "testing" in skills

        # APIファイル
        skills = manager.determine_skills(files=["src/api/users.py"])
        assert "backend-api" in skills

        # Reactコンポーネント
        skills = manager.determine_skills(files=["src/components/Button.tsx"])
        assert "react-frontend" in skills

        # マイグレーション
        skills = manager.determine_skills(files=["migrations/001_add_users.sql"])
        assert "database-migration" in skills

    def test_determine_skills_from_instruction(self) -> None:
        """指示文から必要なスキルを判定"""
        manager = SkillManager()

        # テスト関連
        skills = manager.determine_skills(
            instruction="pytest でユニットテストを追加"
        )
        assert "testing" in skills

        # セキュリティ関連
        skills = manager.determine_skills(
            instruction="JWT認証を実装してセキュリティを強化"
        )
        assert "security-audit" in skills

    def test_determine_skills_multiple(self) -> None:
        """複数スキルの判定"""
        manager = SkillManager()

        skills = manager.determine_skills(
            files=["src/api/auth.py", "tests/test_auth.py"],
            instruction="認証APIのテストを追加",
        )

        # backend-api, testing, security-audit が含まれるはず
        assert "backend-api" in skills
        assert "testing" in skills
        assert "security-audit" in skills

    def test_determine_skills_no_match(self) -> None:
        """マッチしない場合は空リスト"""
        manager = SkillManager()

        skills = manager.determine_skills(
            files=["README.md"], instruction="ドキュメント更新"
        )
        assert skills == []

    def test_load_skill_exists(self, skill_manager: SkillManager) -> None:
        """スキル定義を読み込む（存在する場合）"""
        content = skill_manager.load_skill("testing")
        assert content is not None
        assert "Testing Skill" in content

    def test_load_skill_not_exists(self, skill_manager: SkillManager) -> None:
        """スキル定義を読み込む（存在しない場合）"""
        content = skill_manager.load_skill("nonexistent")
        assert content is None

    def test_inject_skills(self, skill_manager: SkillManager) -> None:
        """スキル定義を注入用テキストに変換"""
        injected = skill_manager.inject_skills(["testing", "backend-api"])

        assert "📚 Injected Skills" in injected
        assert "Skill: testing" in injected
        assert "Skill: backend-api" in injected
        assert "Testing Skill" in injected
        assert "Backend API Skill" in injected

    def test_inject_skills_empty(self, skill_manager: SkillManager) -> None:
        """スキルなしの場合は空文字列"""
        injected = skill_manager.inject_skills([])
        assert injected == ""

    def test_inject_skills_not_found(self, skill_manager: SkillManager) -> None:
        """存在しないスキルの場合はメッセージを表示"""
        injected = skill_manager.inject_skills(["nonexistent"])

        assert "Skill: nonexistent" in injected
        assert "スキル定義が見つかりません" in injected

    def test_list_available_skills(self, skill_manager: SkillManager) -> None:
        """利用可能なスキルの一覧を取得"""
        skills = skill_manager.list_available_skills()

        assert "testing" in skills
        assert "backend-api" in skills
        assert len(skills) == 2  # テスト用に2つ作成した


class TestSkillManagerIntegration:
    """実際のスキル定義を使用した統合テスト"""

    def test_real_skills_exist(self) -> None:
        """実際のスキル定義が存在することを確認"""
        manager = SkillManager(skills_dir=Path(".claude/skills"))
        skills = manager.list_available_skills()

        # 5つのスキル定義が存在することを確認
        expected_skills = [
            "backend-api",
            "database-migration",
            "react-frontend",
            "security-audit",
            "testing",
        ]

        for skill in expected_skills:
            assert (
                skill in skills
            ), f"Skill '{skill}' not found in {manager.skills_dir}"

    def test_real_skill_content(self) -> None:
        """実際のスキル定義の内容を確認"""
        manager = SkillManager(skills_dir=Path(".claude/skills"))

        # testing.md
        testing_content = manager.load_skill("testing")
        assert testing_content is not None
        assert "TDD" in testing_content
        assert "pytest" in testing_content

        # backend-api.md
        api_content = manager.load_skill("backend-api")
        assert api_content is not None
        assert "RESTful" in api_content
        assert "HTTP" in api_content

        # react-frontend.md
        react_content = manager.load_skill("react-frontend")
        assert react_content is not None
        assert "React" in react_content
        assert "hooks" in react_content

        # database-migration.md
        db_content = manager.load_skill("database-migration")
        assert db_content is not None
        assert "migration" in db_content.lower()
        # 日本語表記（ロールバック）または英語表記（rollback）を確認
        assert ("rollback" in db_content.lower() or "ロールバック" in db_content)

        # security-audit.md
        security_content = manager.load_skill("security-audit")
        assert security_content is not None
        assert "OWASP" in security_content
        assert "injection" in security_content.lower()
