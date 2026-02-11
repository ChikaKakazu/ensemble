"""
コードベーススキャナー（ensemble scan）

セッション開始時にコードベースを分析し、タスク候補を自動生成する。

スキャン対象:
1. TODO/FIXME/HACK コメント
2. GitHub Issue（gh CLI経由）
3. PROGRESS.md/PLAN.md の未完了チェックボックス

参照: docs/research/008-anthropic-c-compiler-article.md
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskPriority(Enum):
    """タスク候補の優先度"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# 優先度のソート順
_PRIORITY_ORDER = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}

# スキャン除外ディレクトリ
_EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
    ".ensemble",
    "tmp",
}

# スキャン対象の拡張子
_TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".sh",
    ".bash",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}


@dataclass
class TaskCandidate:
    """タスク候補

    Attributes:
        source: タスクのソース（todo, github-issue, progress）
        title: タスクタイトル
        priority: 優先度
        description: 詳細説明（任意）
        file_path: ファイルパス（任意）
        line_number: 行番号（任意）
    """

    source: str
    title: str
    priority: TaskPriority
    description: str | None = None
    file_path: str | None = None
    line_number: int | None = None


@dataclass
class ScanResult:
    """スキャン結果

    Attributes:
        tasks: タスク候補のリスト
        scan_errors: スキャン中に発生したエラー
    """

    tasks: list[TaskCandidate] = field(default_factory=list)
    scan_errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """タスク候補の総数"""
        return len(self.tasks)

    def by_source(self) -> dict[str, list[TaskCandidate]]:
        """ソース別にグループ化"""
        groups: dict[str, list[TaskCandidate]] = defaultdict(list)
        for task in self.tasks:
            groups[task.source].append(task)
        return dict(groups)

    def sorted_by_priority(self) -> list[TaskCandidate]:
        """優先度順にソート"""
        return sorted(self.tasks, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))

    def format_text(self) -> str:
        """テキスト形式でフォーマット"""
        if not self.tasks:
            return "No task candidates found."

        lines = [f"Found {self.total} task candidate(s):", ""]

        sorted_tasks = self.sorted_by_priority()
        by_source = self.by_source()

        for source, tasks in sorted(by_source.items()):
            lines.append(f"## {source} ({len(tasks)} items)")
            for task in sorted(tasks, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99)):
                loc = ""
                if task.file_path:
                    loc = f" ({task.file_path}"
                    if task.line_number:
                        loc += f":{task.line_number}"
                    loc += ")"
                lines.append(f"  [{task.priority.value:6s}] {task.title}{loc}")
            lines.append("")

        if self.scan_errors:
            lines.append("## Scan Errors")
            for err in self.scan_errors:
                lines.append(f"  - {err}")

        return "\n".join(lines)


