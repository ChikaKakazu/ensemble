"""
Bloom's Taxonomy的タスク分類

タスクの認知レベルに基づいてモデルを自動選択する。
6レベルのBloom's Taxonomy（Remember/Understand/Apply/Analyze/Evaluate/Create）を使用。
"""

from __future__ import annotations

from enum import IntEnum


class BloomLevel(IntEnum):
    """Bloom's Taxonomyの認知レベル"""

    REMEMBER = 1  # 事実の想起、コピー、リスト
    UNDERSTAND = 2  # 説明、要約、言い換え
    APPLY = 3  # 手順の実行、実装
    ANALYZE = 4  # 比較、調査、分析
    EVALUATE = 5  # 判断、批評、レビュー
    CREATE = 6  # 設計、新しい解決策、アーキテクチャ


# 各レベルのキーワード辞書（日本語・英語両対応）
BLOOM_KEYWORDS = {
    BloomLevel.REMEMBER: [
        # 日本語
        "コピー",
        "リスト",
        "列挙",
        "ファイルをリスト",
        "一覧",
        "表示",
        "確認",
        "参照",
        # 英語
        "copy",
        "list",
        "enumerate",
        "show",
        "display",
        "recall",
        "remember",
    ],
    BloomLevel.UNDERSTAND: [
        # 日本語
        "説明",
        "要約",
        "言い換え",
        "解釈",
        "理解",
        "この関数を説明",
        # 英語
        "explain",
        "summarize",
        "interpret",
        "understand",
        "describe",
        "paraphrase",
    ],
    BloomLevel.APPLY: [
        # 日本語
        "実装",
        "適用",
        "テスト",
        "使用",
        "実行",
        "APIエンドポイントを実装",
        "作成",
        "追加",
        # 英語
        "implement",
        "apply",
        "test",
        "use",
        "execute",
        "create",
        "add",
    ],
    BloomLevel.ANALYZE: [
        # 日本語
        "比較",
        "調査",
        "分析",
        "検証",
        "パフォーマンスを分析",
        "調べる",
        # 英語
        "analyze",
        "compare",
        "investigate",
        "examine",
        "research",
    ],
    BloomLevel.EVALUATE: [
        # 日本語
        "判断",
        "評価",
        "レビュー",
        "批評",
        "コードをレビュー",
        "検討",
        # 英語
        "evaluate",
        "judge",
        "review",
        "critique",
        "assess",
    ],
    BloomLevel.CREATE: [
        # 日本語
        "設計",
        "構築",
        "アーキテクチャ",
        "新しい解決策",
        "認証システムを設計",
        "システムを設計",
        "デザイン",
        # 英語
        "design",
        "architect",
        "build",
        "construct",
        "new solution",
        "create architecture",
    ],
}


def classify_task(instruction: str) -> BloomLevel:
    """
    タスク指示文からBloomレベルを判定

    高レベル優先で判定（CREATE > EVALUATE > ... > REMEMBER）。
    複数のレベルのキーワードが含まれる場合は、最も高いレベルを返す。

    Args:
        instruction: タスク指示文

    Returns:
        Bloomレベル（デフォルトは APPLY）
    """
    instruction_lower = instruction.lower()

    # 高レベル優先でチェック（CREATE → REMEMBER の順）
    for level in sorted(BLOOM_KEYWORDS.keys(), reverse=True):
        keywords = BLOOM_KEYWORDS[level]
        for keyword in keywords:
            if keyword.lower() in instruction_lower:
                return level

    # デフォルトは APPLY（最も一般的なタスク）
    return BloomLevel.APPLY


def select_model(level: BloomLevel) -> str:
    """
    BloomレベルからClaude Codeモデルを選択

    L1-L3（Remember/Understand/Apply）: Sonnet
    L4-L6（Analyze/Evaluate/Create）: Opus

    Args:
        level: Bloomレベル

    Returns:
        モデル名（"sonnet" または "opus"）
    """
    if level <= BloomLevel.APPLY:
        return "sonnet"  # L1-L3: Sonnet
    else:
        return "opus"  # L4-L6: Opus


def get_level_description(level: BloomLevel) -> str:
    """
    UI向けの説明文を返す

    Args:
        level: Bloomレベル

    Returns:
        説明文（例: "L1 - Remember: 事実の想起、コピー、リスト"）
    """
    descriptions = {
        BloomLevel.REMEMBER: "L1 - Remember: 事実の想起、コピー、リスト",
        BloomLevel.UNDERSTAND: "L2 - Understand: 説明、要約、言い換え",
        BloomLevel.APPLY: "L3 - Apply: 手順の実行、実装",
        BloomLevel.ANALYZE: "L4 - Analyze: 比較、調査、分析",
        BloomLevel.EVALUATE: "L5 - Evaluate: 判断、批評、レビュー",
        BloomLevel.CREATE: "L6 - Create: 設計、新しい解決策、アーキテクチャ",
    }
    return descriptions.get(level, "Unknown level")


def classify_and_recommend(instruction: str) -> dict[str, str | int]:
    """
    分類と推奨を一度に返す便利関数

    Args:
        instruction: タスク指示文

    Returns:
        辞書形式の結果:
        {
            "level": BloomLevel,
            "level_name": str,
            "level_description": str,
            "recommended_model": str,
        }
    """
    level = classify_task(instruction)
    model = select_model(level)
    description = get_level_description(level)

    return {
        "level": int(level),
        "level_name": level.name,
        "level_description": description,
        "recommended_model": model,
    }
