"""
src/ensemble/worktree.py - git worktree操作ユーティリティ

worktreeの一覧取得、コンフリクト検出、レポート生成を行う。
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WorktreeInfo:
    """worktreeの情報"""

    path: str
    branch: str
    head: str
    is_bare: bool = False

    def __str__(self) -> str:
        return f"WorktreeInfo({self.branch} @ {self.path})"


@dataclass
class ConflictFile:
    """コンフリクトが発生したファイルの情報"""

    file_path: str
    conflict_type: str  # "both_modified", "deleted_by_us", "deleted_by_them"
    ours_content: str
    theirs_content: str
    auto_resolvable: bool = False


@dataclass
class ConflictReport:
    """コンフリクトレポート"""

    worktree_path: str
    branch: str
    main_branch: str
    conflicts: list[ConflictFile] = field(default_factory=list)
    has_conflicts: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_yaml(self) -> str:
        """YAML形式に変換"""
        lines = [
            "type: conflict",
            f"timestamp: {self.timestamp}",
            f"worktree: {self.worktree_path}",
            f"branch: {self.branch}",
            f"main_branch: {self.main_branch}",
            f"has_conflicts: {str(self.has_conflicts).lower()}",
            "conflict_files:",
        ]

        for conflict in self.conflicts:
            lines.extend(
                [
                    f"  - file: {conflict.file_path}",
                    f"    type: {conflict.conflict_type}",
                    f"    auto_resolvable: {str(conflict.auto_resolvable).lower()}",
                ]
            )

        return "\n".join(lines)


def list_worktrees(repo_path: str) -> list[WorktreeInfo]:
    """
    gitリポジトリのworktree一覧を取得する

    Args:
        repo_path: gitリポジトリのパス

    Returns:
        WorktreeInfoのリスト（メインリポジトリは除外）
    """
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    worktrees = []
    lines = result.stdout.strip().split("\n")

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        # パース: /path/to/worktree  abc1234 [branch-name]
        match = re.match(r"^(\S+)\s+([a-f0-9]+)\s+\[(.+)\]$", line.strip())
        if match:
            path, head, branch = match.groups()

            # 最初の行（メインリポジトリ）は除外
            if i == 0:
                continue

            worktrees.append(
                WorktreeInfo(
                    path=path,
                    branch=branch,
                    head=head,
                    is_bare=False,
                )
            )

    return worktrees


def get_worktree_branch(worktree_path: str) -> str:
    """
    worktreeのブランチ名を取得

    Args:
        worktree_path: worktreeのパス

    Returns:
        ブランチ名
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def detect_conflicts(
    worktree_path: str,
    branch: str,
    main_branch: str = "main",
) -> ConflictReport:
    """
    worktreeをメインブランチにマージする際のコンフリクトを検出

    Args:
        worktree_path: worktreeのパス
        branch: マージするブランチ名
        main_branch: マージ先のブランチ名

    Returns:
        ConflictReport
    """
    # dry-runでマージを試行
    result = subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # コンフリクトなし - マージをアボート
        subprocess.run(
            ["git", "merge", "--abort"],
            cwd=worktree_path,
            capture_output=True,
        )
        return ConflictReport(
            worktree_path=worktree_path,
            branch=branch,
            main_branch=main_branch,
            has_conflicts=False,
        )

    # コンフリクトあり - ファイル一覧を取得
    diff_result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    conflict_files = []
    for file_path in diff_result.stdout.strip().split("\n"):
        if not file_path:
            continue

        # ファイル内容を読み取り
        full_path = Path(worktree_path) / file_path
        if full_path.exists():
            content = full_path.read_text()
            ours, theirs = parse_conflict_markers(content)
            auto_resolvable = is_auto_resolvable(file_path, ours, theirs)
        else:
            ours, theirs = "", ""
            auto_resolvable = False

        conflict_files.append(
            ConflictFile(
                file_path=file_path,
                conflict_type="both_modified",
                ours_content=ours,
                theirs_content=theirs,
                auto_resolvable=auto_resolvable,
            )
        )

    # マージをアボート
    subprocess.run(
        ["git", "merge", "--abort"],
        cwd=worktree_path,
        capture_output=True,
    )

    return ConflictReport(
        worktree_path=worktree_path,
        branch=branch,
        main_branch=main_branch,
        conflicts=conflict_files,
        has_conflicts=True,
    )


def parse_conflict_markers(content: str) -> tuple[str, str]:
    """
    コンフリクトマーカーをパースして、ours/theirsの内容を抽出

    Args:
        content: ファイル内容

    Returns:
        (ours_content, theirs_content) のタプル
    """
    # <<<<<<< HEAD
    # ours content
    # =======
    # theirs content
    # >>>>>>> branch
    pattern = r"<<<<<<< .*?\n(.*?)\n=======\n(.*?)\n>>>>>>> .*?"

    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return "", ""


def is_auto_resolvable(
    file_path: str, ours_content: str, theirs_content: str
) -> bool:
    """
    コンフリクトが自動解決可能かどうかを判定

    自動解決可能なケース:
    - インポート文の追加
    - 独立した関数/クラスの追加

    自動解決不可のケース:
    - 同じ関数/クラスの異なる修正
    - 設定値の競合

    Args:
        file_path: ファイルパス
        ours_content: oursの内容
        theirs_content: theirsの内容

    Returns:
        自動解決可能ならTrue
    """
    if not ours_content or not theirs_content:
        return False

    # インポート文のみの場合は自動解決可能
    import_pattern = r"^(import |from .* import )"
    ours_is_import = bool(re.match(import_pattern, ours_content.strip()))
    theirs_is_import = bool(re.match(import_pattern, theirs_content.strip()))

    if ours_is_import and theirs_is_import:
        return True

    # 独立した関数/クラス定義の追加
    def_pattern = r"^(def |class |async def )"
    ours_is_def = bool(re.match(def_pattern, ours_content.strip()))
    theirs_is_def = bool(re.match(def_pattern, theirs_content.strip()))

    if ours_is_def and theirs_is_def:
        # 同じ名前の関数/クラスでなければ自動解決可能
        ours_name = _extract_def_name(ours_content)
        theirs_name = _extract_def_name(theirs_content)
        if ours_name and theirs_name and ours_name != theirs_name:
            return True

    # 設定ファイルの同じキーは自動解決不可
    if "config" in file_path.lower() or "settings" in file_path.lower():
        return False

    return False


def _extract_def_name(content: str) -> Optional[str]:
    """関数/クラス名を抽出"""
    match = re.match(r"^(?:async )?(?:def|class)\s+(\w+)", content.strip())
    if match:
        return match.group(1)
    return None


def generate_conflict_report(report: ConflictReport, output_path: str) -> None:
    """
    コンフリクトレポートをファイルに出力

    Args:
        report: ConflictReport
        output_path: 出力先パス
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.to_yaml())
