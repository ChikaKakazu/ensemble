"""
タスク候補調査モジュール（ensemble investigate）

scan結果のタスク候補を調査し、実行優先度・工数・推奨アクションを判定する。

調査戦略:
1. Agent Teams: Conductor直接操作で並列調査（推奨）
2. Subprocess: 専用Claude Codeセッションで順次調査
3. Inline: 現在のセッション内で調査（最軽量）

参照: .claude/rules/agent-teams.md
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ensemble.scanner import TaskCandidate


class InvestigationStrategy(Enum):
    """調査戦略"""

    AGENT_TEAMS = "agent_teams"
    SUBPROCESS = "subprocess"
    INLINE = "inline"


@dataclass
class InvestigationResult:
    """調査結果

    Attributes:
        task_title: タスクタイトル
        findings: 調査結果の要約
        recommendation: 推奨アクション
        estimated_effort: 見積もり工数（small/medium/large）
        priority_adjustment: 優先度調整（high/medium/low/None）
    """

    task_title: str
    findings: str
    recommendation: str
    estimated_effort: str
    priority_adjustment: str | None = None


class TaskInvestigator:
    """タスク候補調査エンジン

    scan結果のTaskCandidateを受け取り、Claude Codeで調査する。
    Agent Teamsが利用可能ならそれを使い、なければsubprocessで個別に調査。
    """

    def __init__(
        self,
        root_dir: Path,
        force_strategy: InvestigationStrategy | None = None,
        timeout: int = 120,
    ) -> None:
        """
        Args:
            root_dir: プロジェクトルートディレクトリ
            force_strategy: 強制する調査戦略（Noneなら自動検出）
            timeout: 1タスクあたりのタイムアウト秒数
        """
        self.root_dir = root_dir
        self.force_strategy = force_strategy
        self.timeout = timeout

    def detect_strategy(self) -> InvestigationStrategy:
        """利用可能な調査戦略を検出する

        Returns:
            最適な調査戦略
        """
        if self.force_strategy:
            return self.force_strategy

        # Agent Teams有効チェック
        if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1":
            return InvestigationStrategy.AGENT_TEAMS

        return InvestigationStrategy.SUBPROCESS

    def build_investigation_prompt(self, task: TaskCandidate) -> str:
        """タスク候補の調査プロンプトを構築する

        Args:
            task: 調査対象のタスク候補

        Returns:
            調査プロンプト文字列
        """
        parts = [
            "Investigate the following task candidate and provide analysis.",
            "",
            f"## Task: {task.title}",
            f"Source: {task.source}",
            f"Priority: {task.priority.value}",
        ]

        if task.file_path:
            parts.append(f"File: {task.file_path}")
            if task.line_number:
                parts.append(f"Line: {task.line_number}")

        if task.description:
            parts.append(f"Description: {task.description}")

        parts.extend([
            "",
            "## Instructions",
            "",
            "Analyze this task and respond ONLY with valid JSON (no markdown, no extra text):",
            "",
            '{"findings": "<what you found about this task>",',
            ' "recommendation": "<what action to take>",',
            ' "estimated_effort": "<small|medium|large>",',
            ' "priority_adjustment": "<high|medium|low|null>"}',
            "",
            "If the file path is provided, read the file and analyze the context.",
            "Focus on: impact, complexity, dependencies, and risks.",
        ])

        return "\n".join(parts)

    def investigate_single(self, task: TaskCandidate) -> InvestigationResult | None:
        """1つのタスク候補を調査する

        Args:
            task: 調査対象

        Returns:
            調査結果（失敗時はNone）
        """
        strategy = self.detect_strategy()

        if strategy == InvestigationStrategy.SUBPROCESS:
            return self._investigate_subprocess(task)
        elif strategy == InvestigationStrategy.INLINE:
            return self._investigate_inline(task)
        else:
            # Agent Teamsの場合もsubprocessで個別調査（単一タスクの場合）
            return self._investigate_subprocess(task)

    def investigate_batch(
        self,
        tasks: list[TaskCandidate],
        max_tasks: int = 10,
    ) -> list[InvestigationResult]:
        """複数のタスク候補をバッチ調査する

        Args:
            tasks: 調査対象のリスト
            max_tasks: 最大調査数

        Returns:
            調査結果のリスト
        """
        results: list[InvestigationResult] = []
        target_tasks = tasks[:max_tasks]

        for task in target_tasks:
            result = self.investigate_single(task)
            if result:
                results.append(result)

        return results

    def generate_agent_teams_script(
        self,
        tasks: list[TaskCandidate],
    ) -> str:
        """Agent Teams用の調査指示スクリプトを生成する

        Agent Teamsモードでは、Conductorがこのスクリプトを
        自然言語でAgent Teamsに渡す。

        Args:
            tasks: 調査対象のタスク候補

        Returns:
            Agent Teams向けの自然言語指示
        """
        task_descriptions = []
        for i, task in enumerate(tasks, 1):
            desc = f"{i}. {task.title}"
            if task.file_path:
                desc += f" (file: {task.file_path}"
                if task.line_number:
                    desc += f":{task.line_number}"
                desc += ")"
            desc += f" [priority: {task.priority.value}]"
            task_descriptions.append(desc)

        tasks_text = "\n".join(task_descriptions)

        return (
            f"Create an agent team to investigate {len(tasks)} task candidates.\n"
            f"Spawn {min(len(tasks), 4)} teammates to investigate different tasks in parallel.\n"
            f"Use Sonnet for all teammates.\n"
            f"\n"
            f"Tasks to investigate:\n"
            f"{tasks_text}\n"
            f"\n"
            f"Each teammate should:\n"
            f"1. Read the relevant source files\n"
            f"2. Analyze the impact and complexity\n"
            f"3. Estimate the effort (small/medium/large)\n"
            f"4. Recommend an action (fix/refactor/defer/close)\n"
            f"5. Suggest priority adjustment if needed\n"
            f"\n"
            f"Report findings in structured format."
        )

    def format_results(self, results: list[InvestigationResult]) -> str:
        """調査結果をテキスト形式にフォーマットする

        Args:
            results: 調査結果のリスト

        Returns:
            フォーマットされたテキスト
        """
        if not results:
            return "No investigation results."

        lines = [
            f"Investigation Report ({len(results)} tasks analyzed)",
            "=" * 50,
            "",
        ]

        for i, result in enumerate(results, 1):
            lines.append(f"### {i}. {result.task_title}")
            lines.append(f"  Findings: {result.findings}")
            lines.append(f"  Recommendation: {result.recommendation}")
            lines.append(f"  Effort: {result.estimated_effort}")
            if result.priority_adjustment:
                lines.append(f"  Priority adjustment: {result.priority_adjustment}")
            lines.append("")

        return "\n".join(lines)

    def _investigate_subprocess(self, task: TaskCandidate) -> InvestigationResult | None:
        """subprocessでClaude CLIを使って調査する"""
        prompt = self.build_investigation_prompt(task)

        try:
            result = subprocess.run(
                ["claude", "--print", "-m", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.root_dir),
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            return None

        if result.returncode != 0:
            return None

        return self._parse_response(task.title, result.stdout)

    def _investigate_inline(self, task: TaskCandidate) -> InvestigationResult | None:
        """インラインで簡易調査する（Claude呼び出しなし）"""
        return InvestigationResult(
            task_title=task.title,
            findings=f"Source: {task.source}, File: {task.file_path or 'N/A'}",
            recommendation="Needs further investigation",
            estimated_effort="unknown",
            priority_adjustment=None,
        )

    def _parse_response(self, task_title: str, response: str) -> InvestigationResult | None:
        """Claude CLIの応答をパースする"""
        # JSONブロックを抽出（マークダウンのコードブロック内の可能性あり）
        text = response.strip()

        # ```json ... ``` を除去
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()

        # JSON部分を抽出（{ から } まで）
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            text = text[json_start:json_end]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # パース失敗時はraw responseを使用
            return InvestigationResult(
                task_title=task_title,
                findings=response[:500],
                recommendation="Parse failed - manual review needed",
                estimated_effort="unknown",
            )

        return InvestigationResult(
            task_title=task_title,
            findings=data.get("findings", "No findings"),
            recommendation=data.get("recommendation", "No recommendation"),
            estimated_effort=data.get("estimated_effort", "unknown"),
            priority_adjustment=data.get("priority_adjustment"),
        )
