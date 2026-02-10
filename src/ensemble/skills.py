"""
Ensemble Skills管理モジュール

タスク種別に応じてWorkerにSkillsを動的注入する。
"""

from __future__ import annotations

from pathlib import Path


class SkillManager:
    """
    Skillsの判定・読み込み・注入を管理する
    """

    # スキル判定用のパターン
    SKILL_PATTERNS = {
        "testing": ["test_", "_test.py", "/tests/", "pytest", "unittest"],
        "backend-api": ["api/", "routes/", "views/", "endpoints/", "controllers/"],
        "react-frontend": [
            "components/",
            "pages/",
            "app/",
            ".tsx",
            ".jsx",
            "hooks/",
        ],
        "database-migration": [
            "migrations/",
            "schema.sql",
            "alembic/",
            "migrate",
            "db/",
        ],
        "security-audit": ["auth", "password", "token", "jwt", "session", "security"],
    }

    def __init__(self, skills_dir: Path | None = None) -> None:
        """
        Args:
            skills_dir: スキル定義ディレクトリ（デフォルト: .claude/skills/）
        """
        self.skills_dir = skills_dir if skills_dir else Path(".claude/skills")

    def determine_skills(
        self, files: list[str] | None = None, instruction: str | None = None
    ) -> list[str]:
        """
        タスク内容から必要なスキルを判定

        Args:
            files: 対象ファイルリスト
            instruction: タスク指示文

        Returns:
            必要なスキルのリスト（例: ["testing", "backend-api"]）
        """
        skills = set()
        files = files or []
        instruction = instruction or ""

        # ファイルパスから判定
        for skill, patterns in self.SKILL_PATTERNS.items():
            for pattern in patterns:
                if any(pattern.lower() in f.lower() for f in files):
                    skills.add(skill)
                    break

        # 指示文から判定
        instruction_lower = instruction.lower()
        for skill, patterns in self.SKILL_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in instruction_lower:
                    skills.add(skill)
                    break

        return sorted(list(skills))

    def load_skill(self, skill_name: str) -> str | None:
        """
        スキル定義を読み込む

        Args:
            skill_name: スキル名（例: "testing"）

        Returns:
            スキル定義の内容（見つからない場合はNone）
        """
        skill_file = self.skills_dir / f"{skill_name}.md"
        if not skill_file.exists():
            return None

        return skill_file.read_text()

    def inject_skills(self, skills: list[str]) -> str:
        """
        スキル定義を結合して注入用のテキストを生成

        Args:
            skills: スキル名のリスト

        Returns:
            注入用のマークダウンテキスト
        """
        if not skills:
            return ""

        sections = []
        sections.append("# 📚 Injected Skills\n")
        sections.append(
            "以下のスキルがこのタスクに関連すると判定されました。\n"
        )

        for skill in skills:
            content = self.load_skill(skill)
            if content:
                sections.append(f"## Skill: {skill}\n")
                sections.append(content)
                sections.append("\n---\n")
            else:
                sections.append(
                    f"## Skill: {skill}\n（スキル定義が見つかりません）\n---\n"
                )

        return "\n".join(sections)

    def list_available_skills(self) -> list[str]:
        """
        利用可能なスキルの一覧を取得

        Returns:
            スキル名のリスト
        """
        if not self.skills_dir.exists():
            return []

        skills = []
        for skill_file in self.skills_dir.glob("*.md"):
            skills.append(skill_file.stem)

        return sorted(skills)
