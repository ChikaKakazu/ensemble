"""
inotifywaitベースのファイル監視システム

Ensembleのqueue/ディレクトリを監視し、ファイル変更をイベント駆動で検知する。
inbox_watcher.shをPythonから制御する。
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional


class InboxWatcher:
    """
    inotifywaitベースのファイル監視デーモン

    inbox_watcher.shをバックグラウンドで起動し、プロセス管理を行う。
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        """
        Args:
            project_dir: プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）
        """
        self.project_dir = project_dir if project_dir else Path.cwd()
        self.pid_file = self.project_dir / ".ensemble" / "inbox_watcher.pid"
        self.script_path = self._find_script()
        self.process: Optional[subprocess.Popen] = None

    def _find_script(self) -> Path:
        """
        inbox_watcher.shのパスを解決する

        優先順位:
        1. プロジェクト内: scripts/inbox_watcher.sh
        2. テンプレート: src/ensemble/templates/scripts/inbox_watcher.sh
        """
        # プロジェクト内スクリプト
        local_script = self.project_dir / "scripts" / "inbox_watcher.sh"
        if local_script.exists():
            return local_script

        # テンプレートスクリプト
        template_script = (
            self.project_dir / "src" / "ensemble" / "templates" / "scripts" / "inbox_watcher.sh"
        )
        if template_script.exists():
            return template_script

        raise FileNotFoundError(
            f"inbox_watcher.sh not found in {local_script} or {template_script}"
        )

    def start(self) -> None:
        """
        inbox_watcher.shをバックグラウンドで起動する

        Raises:
            RuntimeError: 既に起動している場合
        """
        if self.is_running():
            raise RuntimeError(
                f"inbox_watcher is already running (PID: {self._read_pid()})"
            )

        # inotifywaitの存在確認（警告のみ、スクリプト側でフォールバック）
        if not self.ensure_inotifywait():
            print(
                "Warning: inotify-tools not installed. "
                "inbox_watcher will use polling mode (5-second interval)."
            )
            print("For better performance, install inotify-tools:")
            print("  Ubuntu/Debian: sudo apt-get install inotify-tools")
            print("  macOS: brew install fswatch (alternative)")

        # バックグラウンド起動
        env = os.environ.copy()
        env["PROJECT_DIR"] = str(self.project_dir)

        self.process = subprocess.Popen(
            ["bash", str(self.script_path)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # デーモン化
        )

        # PIDファイルが作成されるまで待機（最大3秒）
        for _ in range(30):
            if self.pid_file.exists():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Failed to start inbox_watcher (PID file not created)")

        print(f"inbox_watcher started (PID: {self._read_pid()})")

    def stop(self) -> None:
        """
        inbox_watcher.shを停止する

        SIGTERM送信 → 最大5秒待機 → SIGKILL送信
        """
        pid = self._read_pid()
        if pid is None:
            print("inbox_watcher is not running")
            return

        try:
            # SIGTERM送信
            os.kill(pid, signal.SIGTERM)

            # プロセス終了を待機（最大5秒）
            for _ in range(50):
                if not self._is_process_alive(pid):
                    break
                time.sleep(0.1)
            else:
                # タイムアウト → SIGKILL
                print(f"inbox_watcher (PID: {pid}) did not stop gracefully, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)

                # SIGKILL後も少し待機
                for _ in range(10):
                    if not self._is_process_alive(pid):
                        break
                    time.sleep(0.1)

            # PIDファイル削除
            if self.pid_file.exists():
                self.pid_file.unlink()

            print(f"inbox_watcher stopped (PID: {pid})")

        except ProcessLookupError:
            # プロセスが既に終了している
            if self.pid_file.exists():
                self.pid_file.unlink()
            print("inbox_watcher was already stopped")

    def is_running(self) -> bool:
        """
        inbox_watcher.shが起動しているか確認する

        Returns:
            起動している場合True
        """
        pid = self._read_pid()
        if pid is None:
            return False
        return self._is_process_alive(pid)

    def _read_pid(self) -> Optional[int]:
        """
        PIDファイルからPIDを読み込む

        Returns:
            PID、またはファイルが存在しない場合None
        """
        if not self.pid_file.exists():
            return None

        try:
            return int(self.pid_file.read_text().strip())
        except (ValueError, OSError):
            return None

    def _is_process_alive(self, pid: int) -> bool:
        """
        プロセスが生存しているか確認する

        Args:
            pid: プロセスID

        Returns:
            生存している場合True
        """
        try:
            # signal 0はプロセスにシグナルを送らず、存在確認のみ
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # プロセスは存在するが権限がない → 存在する
            return True

    @staticmethod
    def ensure_inotifywait() -> bool:
        """
        inotifywaitコマンドがインストールされているか確認する

        Returns:
            インストールされている場合True
        """
        return shutil.which("inotifywait") is not None
