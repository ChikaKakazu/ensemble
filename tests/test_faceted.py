"""Faceted Prompting合成ロジックのテスト"""

from pathlib import Path

import pytest

from ensemble.faceted import FacetedPromptComposer


class TestFacetedPromptComposer:
    """FacetedPromptComposer のテスト"""

    def test_compose_basic(self, tmp_path: Path) -> None:
        """基本的な合成テスト"""
        # テスト用ディレクトリ構造を作成
        base_dir = tmp_path / ".claude"
        personas_dir = base_dir / "personas"
        instructions_dir = base_dir / "instructions"
        knowledge_dir = base_dir / "knowledge"
        output_contracts_dir = base_dir / "output-contracts"
        policies_dir = base_dir / "policies"

        personas_dir.mkdir(parents=True)
        instructions_dir.mkdir(parents=True)
        knowledge_dir.mkdir(parents=True)
        output_contracts_dir.mkdir(parents=True)
        policies_dir.mkdir(parents=True)

        # テスト用ファイルを作成
        (personas_dir / "conductor.md").write_text("WHO: You are Conductor")
        (policies_dir / "security.md").write_text("RULES: Security policy")
        (instructions_dir / "plan.md").write_text("WHAT: Plan instructions")
        (knowledge_dir / "project-specific.md").write_text("CONTEXT: Project knowledge")
        (output_contracts_dir / "completion-summary.md").write_text(
            "OUTPUT: Completion format"
        )

        # 合成
        composer = FacetedPromptComposer(base_dir=base_dir)
        result = composer.compose("conductor")

        # 各セクションが含まれることを確認
        assert "WHO: You are Conductor" in result
        assert "RULES: Security policy" in result
        assert "WHAT: Plan instructions" in result
        assert "CONTEXT: Project knowledge" in result
        assert "OUTPUT: Completion format" in result

    def test_compose_with_specific_files(self, tmp_path: Path) -> None:
        """特定のファイルを指定して合成"""
        base_dir = tmp_path / ".claude"
        personas_dir = base_dir / "personas"
        instructions_dir = base_dir / "instructions"
        policies_dir = base_dir / "policies"

        personas_dir.mkdir(parents=True)
        instructions_dir.mkdir(parents=True)
        policies_dir.mkdir(parents=True)

        (personas_dir / "worker.md").write_text("You are Worker")
        (instructions_dir / "implement.md").write_text("Implementation steps")
        (policies_dir / "coding.md").write_text("Coding standards")
        (policies_dir / "security.md").write_text("Security policy")

        composer = FacetedPromptComposer(base_dir=base_dir)
        result = composer.compose(
            "worker",
            persona="worker.md",
            policies=["coding.md"],  # securityは含めない
            instruction="implement.md",
        )

        assert "You are Worker" in result
        assert "Implementation steps" in result
        assert "Coding standards" in result
        assert "Security policy" not in result  # 指定していないので含まれない

    def test_compose_missing_files(self, tmp_path: Path) -> None:
        """存在しないファイルを指定した場合"""
        base_dir = tmp_path / ".claude"
        base_dir.mkdir(parents=True)

        composer = FacetedPromptComposer(base_dir=base_dir)
        result = composer.compose("nonexistent")

        # エラーにならず、空または最小限のプロンプトが返る
        assert isinstance(result, str)

    def test_get_agent_config_conductor(self, tmp_path: Path) -> None:
        """Conductorの設定を取得"""
        composer = FacetedPromptComposer(base_dir=tmp_path)
        config = composer.get_agent_config("conductor")

        assert config["persona"] == "conductor.md"
        assert config["instruction"] == "plan.md"
        assert config["output_contract"] == "completion-summary.md"
        assert config["knowledge"] == "project-specific.md"

    def test_get_agent_config_worker(self, tmp_path: Path) -> None:
        """Workerの設定を取得"""
        composer = FacetedPromptComposer(base_dir=tmp_path)
        config = composer.get_agent_config("worker")

        assert config["persona"] == "worker.md"
        assert config["instruction"] == "implement.md"
        assert config["output_contract"] == "worker-report.md"

    def test_get_agent_config_dispatch(self, tmp_path: Path) -> None:
        """Dispatchの設定を取得"""
        composer = FacetedPromptComposer(base_dir=tmp_path)
        config = composer.get_agent_config("dispatch")

        assert config["persona"] == "dispatch.md"
        assert config["instruction"] == "dispatch.md"
        assert config["output_contract"] == "completion-summary.md"

    def test_validate_complete_structure(self, tmp_path: Path) -> None:
        """完全なディレクトリ構造の検証"""
        base_dir = tmp_path / ".claude"
        personas_dir = base_dir / "personas"
        instructions_dir = base_dir / "instructions"
        knowledge_dir = base_dir / "knowledge"
        output_contracts_dir = base_dir / "output-contracts"
        policies_dir = base_dir / "policies"

        # ディレクトリを作成
        for d in [
            personas_dir,
            instructions_dir,
            knowledge_dir,
            output_contracts_dir,
            policies_dir,
        ]:
            d.mkdir(parents=True)

        # 必須ファイルを作成
        (instructions_dir / "plan.md").write_text("Plan")
        (instructions_dir / "implement.md").write_text("Implement")
        (instructions_dir / "dispatch.md").write_text("Dispatch")
        (knowledge_dir / "project-specific.md").write_text("Knowledge")
        (output_contracts_dir / "worker-report.md").write_text("Worker report")
        (output_contracts_dir / "completion-summary.md").write_text("Summary")

        composer = FacetedPromptComposer(base_dir=base_dir)
        errors = composer.validate()

        assert len(errors) == 0

    def test_validate_missing_directories(self, tmp_path: Path) -> None:
        """ディレクトリが欠けている場合の検証"""
        base_dir = tmp_path / ".claude"
        base_dir.mkdir(parents=True)

        composer = FacetedPromptComposer(base_dir=base_dir)
        errors = composer.validate()

        # 5つの必須ディレクトリが欠けている
        assert len(errors) >= 5
        assert any("personas" in err for err in errors)
        assert any("policies" in err for err in errors)
        assert any("instructions" in err for err in errors)
        assert any("knowledge" in err for err in errors)
        assert any("output-contracts" in err for err in errors)


