"""アトミックロック機構のテスト"""

import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ensemble.lock import atomic_claim, atomic_write, atomic_write_with_lock


class TestAtomicWrite:
    """atomic_write のテスト"""

    def test_writes_file_atomically(self, tmp_path: Path) -> None:
        """ファイルがアトミックに書き込まれることを確認"""
        filepath = tmp_path / "test.txt"
        content = "Hello, World!"

        result = atomic_write(str(filepath), content)

        assert result is True
        assert filepath.exists()
        assert filepath.read_text() == content

    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        """成功時にTrueを返すことを確認"""
        filepath = tmp_path / "success.txt"
        result = atomic_write(str(filepath), "content")
        assert result is True

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """既存ファイルを上書きすることを確認"""
        filepath = tmp_path / "existing.txt"
        filepath.write_text("old content")

        atomic_write(str(filepath), "new content")

        assert filepath.read_text() == "new content"

    def test_handles_unicode_content(self, tmp_path: Path) -> None:
        """Unicode文字を正しく書き込むことを確認"""
        filepath = tmp_path / "unicode.txt"
        content = "日本語テスト 🎵"

        atomic_write(str(filepath), content)

        assert filepath.read_text() == content

    def test_creates_file_in_nonexistent_parent(self, tmp_path: Path) -> None:
        """親ディレクトリが存在しない場合はFalseを返す（またはエラー）"""
        filepath = tmp_path / "nonexistent" / "test.txt"

        # 親ディレクトリがなければ失敗
        result = atomic_write(str(filepath), "content")
        assert result is False


