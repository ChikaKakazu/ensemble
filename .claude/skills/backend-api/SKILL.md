---
name: backend-api
description: RESTful API design, implementation, error handling, pagination, security, and logging best practices for Python/FastAPI backends.
---

# Backend API Skill

## 概要
RESTful API設計・実装・エラーハンドリングの専門知識。

## RESTful API設計原則

### HTTPメソッド
- **GET**: リソース取得（冪等）
- **POST**: リソース作成
- **PUT**: リソース全体更新（冪等）
- **PATCH**: リソース部分更新
- **DELETE**: リソース削除（冪等）

### ステータスコード
- **200 OK**: 成功
- **201 Created**: リソース作成成功
- **204 No Content**: 成功（レスポンスボディなし）
- **400 Bad Request**: クライアントエラー（バリデーション失敗）
- **401 Unauthorized**: 認証失敗
- **403 Forbidden**: 権限不足
- **404 Not Found**: リソースが存在しない
- **500 Internal Server Error**: サーバーエラー

## レスポンス形式（推奨）

### 成功レスポンス
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "Example"
  },
  "meta": {
    "timestamp": "2026-02-11T00:00:00Z"
  }
}
```

### エラーレスポンス
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  }
}
```

## エラーハンドリング

### バリデーション
- リクエストボディを必ずバリデーション
- Pydantic、marshmallowなどのライブラリ活用

### 例外処理
```python
from fastapi import HTTPException

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## ページネーション

```python
@app.get("/items")
async def list_items(page: int = 1, limit: int = 20):
    offset = (page - 1) * limit
    items = db.query().offset(offset).limit(limit).all()
    total = db.query().count()

    return {
        "data": items,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }
```

## セキュリティ

- **入力サニタイズ**: SQLインジェクション、XSS防止
- **レート制限**: DDoS防止
- **認証・認可**: JWT、OAuth2など
- **CORS設定**: 適切なオリジン制限

## ロギング

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/items")
async def create_item(item: Item):
    logger.info(f"Creating item: {item.name}")
    try:
        result = db.create(item)
        logger.info(f"Item created: {result.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to create item: {e}")
        raise
```

## テスト

- **Unit Test**: 各エンドポイントのロジックテスト
- **Integration Test**: データベース連携テスト
- **E2E Test**: APIクライアント視点のテスト
