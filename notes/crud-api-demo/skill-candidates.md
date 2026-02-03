# スキル化候補: CRUD API Demo

## 候補1: fastapi-crud

### 概要
FastAPIでCRUDエンドポイントを生成するスキル

### 用途
- 新規エンティティのCRUD APIを素早く生成
- 統一されたコードスタイルを保証

### 入力
```
/fastapi-crud <entity-name> [--fields name:str,price:float,...]
```

### 出力
- `routes/create.py`
- `routes/read.py`
- `routes/update.py`
- `routes/delete.py`
- `models.py`（更新）

### 推奨度: **YES**
- 繰り返し発生する可能性が高い
- 定型化しやすい
- 品質の一貫性を保証できる

---

## 候補2: parallel-task-template

### 概要
並列タスクの指示書を生成するスキル

### 用途
- 類似タスクを複数ワーカーに分割する指示書を自動生成

### 入力
```
/parallel-task-template <task-type> --count N
```

### 推奨度: **MAYBE**
- 汎用化が難しい
- タスクの多様性が高い