class CodebaseScanner:
    """コードベーススキャナー

    プロジェクトディレクトリを分析し、タスク候補を自動生成する。
    """

    def __init__(self, root_dir: Path, exclude_tests: bool = False) -> None:
        """
        Args:
            root_dir: プロジェクトルートディレクトリ
            exclude_tests: テストファイル/ディレクトリを除外するか
        """
        self.root_dir = root_dir
        self.exclude_tests = exclude_tests

    def scan(self) -> ScanResult:
        """全スキャンを実行し結果を統合する

        Returns:
            ScanResult: 統合されたスキャン結果
        """
        all_tasks: list[TaskCandidate] = []
        errors: list[str] = []

        # 1. TODO/FIXME/HACK
        try:
            all_tasks.extend(self.scan_todos())
        except Exception as e:
            errors.append(f"todo scan failed: {e}")

        # 2. GitHub Issues
        try:
            all_tasks.extend(self.scan_github_issues())
        except Exception as e:
            errors.append(f"github issue scan failed: {e}")

        # 3. PROGRESS.md / PLAN.md
        try:
            all_tasks.extend(self.scan_progress_files())
        except Exception as e:
            errors.append(f"progress scan failed: {e}")

        return ScanResult(tasks=all_tasks, scan_errors=errors)

    def scan_todos(self) -> list[TaskCandidate]:
        """TODO/FIXME/HACKコメントをスキャンする

        Returns:
            タスク候補のリスト
        """
        tasks: list[TaskCandidate] = []
        pattern = re.compile(
            r"#\s*(TODO|FIXME|HACK|XXX)\s*:?\s*(.*)",
            re.IGNORECASE,
        )
        # Also match // style comments
        pattern_slash = re.compile(
            r"//\s*(TODO|FIXME|HACK|XXX)\s*:?\s*(.*)",
            re.IGNORECASE,
        )

        for file_path in self._iter_text_files():
            try:
                content = file_path.read_text(errors="ignore")
            except (OSError, PermissionError):
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                match = pattern.search(line) or pattern_slash.search(line)
                if match:
                    tag = match.group(1).upper()
                    comment = match.group(2).strip()

                    # 優先度判定
                    if tag in ("FIXME", "XXX"):
                        priority = TaskPriority.HIGH
                    elif tag == "HACK":
                        priority = TaskPriority.MEDIUM
                    else:  # TODO
                        priority = TaskPriority.MEDIUM

                    rel_path = str(file_path.relative_to(self.root_dir))
                    title = f"{tag}: {comment}" if comment else tag

                    tasks.append(
                        TaskCandidate(
                            source="todo",
                            title=title,
                            description=f"{rel_path}:{line_num}: {line.strip()}",
                            file_path=rel_path,
                            line_number=line_num,
                            priority=priority,
                        )
                    )

        return tasks

    def scan_github_issues(self) -> list[TaskCandidate]:
        """GitHub Issueをスキャンする

        Returns:
            タスク候補のリスト
        """
        tasks: list[TaskCandidate] = []

        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "list",
                    "--state",
                    "open",
                    "--json",
                    "number,title,labels",
                    "--limit",
                    "50",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.root_dir),
            )
        except FileNotFoundError:
            return tasks
        except subprocess.TimeoutExpired:
            return tasks

        if result.returncode != 0:
            return tasks

        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            return tasks

        for issue in issues:
            number = issue.get("number", 0)
            title = issue.get("title", "")
            labels = issue.get("labels", [])
            label_names = [l.get("name", "") for l in labels]

            # 優先度判定
            if any(l in ("bug", "critical", "urgent", "security") for l in label_names):
                priority = TaskPriority.HIGH
            elif any(l in ("feature", "enhancement") for l in label_names):
                priority = TaskPriority.MEDIUM
            else:
                priority = TaskPriority.LOW

            label_str = f" [{', '.join(label_names)}]" if label_names else ""
            tasks.append(
                TaskCandidate(
                    source="github-issue",
                    title=f"#{number} {title}{label_str}",
                    description=f"https://github.com/issues/{number}",
                    priority=priority,
                )
            )

        return tasks

    def scan_progress_files(self) -> list[TaskCandidate]:
        """PROGRESS.md/PLAN.mdの未完了チェックボックスをスキャンする

        Returns:
            タスク候補のリスト
        """
        tasks: list[TaskCandidate] = []
        progress_files = ["PROGRESS.md", "PLAN.md", "TODO.md"]
        unchecked_pattern = re.compile(r"^-\s*\[\s*\]\s*(.*)")

        for filename in progress_files:
            file_path = self.root_dir / filename
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text()
            except (OSError, PermissionError):
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                match = unchecked_pattern.match(line.strip())
                if match:
                    item = match.group(1).strip()
                    if item:
                        tasks.append(
                            TaskCandidate(
                                source="progress",
                                title=item,
                                description=f"{filename}:{line_num}",
                                file_path=filename,
                                line_number=line_num,
                                priority=TaskPriority.MEDIUM,
                            )
                        )

        return tasks

    def _iter_text_files(self):
        """テキストファイルをイテレートする（除外ディレクトリをスキップ）"""
        for path in self.root_dir.rglob("*"):
            if not path.is_file():
                continue

            # 除外ディレクトリチェック
            parts = path.relative_to(self.root_dir).parts
            if any(part in _EXCLUDE_DIRS for part in parts):
                continue

            # テストファイル除外
            if self.exclude_tests and self._is_test_file(path):
                continue

            # 拡張子チェック
            if path.suffix.lower() not in _TEXT_EXTENSIONS:
                continue

            yield path

    def _is_test_file(self, path: Path) -> bool:
        """テストファイルかどうかを判定する"""
        rel_parts = path.relative_to(self.root_dir).parts

        # テストディレクトリ内のファイル
        test_dirs = {"tests", "test", "__tests__", "spec", "specs"}
        if any(part in test_dirs for part in rel_parts):
            return True

        # テストファイル名パターン
        name = path.name
        if name.startswith("test_") or name.endswith("_test.py"):
            return True
        if name.startswith("test.") or name.endswith(".test.js") or name.endswith(".test.ts"):
            return True
        if name.endswith(".spec.js") or name.endswith(".spec.ts"):
            return True

        return False
