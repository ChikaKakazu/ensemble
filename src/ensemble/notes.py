"""
学習ノート管理ユーティリティ

タスク実行の学習記録を管理する。
notes/{task-id}/以下にplan.md, decisions.md, lessons.md, skill-candidates.mdを配置。
"""

from datetime import datetime
from pathlib import Path
from typing import Any


def create_task_notes_dir(notes_base_dir: str, task_id: str) -> Path:
    """
    タスクノート用ディレクトリを作成する

    Args:
        notes_base_dir: ノートのベースディレクトリ
        task_id: タスクID

    Returns:
        作成されたディレクトリのPath
    """
    task_dir = Path(notes_base_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def write_lessons(
    task_dir: Path,
    task_id: str,
    lessons: dict[str, Any],
) -> None:
    """
    lessons.mdファイルを作成/更新する

    Args:
        task_dir: タスクディレクトリ
        task_id: タスクID
        lessons: 学習内容
            - successes: 成功したこと（リスト）
            - improvements: 改善点（リスト）
            - metrics: 数値（辞書）
    """
    content = f"""# タスク: {task_id}
## 日時: {datetime.now().isoformat()}

## 成功したこと
"""
    for success in lessons.get("successes", []):
        content += f"- {success}\n"

    content += "\n## 改善すべきこと\n"
    for improvement in lessons.get("improvements", []):
        if isinstance(improvement, dict):
            content += f"- [ ] {improvement.get('issue', '')}\n"
            content += f"  - 原因: {improvement.get('cause', '')}\n"
            content += f"  - 対策: {improvement.get('solution', '')}\n"
        else:
            content += f"- [ ] {improvement}\n"

    metrics = lessons.get("metrics", {})
    content += f"""
## 数値
- 修正回数: {metrics.get('fix_count', 0)}回
- テスト失敗回数: {metrics.get('test_failures', 0)}回
- レビュー指摘数: {metrics.get('review_issues', 0)}件
"""

    (task_dir / "lessons.md").write_text(content)


def write_skill_candidates(
    task_dir: Path,
    candidates: list[dict[str, Any]],
) -> None:
    """
    skill-candidates.mdファイルを作成する

    Args:
        task_dir: タスクディレクトリ
        candidates: スキル化候補のリスト
            - name: スキル名
            - purpose: 用途
            - occurrences: 発生回数
            - cost: 実装コスト（low/medium/high）
            - recommended: 推奨（True/False）
    """
    content = "# スキル化候補\n\n"

    if not candidates:
        content += "候補なし\n"
    else:
        for i, candidate in enumerate(candidates, 1):
            recommended = "YES" if candidate.get("recommended", False) else "NO"
            content += f"""## 候補{i}: {candidate.get('name', 'unknown')}
- 用途: {candidate.get('purpose', '')}
- 発生回数: {candidate.get('occurrences', 0)}回
- 実装コスト: {candidate.get('cost', 'unknown')}
- 推奨: {recommended}

"""

    (task_dir / "skill-candidates.md").write_text(content)


def write_decisions(
    task_dir: Path,
    task_id: str,
    decisions: list[dict[str, Any]],
    append: bool = False,
) -> None:
    """
    decisions.mdファイルを作成/更新する

    Args:
        task_dir: タスクディレクトリ
        task_id: タスクID
        decisions: 決定のリスト
            - timestamp: タイムスタンプ
            - context: 文脈
            - decision: 決定内容
            - rationale: 理由
        append: Trueの場合、既存ファイルに追記
    """
    decisions_file = task_dir / "decisions.md"

    if append and decisions_file.exists():
        content = decisions_file.read_text()
        content += "\n---\n\n"
    else:
        content = f"# 決定ログ: {task_id}\n\n"

    for decision in decisions:
        content += f"""## {decision.get('context', 'No context')}
- **日時**: {decision.get('timestamp', datetime.now().isoformat())}
- **決定**: {decision.get('decision', '')}
- **理由**: {decision.get('rationale', '')}

"""

    decisions_file.write_text(content)


def read_lessons(task_dir: Path) -> str | None:
    """
    lessons.mdの内容を読み込む

    Args:
        task_dir: タスクディレクトリ

    Returns:
        ファイル内容。存在しない場合はNone
    """
    lessons_file = task_dir / "lessons.md"
    if lessons_file.exists():
        return lessons_file.read_text()
    return None


def read_skill_candidates(task_dir: Path) -> str | None:
    """
    skill-candidates.mdの内容を読み込む

    Args:
        task_dir: タスクディレクトリ

    Returns:
        ファイル内容。存在しない場合はNone
    """
    skills_file = task_dir / "skill-candidates.md"
    if skills_file.exists():
        return skills_file.read_text()
    return None


def list_task_notes(notes_base_dir: str) -> list[str]:
    """
    全タスクディレクトリをリストする

    Args:
        notes_base_dir: ノートのベースディレクトリ

    Returns:
        タスクIDのリスト
    """
    notes_path = Path(notes_base_dir)
    if not notes_path.exists():
        return []

    return [d.name for d in notes_path.iterdir() if d.is_dir()]


def get_notes_summary(notes_base_dir: str) -> dict[str, dict[str, bool]]:
    """
    全ノートの要約を返す

    Args:
        notes_base_dir: ノートのベースディレクトリ

    Returns:
        {task_id: {has_lessons: bool, has_skill_candidates: bool, ...}}
    """
    notes_path = Path(notes_base_dir)
    if not notes_path.exists():
        return {}

    summary: dict[str, dict[str, bool]] = {}

    for task_dir in notes_path.iterdir():
        if not task_dir.is_dir():
            continue

        summary[task_dir.name] = {
            "has_lessons": (task_dir / "lessons.md").exists(),
            "has_skill_candidates": (task_dir / "skill-candidates.md").exists(),
            "has_decisions": (task_dir / "decisions.md").exists(),
            "has_plan": (task_dir / "plan.md").exists(),
        }

    return summary
