"""
CI/CD Pipeline Mode for Ensemble

tmuxなしの非対話環境で実行可能なパイプラインモード。
標準出力にNDJSONログを出力し、終了コードで成否を返す。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ensemble.logger import NDJSONLogger

if TYPE_CHECKING:
    pass

# 終了コード定義
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_NEEDS_FIX = 2
EXIT_LOOP_DETECTED = 3


class PipelineRunner:
    """
    CI/CD環境向けの非対話パイプライン実行

    tmuxなしで順次実行し、標準出力にNDJSONログを出力する。
    終了コードで成否を返す。
    """

    def __init__(
        self,
        task: str,
        workflow: str = "default",
        auto_pr: bool = False,
        branch: str | None = None,
    ) -> None:
        """
        パイプラインランナーを初期化

        Args:
            task: タスク説明
            workflow: ワークフロー (simple/default/heavy)
            auto_pr: PR自動作成フラグ
            branch: ブランチ名（Noneなら自動生成）

        Raises:
            ValueError: 無効なワークフローが指定された場合
        """
        self.task = task
        self.workflow = workflow
        self.auto_pr = auto_pr
        self.branch = branch if branch else self._generate_branch_name(task)

        # ワークフローバリデーション
        valid_workflows = ["simple", "default", "heavy"]
        if workflow not in valid_workflows:
            raise ValueError(
                f"Invalid workflow: {workflow}. "
                f"Must be one of {', '.join(valid_workflows)}"
            )

        # NDJSONロガーを初期化（標準出力）
        self.logger = NDJSONLogger()

    def run(self) -> int:
        """
        パイプラインを実行

        実行フロー:
        1. ブランチ作成
        2. タスク実行
        3. レビュー実行
        4. コミット
        5. PR作成（--auto-prが指定されている場合）

        Returns:
            終了コード (EXIT_SUCCESS/EXIT_ERROR/EXIT_NEEDS_FIX/EXIT_LOOP_DETECTED)
        """
        self.logger.log_event("pipeline_start", {"task": self.task, "branch": self.branch})

        try:
            # Step 1: ブランチ作成
            self._create_branch()

            # Step 2: タスク実行
            task_result = self._execute_task()
            if task_result != EXIT_SUCCESS:
                return task_result

            # Step 3: レビュー実行（defaultまたはheavyワークフローの場合）
            if self.workflow in ["default", "heavy"]:
                review_result = self._run_review()
                if review_result != EXIT_SUCCESS:
                    return review_result

            # Step 4: コミット
            self._commit_changes()

            # Step 5: PR作成（--auto-prが指定されている場合）
            if self.auto_pr:
                self._create_pr()

            self.logger.log_event("pipeline_complete", {"status": "success"})
            return EXIT_SUCCESS

        except Exception as e:
            self.logger.log_event("pipeline_error", {"error": str(e)})
            print(f"Error: {e}", file=sys.stderr)
            return EXIT_ERROR

    def _create_branch(self) -> None:
        """ブランチを作成"""
        self.logger.log_event("branch_create", {"branch": self.branch})
        subprocess.run(["git", "checkout", "-b", self.branch], check=True)

    def _execute_task(self) -> int:
        """
        タスクを実行（claude CLI経由）

        Returns:
            終了コード
        """
        self.logger.log_event("task_execute_start", {"task": self.task})
        try:
            result = subprocess.run(
                ["claude", "--print", "-m", self.task],
                capture_output=True,
                text=True,
                timeout=600,  # 10分タイムアウト
            )
            if result.returncode != 0:
                self.logger.log_event("task_execute_error", {"stderr": result.stderr[:500]})
                return EXIT_ERROR
            self.logger.log_event("task_execute_complete", {"status": "success"})
            return EXIT_SUCCESS
        except subprocess.TimeoutExpired:
            self.logger.log_event("task_execute_timeout", {"timeout": 600})
            return EXIT_ERROR
        except FileNotFoundError:
            self.logger.log_event("task_execute_error", {"error": "claude CLI not found"})
            return EXIT_ERROR

    def _run_review(self) -> int:
        """
        レビューを実行（claude CLI経由）

        Returns:
            終了コード（approved=EXIT_SUCCESS, needs_fix=EXIT_NEEDS_FIX）
        """
        self.logger.log_event("review_start", {})
        try:
            review_prompt = (
                "Review the changes in this branch. Check for: "
                "1) Code quality 2) Security issues 3) Test coverage. "
                "Output 'approved' if no critical issues, or 'needs_fix' with details."
            )
            result = subprocess.run(
                ["claude", "--print", "-m", review_prompt],
                capture_output=True,
                text=True,
                timeout=300,  # 5分タイムアウト
            )
            if result.returncode != 0:
                self.logger.log_event("review_error", {"stderr": result.stderr[:500]})
                return EXIT_ERROR

            output = result.stdout.lower()
            if "needs_fix" in output:
                self.logger.log_event("review_complete", {"result": "needs_fix"})
                return EXIT_NEEDS_FIX

            self.logger.log_event("review_complete", {"result": "approved"})
            return EXIT_SUCCESS
        except subprocess.TimeoutExpired:
            self.logger.log_event("review_timeout", {"timeout": 300})
            return EXIT_ERROR
        except FileNotFoundError:
            self.logger.log_event("review_error", {"error": "claude CLI not found"})
            return EXIT_ERROR

    def _commit_changes(self) -> None:
        """変更をコミット"""
        self.logger.log_event("commit_start", {})

        # git add .
        subprocess.run(["git", "add", "."], check=True)

        # git commit
        commit_message = f"{self.task}\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True,
        )

        self.logger.log_event("commit_complete", {})

    def _create_pr(self) -> None:
        """PRを作成"""
        self.logger.log_event("pr_create_start", {})

        # git push
        subprocess.run(["git", "push", "-u", "origin", self.branch], check=True)

        # gh pr create
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                self.task,
                "--body",
                f"## Summary\n{self.task}\n\n🤖 Generated with Ensemble Pipeline Mode",
            ],
            check=True,
        )

        self.logger.log_event("pr_create_complete", {})

    def _generate_branch_name(self, task: str) -> str:
        """
        タスク説明からブランチ名を自動生成

        Args:
            task: タスク説明

        Returns:
            ブランチ名（例: feature/fix-auth-bug）
        """
        # 日本語を除去し、英数字とハイフンのみにする
        # アルファベット・数字・ハイフン・スペースのみを残す
        cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", task)

        # 連続するスペースを1つに統合
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # スペースをハイフンに変換
        branch_suffix = cleaned.replace(" ", "-").lower()

        # 空の場合はタイムスタンプを使用
        if not branch_suffix:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_suffix = f"task-{timestamp}"

        # 長すぎる場合は切り詰める（最大50文字）
        if len(branch_suffix) > 50:
            branch_suffix = branch_suffix[:50].rstrip("-")

        return f"feature/{branch_suffix}"
