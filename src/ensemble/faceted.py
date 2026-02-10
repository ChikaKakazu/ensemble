"""
Faceted Prompting合成ロジック

エージェント定義を5つの関心（WHO/RULES/WHAT/CONTEXT/OUTPUT）に分離し、
宣言的に合成する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class FacetedPromptComposer:
    """Faceted Promptingでエージェントプロンプトを合成"""

    def __init__(self, base_dir: Path | None = None):
        """
        Args:
            base_dir: ベースディレクトリ（デフォルト: .claude/）
        """
        self.base_dir = base_dir if base_dir else Path(".claude")
        self.personas_dir = self.base_dir / "personas"
        self.policies_dir = self.base_dir / "policies"
        self.instructions_dir = self.base_dir / "instructions"
        self.knowledge_dir = self.base_dir / "knowledge"
        self.output_contracts_dir = self.base_dir / "output-contracts"

    def compose(
        self,
        agent_name: str,
        persona: str | None = None,
        policies: list[str] | None = None,
        instruction: str | None = None,
        knowledge: str | None = None,
        output_contract: str | None = None,
    ) -> str:
        """
        Faceted Promptingでエージェントプロンプトを合成

        Args:
            agent_name: エージェント名（conductor, worker, dispatch など）
            persona: Personaファイル名（Noneの場合はget_agent_configから取得）
            policies: Policyファイル名リスト（Noneの場合は全てのpolicy）
            instruction: Instructionファイル名（Noneの場合はget_agent_configから取得）
            knowledge: Knowledgeファイル名（Noneの場合はget_agent_configから取得）
            output_contract: Output Contractファイル名（Noneの場合はget_agent_configから取得）

        Returns:
            合成されたプロンプト文字列
        """
        # エージェント設定を取得（Noneのパラメータのデフォルト値として使用）
        config = self.get_agent_config(agent_name)

        sections = []

        # WHO: Persona
        persona_file = persona or config["persona"]
        persona_content = self._read_file(self.personas_dir / persona_file)
        if persona_content:
            sections.append(f"# {agent_name.upper()} AGENT\n\n{persona_content}")

        # RULES: Policies
        if policies is None:
            # 全てのpolicyを読み込む
            policy_files = sorted(self.policies_dir.glob("*.md"))
        else:
            policy_files = [self.policies_dir / f for f in policies]

        policy_contents = []
        for policy_file in policy_files:
            content = self._read_file(policy_file)
            if content:
                policy_contents.append(content)

        if policy_contents:
            sections.append(f"## RULES\n\n{chr(10).join(policy_contents)}")

        # WHAT: Instructions
        instruction_file = instruction or config["instruction"]
        instruction_content = self._read_file(self.instructions_dir / instruction_file)
        if instruction_content:
            sections.append(f"## INSTRUCTIONS\n\n{instruction_content}")

        # CONTEXT: Knowledge
        knowledge_file = knowledge or config["knowledge"]
        knowledge_content = self._read_file(self.knowledge_dir / knowledge_file)
        if knowledge_content:
            sections.append(f"## PROJECT CONTEXT\n\n{knowledge_content}")

        # OUTPUT: Output Contract
        output_contract_file = output_contract or config["output_contract"]
        output_contract_content = self._read_file(
            self.output_contracts_dir / output_contract_file
        )
        if output_contract_content:
            sections.append(f"## OUTPUT FORMAT\n\n{output_contract_content}")

        return "\n\n---\n\n".join(sections)

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """
        エージェントの設定を取得（personas, policies, instructions, knowledgeのマッピング）

        Args:
            agent_name: エージェント名

        Returns:
            エージェント設定辞書
        """
        # デフォルト設定
        config: dict[str, Any] = {
            "persona": f"{agent_name}.md",
            "policies": None,  # 全てのpolicy
            "instruction": f"{agent_name}.md",
            "knowledge": "project-specific.md",
            "output_contract": f"{agent_name}-report.md",
        }

        # エージェント別の特別な設定
        if agent_name == "conductor":
            config["instruction"] = "plan.md"
            config["output_contract"] = "completion-summary.md"
        elif agent_name == "worker":
            config["instruction"] = "implement.md"
            config["output_contract"] = "worker-report.md"
        elif agent_name == "dispatch":
            config["instruction"] = "dispatch.md"
            config["output_contract"] = "completion-summary.md"
        elif agent_name in ["reviewer", "security-reviewer"]:
            config["instruction"] = "review.md"
            config["output_contract"] = "review-report.md"
        elif agent_name == "integrator":
            config["instruction"] = "integrate.md"
        elif agent_name == "learner":
            config["instruction"] = "learn.md"

        return config

    def validate(self) -> list[str]:
        """
        Faceted Promptingディレクトリ構造を検証

        Returns:
            エラーメッセージのリスト（エラーがなければ空リスト）
        """
        errors = []

        # 必須ディレクトリの存在確認
        required_dirs = [
            self.personas_dir,
            self.policies_dir,
            self.instructions_dir,
            self.knowledge_dir,
            self.output_contracts_dir,
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                errors.append(f"Missing directory: {dir_path}")

        # 必須ファイルの存在確認
        required_files = [
            self.instructions_dir / "plan.md",
            self.instructions_dir / "implement.md",
            self.instructions_dir / "dispatch.md",
            self.knowledge_dir / "project-specific.md",
            self.output_contracts_dir / "worker-report.md",
            self.output_contracts_dir / "completion-summary.md",
        ]

        for file_path in required_files:
            if not file_path.exists():
                errors.append(f"Missing file: {file_path}")

        return errors

    def _read_file(self, file_path: Path) -> str:
        """
        ファイルを読み込む

        Args:
            file_path: ファイルパス

        Returns:
            ファイル内容（存在しない場合は空文字列）
        """
        if not file_path.exists():
            return ""

        try:
            return file_path.read_text(encoding="utf-8")
        except Exception:
            return ""
