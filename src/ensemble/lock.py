"""
アトミックロック機構

ファイルベースのアトミック操作を提供する。
mvコマンド（os.rename）のアトミック性を利用。
"""

from __future__ import annotations

import os
import tempfile


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