class TestActualTemplates:
    """実際のテンプレートファイルを使用したテスト"""

    def test_compose_with_actual_templates(self) -> None:
        """実際のテンプレートファイルを使って合成"""
        base_dir = Path("src/ensemble/templates")
        composer = FacetedPromptComposer(base_dir=base_dir)

        # Conductorの合成（personasとpoliciesがないため、instructions以降のみ）
        result = composer.compose("conductor")

        # 少なくともinstructions, knowledge, output-contractsが含まれるはず
        assert len(result) > 0

    def test_validate_actual_templates(self) -> None:
        """実際のテンプレートディレクトリ構造を検証"""
        base_dir = Path("src/ensemble/templates")
        composer = FacetedPromptComposer(base_dir=base_dir)

        errors = composer.validate()

        # personas, policiesディレクトリは存在するが、中身は空の可能性がある
        # instructions, knowledge, output-contractsのファイルは存在するはず
        # エラーがあれば、必須ファイルが欠けている

        # 必須ファイルが全て存在するかチェック
        required_files_exist = all([
            (base_dir / "instructions" / "plan.md").exists(),
            (base_dir / "instructions" / "implement.md").exists(),
            (base_dir / "instructions" / "dispatch.md").exists(),
            (base_dir / "knowledge" / "project-specific.md").exists(),
            (base_dir / "output-contracts" / "worker-report.md").exists(),
            (base_dir / "output-contracts" / "completion-summary.md").exists(),
        ])

        if required_files_exist:
            # 必須ファイルが全て存在すれば、エラーはないはず
            assert len(errors) == 0
        else:
            # 必須ファイルが欠けていれば、エラーがあるはず
            assert len(errors) > 0
