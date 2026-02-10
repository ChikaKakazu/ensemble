"""
アトミックロック機構

ファイルベースのアトミック操作を提供する。
mvコマンド（os.rename）のアトミック性を利用。
"""

from __future__ import annotations

import fcntl
import os
import tempfile
import time
from pathlib import Path


def atomic_write(filepath: str, content: str) -> bool:
    """
    アトミックな書き込みを行う

    tmp作成 → mv（アトミック）で安全に書き込む。
    同一ファイルシステム上でのos.renameはアトミック。

    Args:
        filepath: 書き込み先ファイルパス
        content: 書き込む内容

    Returns:
        成功時True、失敗時False
    """
    dir_path = os.path.dirname(filepath)

    # 親ディレクトリが存在しない場合は失敗
    if dir_path and not os.path.exists(dir_path):
        return False

    try:
        # tmpファイルを同じディレクトリに作成（同一ファイルシステム保証）
        fd, tmp_path = tempfile.mkstemp(dir=dir_path if dir_path else ".")
        try:
            os.write(fd, content.encode("utf-8"))
            os.close(fd)
            os.rename(tmp_path, filepath)  # アトミック
            return True
        except Exception:
            # 失敗時はtmpファイルを削除
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return False
    except Exception:
        return False


def atomic_write_with_lock(filepath: str, content: str, timeout: float = 5.0) -> bool:
    """
    flock排他ロック + atomic write（tmp + rename）

    複数プロセスからの並列書き込みを排他制御し、YAML破損を防ぐ。
    Shogun inbox_write.shの実装に倣い、以下を実現:
    - flockによる排他ロック（タイムアウト付き）
    - tmpファイル作成 → renameでアトミック書き込み
    - 3回リトライ

    Args:
        filepath: 書き込み先ファイルパス
        content: 書き込む内容
        timeout: ロック取得タイムアウト（秒）

    Returns:
        成功時True、失敗時False
    """
    dir_path = os.path.dirname(filepath)

    # 親ディレクトリが存在しない場合は失敗
    if dir_path and not os.path.exists(dir_path):
        return False

    lock_file_path = Path(filepath).with_suffix(Path(filepath).suffix + ".lock")
    max_attempts = 3

    for attempt in range(max_attempts):
        lock_fd = None
        try:
            # ロックファイルを開く（作成）
            lock_fd = os.open(str(lock_file_path), os.O_CREAT | os.O_WRONLY, 0o644)

            # 非ブロッキングでロック取得を試みる（タイムアウト実装）
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # ロック取得成功
                    break
                except BlockingIOError:
                    # ロック取得失敗、タイムアウトチェック
                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Failed to acquire lock within {timeout}s")
                    time.sleep(0.1)  # 100ms待機後リトライ

            # tmpファイルを同じディレクトリに作成（同一ファイルシステム保証）
            fd, tmp_path = tempfile.mkstemp(dir=dir_path if dir_path else ".")
            try:
                os.write(fd, content.encode("utf-8"))
                os.close(fd)
                os.rename(tmp_path, filepath)  # アトミック
                return True
            except Exception:
                # 失敗時はtmpファイルを削除
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise  # リトライのために再送出

        except (TimeoutError, Exception) as e:
            # ロック取得失敗またはエラー
            if attempt < max_attempts - 1:
                # リトライ
                time.sleep(1)
                continue
            else:
                # 最終試行でも失敗
                return False

        finally:
            # ロック解放 + ロックファイル削除
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                except Exception:
                    pass

            try:
                lock_file_path.unlink(missing_ok=True)
            except Exception:
                pass

    return False


def atomic_claim(filepath: str, processing_dir: str) -> str | None:
    """
    アトミックなタスク取得を行う

    mv（アトミック）で処理中ディレクトリへ移動することで、
    複数プロセス間での排他制御を実現。

    Args:
        filepath: 取得対象のファイルパス
        processing_dir: 処理中ファイルの移動先ディレクトリ

    Returns:
        成功時は移動先パス、失敗時（別プロセスが先に取得）はNone
    """
    filename = os.path.basename(filepath)
    dest = os.path.join(processing_dir, filename)

    try:
        os.rename(filepath, dest)  # アトミック
        return dest
    except FileNotFoundError:
        # 別プロセスが先に取得した場合
        return None
    except Exception:
        return None