class TestAtomicClaim:
    """atomic_claim のテスト"""

    def test_moves_file_to_processing_dir(self, tmp_path: Path) -> None:
        """ファイルを処理中ディレクトリに移動することを確認"""
        source = tmp_path / "tasks" / "task.yaml"
        processing = tmp_path / "processing"

        source.parent.mkdir(parents=True)
        processing.mkdir()
        source.write_text("task content")

        result = atomic_claim(str(source), str(processing))

        assert result == str(processing / "task.yaml")
        assert not source.exists()
        assert (processing / "task.yaml").exists()

    def test_returns_none_if_file_not_found(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合はNoneを返すことを確認"""
        source = tmp_path / "nonexistent.yaml"
        processing = tmp_path / "processing"
        processing.mkdir()

        result = atomic_claim(str(source), str(processing))

        assert result is None

    def test_returns_none_if_already_claimed(self, tmp_path: Path) -> None:
        """既に別プロセスが取得済みの場合はNoneを返すことを確認"""
        source = tmp_path / "tasks" / "task.yaml"
        processing = tmp_path / "processing"

        source.parent.mkdir(parents=True)
        processing.mkdir()
        source.write_text("task content")

        # 最初のclaimは成功
        result1 = atomic_claim(str(source), str(processing))
        assert result1 is not None

        # 2回目はファイルがないのでNone
        result2 = atomic_claim(str(source), str(processing))
        assert result2 is None

    def test_preserves_file_content(self, tmp_path: Path) -> None:
        """ファイル内容が保持されることを確認"""
        source = tmp_path / "tasks" / "task.yaml"
        processing = tmp_path / "processing"

        source.parent.mkdir(parents=True)
        processing.mkdir()

        original_content = "task_id: abc123\ncommand: build"
        source.write_text(original_content)

        result = atomic_claim(str(source), str(processing))

        assert result is not None
        claimed_file = Path(result)
        assert claimed_file.read_text() == original_content


class TestAtomicWriteWithLock:
    """atomic_write_with_lock のテスト"""

    def test_atomic_write_with_lock_basic(self, tmp_path: Path) -> None:
        """基本的な書き込みテスト"""
        filepath = tmp_path / "test.txt"
        content = "Hello, Locked World!"

        result = atomic_write_with_lock(str(filepath), content)

        assert result is True
        assert filepath.exists()
        assert filepath.read_text() == content

    def test_atomic_write_with_lock_concurrent(self, tmp_path: Path) -> None:
        """並列書き込みテスト（10スレッド同時書き込み）"""
        filepath = tmp_path / "concurrent.txt"
        num_threads = 10
        results = []
        errors = []

        def write_thread(thread_id: int) -> None:
            try:
                content = f"Thread {thread_id}\n"
                result = atomic_write_with_lock(str(filepath), content)
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=write_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 全てのスレッドが成功したことを確認
        assert len(results) == num_threads
        assert all(result for _, result in results)
        assert len(errors) == 0

        # ファイルが正常に書き込まれていることを確認
        assert filepath.exists()
        # 最後のスレッドの内容が書き込まれている
        content = filepath.read_text()
        assert content.startswith("Thread ")

    def test_atomic_write_with_lock_creates_and_removes_lockfile(
        self, tmp_path: Path
    ) -> None:
        """ロックファイルの作成・削除確認"""
        filepath = tmp_path / "locktest.txt"
        lock_filepath = Path(str(filepath) + ".lock")
        content = "Lock test content"

        # 書き込み前はロックファイルが存在しない
        assert not lock_filepath.exists()

        result = atomic_write_with_lock(str(filepath), content)

        # 書き込み成功
        assert result is True
        assert filepath.exists()

        # 書き込み後はロックファイルが削除されている
        assert not lock_filepath.exists()

    def test_atomic_write_with_lock_nonexistent_dir(self) -> None:
        """存在しないディレクトリへの書き込みがFalseを返す"""
        filepath = "/nonexistent_dir_12345/test.txt"
        content = "This should fail"

        result = atomic_write_with_lock(filepath, content)

        assert result is False

    def test_atomic_write_with_lock_preserves_original_on_failure(
        self, tmp_path: Path
    ) -> None:
        """失敗時に元ファイルが保持される"""
        filepath = tmp_path / "preserve.txt"
        original_content = "Original content"
        filepath.write_text(original_content)

        # os.renameを失敗させる（モック使用）
        with patch("ensemble.lock.os.rename", side_effect=OSError("Mocked error")):
            result = atomic_write_with_lock(str(filepath), "New content")

        # 書き込み失敗
        assert result is False

        # 元のファイルが保持されている
        assert filepath.exists()
        assert filepath.read_text() == original_content

    def test_atomic_write_with_lock_overwrites_existing(self, tmp_path: Path) -> None:
        """既存ファイルを上書きすることを確認"""
        filepath = tmp_path / "overwrite.txt"
        filepath.write_text("Old content")

        result = atomic_write_with_lock(str(filepath), "New content")

        assert result is True
        assert filepath.read_text() == "New content"

    def test_atomic_write_with_lock_handles_unicode(self, tmp_path: Path) -> None:
        """Unicode文字を正しく書き込むことを確認"""
        filepath = tmp_path / "unicode.txt"
        content = "日本語テスト 🔒"

        result = atomic_write_with_lock(str(filepath), content)

        assert result is True
        assert filepath.read_text() == content


class TestQueueUsesLockedWrite:
    """TaskQueueがflock版を使用していることを確認"""

    def test_queue_enqueue_uses_locked_write(self, tmp_path: Path) -> None:
        """TaskQueue.enqueue()がatomic_write_with_lockを使用"""
        from ensemble.queue import TaskQueue

        queue = TaskQueue(base_dir=tmp_path / "queue")

        # atomic_write_with_lockが呼ばれることを確認
        with patch("ensemble.queue.atomic_write_with_lock") as mock_write:
            mock_write.return_value = True
            task_id = queue.enqueue("test command", "test-agent")

        # atomic_write_with_lockが呼ばれたことを確認
        assert mock_write.called

    def test_queue_complete_uses_locked_write(self, tmp_path: Path) -> None:
        """TaskQueue.complete()がatomic_write_with_lockを使用"""
        from ensemble.queue import TaskQueue

        queue = TaskQueue(base_dir=tmp_path / "queue")

        # atomic_write_with_lockが呼ばれることを確認
        with patch("ensemble.queue.atomic_write_with_lock") as mock_write:
            mock_write.return_value = True
            queue.complete("test-task-id", "success", "output", None)

        # atomic_write_with_lockが呼ばれたことを確認
        assert mock_write.called
