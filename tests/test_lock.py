"""アトミックロック機構のテスト"""

import os
import tempfile
from pathlib import Path

import pytest

from ensemble.lock import atomic_claim, atomic_write


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
