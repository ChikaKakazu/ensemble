"""
自律ループモード（Autonomous Loop Mode）

Anthropic "Building a C compiler with a team of parallel Claudes" 記事から着想。
Claudeを無限ループで実行し、タスク完了→次タスク取得を自動化する。

セーフティ:
- LoopDetectorで最大イテレーション数を制御
- 各イテレーションでgitコミット（ロールバック可能）
- タイムアウトで暴走防止
- ログファイルで全出力を記録

参照: docs/research/008-anthropic-c-compiler-article.md
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ensemble.logger import NDJSONLogger


class LoopStatus(Enum):
    """ループ終了ステータス"""

    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    ERROR = "error"
    QUEUE_EMPTY = "queue_empty"
    LOOP_DETECTED = "loop_detected"


@dataclass
class LoopConfig:
    """自律ループの設定

    Attributes:
        max_iterations: 最大イテレーション数（デフォルト: 50）
        task_timeout: 1イテレーションのタイムアウト秒数（デフォルト: 600）
        prompt_file: エージェントプロンプトファイル名（デフォルト: AGENT_PROMPT.md）
        model: 使用するモデル（デフォルト: sonnet）
        commit_each: 各イテレーションでコミットするか（デフォルト: True）
        log_dir: ログ出力ディレクトリ（デフォルト: .ensemble/logs/loop）
    """

    max_iterations: int = 50
    task_timeout: int = 600
    prompt_file: str = "AGENT_PROMPT.md"
    model: str = "sonnet"
    commit_each: bool = True
    log_dir: str = ".ensemble/logs/loop"

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if self.task_timeout <= 0:
            raise ValueError("task_timeout must be positive")


@dataclass
class LoopResult:
    """ループ実行結果

    Attributes:
        iterations_completed: 完了したイテレーション数
        status: 終了ステータス
        commits: 作成されたコミットハッシュのリスト
        errors: 発生したエラーのリスト
    """

    iterations_completed: int
    status: LoopStatus
    commits: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class AutonomousLoopRunner:
    """自律ループ実行エンジン

    記事のアプローチ:
    ```bash
    while true; do
      claude -p "$(cat AGENT_PROMPT.md)" --model opus &> "$LOGFILE"
    done
    ```

    これをPythonで構造化し、安全機構を追加したもの。
    """

    def __init__(
        self,
        work_dir: Path,
        config: LoopConfig | None = None,
        use_queue: bool = False,
    ) -> None:
        """
        Args:
            work_dir: 作業ディレクトリ
            config: ループ設定（Noneならデフォルト）
            use_queue: TaskQueueからタスクを取得するモード
        """
        self.work_dir = work_dir
        self.config = config or LoopConfig()
        self.use_queue = use_queue
        self.iteration = 0
        self.logger = NDJSONLogger()

    def run(self) -> LoopResult:
        """ループを実行する

        Returns:
            LoopResult: 実行結果
        """
        commits: list[str] = []
        errors: list[str] = []

        # プロンプトファイル確認（キューモードでない場合）
        if not self.use_queue:
            prompt_path = self.work_dir / self.config.prompt_file
            if not prompt_path.exists():
                self.logger.log_event(
                    "loop_error",
                    {"error": f"Prompt file not found: {self.config.prompt_file}"},
                )
                return LoopResult(
                    iterations_completed=0,
                    status=LoopStatus.ERROR,
                    commits=commits,
                    errors=[f"Prompt file not found: {self.config.prompt_file}"],
                )

        # ログディレクトリ作成
        log_dir = Path(self.config.log_dir)
        if not log_dir.is_absolute():
            log_dir = self.work_dir / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

        self.logger.log_event(
            "loop_start",
            {
                "max_iterations": self.config.max_iterations,
                "model": self.config.model,
                "use_queue": self.use_queue,
            },
        )

        for i in range(self.config.max_iterations):
            self.iteration = i + 1

            # キューモードの場合、タスクを取得
            if self.use_queue:
                task_command = self._get_queue_task()
                if task_command is None:
                    self.logger.log_event(
                        "loop_queue_empty",
                        {"iteration": self.iteration},
                    )
                    return LoopResult(
                        iterations_completed=i,
                        status=LoopStatus.QUEUE_EMPTY,
                        commits=commits,
                        errors=errors,
                    )
            else:
                task_command = None  # プロンプトファイルモード

            # イテレーション実行
            self.logger.log_event(
                "iteration_start",
                {"iteration": self.iteration},
            )

            success, error = self._execute_iteration(task_command, log_dir)

            if not success and error:
                errors.append(error)
                self.logger.log_event(
                    "iteration_error",
                    {"iteration": self.iteration, "error": error},
                )
            else:
                self.logger.log_event(
                    "iteration_complete",
                    {"iteration": self.iteration},
                )

            # コミット（成功時のみ、commit_each=Trueの場合）
            if self.config.commit_each and success:
                commit_hash = self._commit_iteration()
                if commit_hash:
                    commits.append(commit_hash)

        # 最大イテレーション到達
        self.logger.log_event(
            "loop_complete",
            {
                "iterations": self.iteration,
                "status": "max_iterations",
                "commits": len(commits),
                "errors": len(errors),
            },
        )

        return LoopResult(
            iterations_completed=self.iteration,
            status=LoopStatus.MAX_ITERATIONS,
            commits=commits,
            errors=errors,
        )

    def _execute_iteration(
        self,
        task_command: str | None,
        log_dir: Path,
    ) -> tuple[bool, str | None]:
        """1イテレーションを実行する

        Args:
            task_command: キューから取得したタスクコマンド（Noneならプロンプトファイル使用）
            log_dir: ログディレクトリ

        Returns:
            (成功フラグ, エラーメッセージ)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"iteration_{self.iteration}_{timestamp}.log"

        try:
            if task_command:
                # キューモード: タスクコマンドを直接実行
                cmd = [
                    "claude",
                    "--print",
                    "-m",
                    task_command,
                    "--model",
                    self.config.model,
                ]
            else:
                # プロンプトファイルモード
                prompt_path = self.work_dir / self.config.prompt_file
                prompt_content = prompt_path.read_text()
                cmd = [
                    "claude",
                    "--print",
                    "-p",
                    prompt_content,
                    "--model",
                    self.config.model,
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.task_timeout,
                cwd=str(self.work_dir),
            )

            # ログファイルに出力を保存
            log_file.write_text(
                f"=== Iteration {self.iteration} ===\n"
                f"Timestamp: {timestamp}\n"
                f"Exit code: {result.returncode}\n"
                f"--- STDOUT ---\n{result.stdout}\n"
                f"--- STDERR ---\n{result.stderr}\n"
            )

            if result.returncode != 0:
                return False, f"Iteration {self.iteration}: exit code {result.returncode}"

            return True, None

        except subprocess.TimeoutExpired:
            error_msg = f"Iteration {self.iteration}: timeout ({self.config.task_timeout}s)"
            log_file.write_text(f"=== Iteration {self.iteration} ===\nTIMEOUT\n")
            return False, error_msg

        except FileNotFoundError:
            return False, f"Iteration {self.iteration}: claude CLI not found"

    def _commit_iteration(self) -> str | None:
        """イテレーション後にgitコミットする

        Returns:
            コミットハッシュ（変更なしの場合はNone）
        """
        try:
            # 変更があるか確認
            diff_result = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
            )

            if not diff_result.stdout.strip():
                return None

            # git add .
            subprocess.run(
                ["git", "add", "."],
                check=True,
                capture_output=True,
                cwd=str(self.work_dir),
            )

            # git commit
            commit_msg = f"loop: iteration {self.iteration}\n\nAutonomous loop mode"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
                cwd=str(self.work_dir),
            )

            # コミットハッシュを取得
            hash_result = subprocess.run(
                ["git", "rev-parse", "--short=6", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
            )

            return hash_result.stdout.strip() if hash_result.returncode == 0 else None

        except subprocess.CalledProcessError:
            return None

    def _get_queue_task(self) -> str | None:
        """TaskQueueからタスクを取得する

        Returns:
            タスクコマンド（キューが空の場合はNone）
        """
        try:
            from ensemble.queue import TaskQueue

            queue = TaskQueue(base_dir=self.work_dir / "queue")
            task = queue.claim()

            if task is None:
                return None

            return task.get("command", None)

        except Exception:
            return None
