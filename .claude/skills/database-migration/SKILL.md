---
name: database-migration
description: Database schema changes, migration creation/execution/rollback with Alembic, Django, and Prisma. Covers zero-downtime migrations and safe schema change patterns.
---

# Database Migration Skill

## 概要
データベーススキーマ変更、マイグレーション作成・実行・ロールバックの専門知識。

## マイグレーション基本原則

### 1. 後方互換性を保つ
- 既存データが壊れないようにする
- 本番環境で段階的に適用

### 2. アトミック性
- 1マイグレーション = 1つの変更
- 失敗したらロールバック可能に

### 3. 順序性
- マイグレーションは順番に適用
- タイムスタンプまたはバージョン番号で管理

## マイグレーションツール

### Alembic（Python/SQLAlchemy）
```bash
# 新規マイグレーション作成
alembic revision -m "add users table"

# マイグレーション適用
alembic upgrade head

# ロールバック
alembic downgrade -1
```

### Django Migrations
```bash
# マイグレーション作成
python manage.py makemigrations

# マイグレーション適用
python manage.py migrate

# ロールバック
python manage.py migrate app_name 0001
```

### Prisma（Node.js/TypeScript）
```bash
# マイグレーション作成
npx prisma migrate dev --name add_users_table

# 本番環境適用
npx prisma migrate deploy
```

## 安全なスキーマ変更パターン

### テーブル追加
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### カラム追加（NULL許可）
```sql
-- 安全: 既存行はNULLになる
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- より安全: デフォルト値を設定
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
```

### カラム追加（NOT NULL）
```sql
-- 段階的アプローチ
-- Step 1: NULL許可で追加
ALTER TABLE users ADD COLUMN age INT;

-- Step 2: データ投入
UPDATE users SET age = 0 WHERE age IS NULL;

-- Step 3: NOT NULL制約追加
ALTER TABLE users ALTER COLUMN age SET NOT NULL;
```

### インデックス追加
```sql
-- 本番環境では CONCURRENTLY オプション（PostgreSQL）
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

### カラム削除（危険）
```sql
-- 本番環境では段階的に
-- Step 1: アプリケーションコードから参照を削除
-- Step 2: マイグレーション適用
ALTER TABLE users DROP COLUMN deprecated_field;
```

## データマイグレーション

### 既存データの変換
```python
# Alembic例
def upgrade():
    # スキーマ変更
    op.add_column('users', sa.Column('full_name', sa.String(255)))

    # データ移行
    op.execute("""
        UPDATE users
        SET full_name = first_name || ' ' || last_name
    """)

    # 古いカラム削除
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')

def downgrade():
    # ロールバック処理
    op.add_column('users', sa.Column('first_name', sa.String(100)))
    op.add_column('users', sa.Column('last_name', sa.String(100)))

    op.execute("""
        UPDATE users
        SET first_name = split_part(full_name, ' ', 1),
            last_name = split_part(full_name, ' ', 2)
    """)

    op.drop_column('users', 'full_name')
```

## 本番環境でのマイグレーション

### チェックリスト
- [ ] バックアップ取得
- [ ] ステージング環境でテスト
- [ ] ロールバックプラン準備
- [ ] ダウンタイム見積もり
- [ ] チーム通知

### ゼロダウンタイムマイグレーション
1. **Expand**: 新カラム追加（既存コードは動作継続）
2. **Migrate**: データ移行（バックグラウンド）
3. **Contract**: 古いカラム削除（新コードデプロイ後）

## テスト

```python
def test_migration_up_down():
    # マイグレーション適用
    alembic.upgrade('head')

    # スキーマ確認
    assert table_exists('users')
    assert column_exists('users', 'email')

    # ロールバック
    alembic.downgrade('-1')

    # 元に戻っていることを確認
    assert not table_exists('users')
```

## トラブルシューティング

### マイグレーション失敗時
1. ロールバック実行
2. 原因調査（ログ確認）
3. マイグレーション修正
4. 再実行

### 本番環境でマイグレーションが途中で止まった場合
1. 手動でロールバック
2. データ整合性確認
3. 必要に応じてデータ修復
