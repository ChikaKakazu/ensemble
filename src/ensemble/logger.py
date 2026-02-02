"""
Ensembleログ出力モジュール

コンソール: テキスト形式（人間が読みやすい）
ファイル: JSON形式（機械可読、分析容易）
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class EnsembleLogger:
    """
    Ensemble用ログ出力クラス

    コンソール: テキスト形式（人間が読みやすい）
    ファイル: JSON形式（機械可読、分析容易）
    """

    def __init__(self, name: str = "ensemble", log_dir: Path | None = None) -> None:
        """
        ロガーを初期化する

        Args:
            name: ロガー名
            log_dir: ログ出力ディレクトリ（デフォルト: logs/）
        """
        self.name = name
        self.log_dir = log_dir if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True)

    def _get_log_file(self) -> Path:
        """今日のログファイルパスを取得"""
        today = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"ensemble-{today}.log"

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """
        構造化ログを出力する

        Args:
            level: ログレベル (DEBUG, INFO, WARNING, ERROR)
            message: ログメッセージ
            **kwargs: 追加の構造化データ
        """
        now = datetime.now()

        # コンソール: テキスト形式
        time_str = now.strftime("%H:%M:%S")
        print(f"{time_str} [{level}] {message}")

        # ファイル: JSON形式
        log_entry = {
            "timestamp": now.isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        with open(self._get_log_file(), "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUGレベルでログ出力"""
        self.log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """INFOレベルでログ出力"""
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNINGレベルでログ出力"""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """ERRORレベルでログ出力"""
        self.log("ERROR", message, **kwargs)
