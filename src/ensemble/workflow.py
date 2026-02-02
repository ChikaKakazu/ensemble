"""
ワークフロー集約ロジックユーティリティ

注意: このモジュールは状態遷移を行わない。
状態遷移はClaude（Conductor）が担当する。
このモジュールは集約ロジック（all/any判定）のみを提供する。
"""

import re
from pathlib import Path
from typing import Any

import yaml


# 重大度の優先順位（ソート用）
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def aggregate_results(results: list[str], rule: str) -> bool:
    """
    並列レビュー結果を集約する

    Args:
        results: 各レビューアの結果 ["approved", "needs_fix", ...]
        rule: 集約ルール "all(\"approved\")" or "any(\"needs_fix\")"

    Returns:
        ルールが満たされればTrue

    Example:
        >>> aggregate_results(["approved", "approved"], 'all("approved")')
        True
        >>> aggregate_results(["approved", "needs_fix"], 'any("needs_fix")')
        True
    """
    # ルールをパース（"all('xxx')" or 'all("xxx")' 形式に対応）
    match = re.match(r'(all|any)\(["\']([^"\']+)["\']\)', rule)
    if not match:
        return False

    operator, target = match.groups()

    if operator == "all":
        return all(r == target for r in results)
    elif operator == "any":
        return any(r == target for r in results)

    return False


def parse_review_results(reports_dir: str) -> dict[str, str]:
    """
    queue/reports/ からレビュー結果を収集する

    Args:
        reports_dir: レポートディレクトリのパス

    Returns:
        {"arch-review": "approved", "security-review": "needs_fix"}
    """
    results: dict[str, str] = {}
    reports_path = Path(reports_dir)

    if not reports_path.exists():
        return results

    for report_file in reports_path.glob("*.yaml"):
        try:
            content = yaml.safe_load(report_file.read_text())
            if content and isinstance(content, dict) and "result" in content:
                # ファイル名からレビュー名を抽出（例: arch-review-task-123.yaml → arch-review）
                filename = report_file.stem  # 拡張子なし
                # task-id部分を除去
                parts = filename.rsplit("-", 2)
                if len(parts) >= 3:
                    review_name = "-".join(parts[:-2])  # arch-review
                else:
                    review_name = filename
                results[review_name] = content["result"]
        except yaml.YAMLError:
            # 不正なYAMLはスキップ
            continue

    return results


def merge_findings(reports_dir: str) -> list[dict[str, Any]]:
    """
    複数のレポートからfindingsをマージして重大度順にソートする

    Args:
        reports_dir: レポートディレクトリのパス

    Returns:
        マージされたfindingsのリスト（重大度の高い順）
    """
    all_findings: list[dict[str, Any]] = []
    reports_path = Path(reports_dir)

    if not reports_path.exists():
        return all_findings

    for report_file in reports_path.glob("*.yaml"):
        try:
            content = yaml.safe_load(report_file.read_text())
            if content and isinstance(content, dict):
                findings = content.get("findings", [])
                # ファイル名からソース情報を取得
                filename = report_file.stem
                parts = filename.rsplit("-", 2)
                if len(parts) >= 3:
                    source = "-".join(parts[:-2])
                else:
                    source = filename

                for finding in findings:
                    if isinstance(finding, dict):
                        finding["source"] = source
                        all_findings.append(finding)
        except yaml.YAMLError:
            continue

    # 重大度でソート（critical > high > medium > low）
    all_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.get("severity", "low"), 999))

    return all_findings
