---
name: testing
description: Test creation, execution, and coverage improvement with pytest. Covers TDD workflow, fixtures, parameterized tests, mocking, and unit/integration/E2E testing.
---

# Testing Skill

## 概要
テスト作成・実行・カバレッジ向上のための専門知識。

## TDD手順

1. **RED**: テストを先に書く（失敗することを確認）
2. **GREEN**: 最小限の実装でテストをパス
3. **REFACTOR**: コードを改善（テストは変更しない）

## pytest ベストプラクティス

### テストファイル命名
- `test_*.py` または `*_test.py`
- テスト関数は `test_` で始める

### Fixture活用
```python
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_example(sample_data):
    assert sample_data["key"] == "value"
```

### パラメータ化テスト
```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 3),
    (3, 4),
])
def test_increment(input, expected):
    assert input + 1 == expected
```

## カバレッジ目標

- **最低ライン**: 80%
- **推奨**: 90%以上
- **カバー必須**: エッジケース、エラーハンドリング

## テスト種類

### Unit Test
- 個別関数・メソッドのテスト
- モック・スタブで依存を切り離す

### Integration Test
- 複数コンポーネントの連携テスト
- データベース、API呼び出しを含む

### E2E Test
- ユーザー視点の全体テスト
- Playwright、Seleniumなど

## モック戦略

```python
from unittest.mock import Mock, patch

@patch('module.external_api_call')
def test_with_mock(mock_api):
    mock_api.return_value = {"status": "ok"}
    result = function_under_test()
    assert result == expected
```

## 注意事項
- テストは独立させる（他テストに依存しない）
- テストは高速に（遅いテストは別スイートに分離）
- テストコードも保守対象（リファクタ推奨）
