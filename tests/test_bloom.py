"""Bloom's Taxonomy的タスク分類のテスト"""

import pytest

from ensemble.bloom import (
    BLOOM_KEYWORDS,
    BloomLevel,
    classify_and_recommend,
    classify_task,
    get_level_description,
    select_model,
)


class TestClassifyTask:
    """classify_task のテスト"""

    def test_classify_remember(self) -> None:
        """「ファイルをリスト」→ REMEMBER (L1)"""
        instruction = "ファイルをリストしてください"
        level = classify_task(instruction)
        assert level == BloomLevel.REMEMBER

    def test_classify_understand(self) -> None:
        """「この関数を説明」→ UNDERSTAND (L2)"""
        instruction = "この関数を説明してください"
        level = classify_task(instruction)
        assert level == BloomLevel.UNDERSTAND

    def test_classify_apply(self) -> None:
        """「APIエンドポイントを実装」→ APPLY (L3)"""
        instruction = "APIエンドポイントを実装してください"
        level = classify_task(instruction)
        assert level == BloomLevel.APPLY

    def test_classify_analyze(self) -> None:
        """「パフォーマンスを分析」→ ANALYZE (L4)"""
        instruction = "パフォーマンスを分析してください"
        level = classify_task(instruction)
        assert level == BloomLevel.ANALYZE

    def test_classify_evaluate(self) -> None:
        """「コードをレビュー」→ EVALUATE (L5)"""
        instruction = "コードをレビューしてください"
        level = classify_task(instruction)
        assert level == BloomLevel.EVALUATE

    def test_classify_create(self) -> None:
        """「認証システムを設計」→ CREATE (L6)"""
        instruction = "認証システムを設計してください"
        level = classify_task(instruction)
        assert level == BloomLevel.CREATE

    def test_classify_default(self) -> None:
        """「何かをする」→ APPLY (デフォルト)"""
        instruction = "何かをする"
        level = classify_task(instruction)
        assert level == BloomLevel.APPLY

    def test_classify_english(self) -> None:
        """\"design a new API\" → CREATE (英語対応)"""
        instruction = "design a new API"
        level = classify_task(instruction)
        assert level == BloomLevel.CREATE

    def test_classify_mixed(self) -> None:
        """「APIを設計して実装」→ CREATE (高レベル優先)"""
        instruction = "APIを設計して実装してください"
        level = classify_task(instruction)
        # 「設計」(L6) と「実装」(L3) の両方が含まれるが、高レベル優先で CREATE
        assert level == BloomLevel.CREATE


class TestSelectModel:
    """select_model のテスト"""

    def test_select_model_low(self) -> None:
        """L1-L3 → \"sonnet\""""
        assert select_model(BloomLevel.REMEMBER) == "sonnet"
        assert select_model(BloomLevel.UNDERSTAND) == "sonnet"
        assert select_model(BloomLevel.APPLY) == "sonnet"

    def test_select_model_high(self) -> None:
        """L4-L6 → \"opus\""""
        assert select_model(BloomLevel.ANALYZE) == "opus"
        assert select_model(BloomLevel.EVALUATE) == "opus"
        assert select_model(BloomLevel.CREATE) == "opus"


class TestGetLevelDescription:
    """get_level_description のテスト"""

    def test_get_level_description(self) -> None:
        """説明文にレベル番号と名前が含まれる"""
        description = get_level_description(BloomLevel.CREATE)
        assert "L6" in description
        assert "Create" in description

        description = get_level_description(BloomLevel.REMEMBER)
        assert "L1" in description
        assert "Remember" in description


class TestClassifyAndRecommend:
    """classify_and_recommend のテスト"""

    def test_classify_and_recommend(self) -> None:
        """便利関数の出力フォーマット確認"""
        instruction = "認証システムを設計してください"
        result = classify_and_recommend(instruction)

        # 必須フィールドが含まれることを確認
        assert "level" in result
        assert "level_name" in result
        assert "level_description" in result
        assert "recommended_model" in result

        # 値の妥当性を確認
        assert result["level"] == 6  # CREATE
        assert result["level_name"] == "CREATE"
        assert "L6" in result["level_description"]
        assert result["recommended_model"] == "opus"


class TestBloomLevelOrdering:
    """BloomLevel のテスト"""

    def test_bloom_level_ordering(self) -> None:
        """IntEnumの順序が正しい (L1 < L2 < ... < L6)"""
        assert BloomLevel.REMEMBER < BloomLevel.UNDERSTAND
        assert BloomLevel.UNDERSTAND < BloomLevel.APPLY
        assert BloomLevel.APPLY < BloomLevel.ANALYZE
        assert BloomLevel.ANALYZE < BloomLevel.EVALUATE
        assert BloomLevel.EVALUATE < BloomLevel.CREATE

        # 数値としても正しい
        assert BloomLevel.REMEMBER == 1
        assert BloomLevel.UNDERSTAND == 2
        assert BloomLevel.APPLY == 3
        assert BloomLevel.ANALYZE == 4
        assert BloomLevel.EVALUATE == 5
        assert BloomLevel.CREATE == 6


class TestBloomKeywords:
    """BLOOM_KEYWORDS のテスト"""

    def test_bloom_keywords_structure(self) -> None:
        """BLOOM_KEYWORDSの構造が正しい"""
        # 6レベル全てのキーワードが定義されている
        assert len(BLOOM_KEYWORDS) == 6

        for level in BloomLevel:
            assert level in BLOOM_KEYWORDS
            assert isinstance(BLOOM_KEYWORDS[level], list)
            assert len(BLOOM_KEYWORDS[level]) > 0

    def test_bloom_keywords_japanese_and_english(self) -> None:
        """日本語と英語のキーワードが両方含まれる"""
        # REMEMBER レベルに日本語と英語の両方が含まれることを確認
        remember_keywords = BLOOM_KEYWORDS[BloomLevel.REMEMBER]
        has_japanese = any(
            any(ord(c) > 127 for c in keyword) for keyword in remember_keywords
        )
        has_english = any(
            all(ord(c) < 128 for c in keyword) for keyword in remember_keywords
        )

        assert has_japanese, "日本語キーワードが含まれていない"
        assert has_english, "英語キーワードが含まれていない"
