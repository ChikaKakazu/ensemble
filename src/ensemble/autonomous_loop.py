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

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ensemble.logger import NDJSONLogger
from ensemble.loop_detector import LoopDetector


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
        use_scan: bool = False,
    ) -> None:
        """
        Args:
            work_dir: 作業ディレクトリ
            config: ループ設定（Noneならデフォルト）
            use_queue: TaskQueueからタスクを取得するモード
            use_scan: CodebaseScannerからタスクを取得するモード
        """
        self.work_dir = work_dir
        self.config = config or LoopConfig()
        self.use_queue = use_queue
        self.use_scan = use_scan
        self.iteration = 0
        self.logger = NDJSONLogger()
        self.loop_detector = LoopDetector(max_iterations=5)
        self._processed_scan_keys: set[str] = set()

    def run(self) -> LoopResult:
        """ループを実行する

        Returns:
            LoopResult: 実行結果
        """
        commits: list[str] = []
        errors: list[str] = []

        # プロンプトファイル確認（キュー/スキャンモードでない場合）
        if not self.use_queue and not self.use_scan:
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

        # queueモード用のインスタンスを事前作成
        queue_instance = None
        if self.use_queue:
            from ensemble.queue import TaskQueue
            queue_instance = TaskQueue(base_dir=self.work_dir / "queue")

        for i in range(self.config.max_iterations):
            self.iteration = i + 1

            # タスク取得モード分岐
            current_task_id: str | None = None
            if self.use_scan:
                task_command = self._get_scan_task()
                if task_command is None:
                    self.logger.log_event(
                        "loop_scan_empty",
                        {"iteration": self.iteration},
                    )
                    return LoopResult(
                        iterations_completed=i,
                        status=LoopStatus.QUEUE_EMPTY,
                        commits=commits,
                        errors=errors,
                    )
                # scanモード用のタスクキー生成（重複検知用）
                current_task_id = self._make_scan_task_key(task_command)
            elif self.use_queue:
                task_data = self._claim_queue_task(queue_instance)
                if task_data is None:
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
                current_task_id = task_data.get("task_id")
                task_command = task_data.get("command")
            else:
                task_command = None  # プロンプトファイルモード
                current_task_id = f"prompt-iteration-{self.iteration}"

            # ループ検知
            if current_task_id and self.loop_detector.record(current_task_id):
                count = self.loop_detector.get_count(current_task_id)
                self.logger.log_event(
                    "loop_detected",
                    {"task_id": current_task_id, "count": count},
                )
                return LoopResult(
                    iterations_completed=i,
                    status=LoopStatus.LOOP_DETECTED,
                    commits=commits,
                    errors=errors + [f"Loop detected: {current_task_id} ({count} times)"],
                )

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

            # queueモード: タスク完了報告
            if self.use_queue and queue_instance and current_task_id:
                try:
                    if success:
                        queue_instance.complete(current_task_id, result="success", output="")
                    else:
                        queue_instance.complete(
                            current_task_id, result="error", output="", error=error
                        )
                except Exception:
                    pass  # 完了報告失敗はログのみ

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

    # 機密ファイルパターン（git add から除外）
    _SENSITIVE_PATTERNS = {
        ".env", ".env.local", ".env.production", ".env.staging",
        "credentials.json", "credentials.yaml",
        "secret", "token",
    }
    _SENSITIVE_EXTENSIONS = {".key", ".pem", ".p12", ".pfx", ".jks"}

    def _is_sensitive_file(self, filepath: str) -> bool:
        """機密ファイルかどうかを判定する"""
        name = filepath.lower().split("/")[-1]
        # 完全一致チェック
        if name in self._SENSITIVE_PATTERNS:
            return True
        # 部分一致チェック
        if any(p in name for p in ("secret", "credential", "token", "api_key", "apikey")):
            return True
        # 拡張子チェック
        for ext in self._SENSITIVE_EXTENSIONS:
            if name.endswith(ext):
                return True
        return False

    def _commit_iteration(self) -> str | None:
        """イテレーション後にgitコミットする

        Returns:
            コミットハッシュ（変更なしの場合はNone）
        """
        try:
            # 変更ファイル一覧を取得
            diff_result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
            )

            # 未追跡ファイルも含める
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                cwd=str(self.work_dir),
            )

            changed_files = [
                f for f in (diff_result.stdout.strip() + "\n" + untracked_result.stdout.strip()).split("\n")
                if f.strip()
            ]

            if not changed_files:
                return None

            # 機密ファイルを除外して個別にadd
            safe_files = [f for f in changed_files if not self._is_sensitive_file(f)]
            if not safe_files:
                return None

            subprocess.run(
                ["git", "add"] + safe_files,
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

    def _make_scan_task_key(self, task_command: str) -> str:
        """scanモードのタスクコマンドからユニークキーを生成する"""
        return hashlib.md5(task_command.encode()).hexdigest()[:12]

    def _claim_queue_task(self, queue_instance) -> dict | None:
        """TaskQueueからタスクをclaim（取得）する

        Returns:
            タスクデータ辞書（キューが空の場合はNone）
        """
        if queue_instance is None:
            return None
        try:
            return queue_instance.claim()
        except Exception:
            return None

    def _get_scan_task(self) -> str | None:
        """CodebaseScannerからタスクを取得する

        Returns:
            タスクコマンド（タスクなしの場合はNone）
        """
        try:
            from ensemble.scanner import CodebaseScanner

            scanner = CodebaseScanner(root_dir=self.work_dir, exclude_tests=True)
            result = scanner.scan()

            if result.total == 0:
                return None

            # 最も優先度の高い未処理タスクを選択
            sorted_tasks = result.sorted_by_priority()
            task = None
            for candidate in sorted_tasks:
                # 処理済みタスクをスキップ（重複排除）
                key = f"{candidate.file_path}:{candidate.line_number}:{candidate.title}"
                candidate_hash = hashlib.md5(key.encode()).hexdigest()[:12]
                if candidate_hash not in self._processed_scan_keys:
                    task = candidate
                    self._processed_scan_keys.add(candidate_hash)
                    break

            if task is None:
                return None

            # タスクの情報をプロンプトとして構築
            prompt_parts = [
                f"Fix the following issue in this project:",
                f"",
                f"Task: {task.title}",
                f"Source: {task.source}",
                f"Priority: {task.priority.value}",
            ]
            if task.file_path:
                prompt_parts.append(f"File: {task.file_path}")
                if task.line_number:
                    prompt_parts.append(f"Line: {task.line_number}")
            if task.description:
                prompt_parts.append(f"Description: {task.description}")

            prompt_parts.extend([
                "",
                "Please fix this issue, write tests if needed, and ensure all existing tests pass.",
            ])

            return "\n".join(prompt_parts)

        except Exception:
            return None

