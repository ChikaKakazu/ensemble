---
name: security-audit
description: Security auditing based on OWASP Top 10, injection prevention, authentication/authorization, XSS/CSRF protection, rate limiting, and security headers.
---

# Security Audit Skill

## 概要
OWASP Top 10、インジェクション防止、認証・認可のセキュリティ専門知識。

## OWASP Top 10（2021）

### 1. Broken Access Control
**問題**: ユーザーが権限外のリソースにアクセスできる

**対策**:
- 最小権限の原則
- 各リクエストで認可チェック
- IDベースのアクセス制御（ユーザーIDがリソース所有者か確認）

```python
def get_user_data(user_id: int, current_user: User):
    if current_user.id != user_id and not current_user.is_admin:
        raise PermissionError("Access denied")
    return db.get_user(user_id)
```

### 2. Cryptographic Failures
**問題**: 暗号化の不備（平文保存、弱い暗号化）

**対策**:
- パスワードはハッシュ化（bcrypt、Argon2）
- HTTPS必須
- 機密データは暗号化して保存

```python
from passlib.hash import bcrypt

# パスワードハッシュ化
hashed = bcrypt.hash("password")

# 検証
bcrypt.verify("password", hashed)  # True
```

### 3. Injection
**問題**: SQLインジェクション、コマンドインジェクション

**対策**:
- プリペアドステートメント使用
- ORM使用（SQLAlchemy、Django ORMなど）
- 入力バリデーション

```python
# ❌ 危険
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ 安全
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (email,))

# ✅ ORM使用
user = db.query(User).filter(User.email == email).first()
```

### 4. Insecure Design
**問題**: 設計段階でのセキュリティ考慮不足

**対策**:
- セキュアバイデザイン
- 脅威モデリング
- セキュリティレビュー

### 5. Security Misconfiguration
**問題**: デフォルト設定、不要な機能有効

**対策**:
- デフォルトパスワード変更
- 不要な機能無効化
- エラーメッセージで情報漏洩しない

```python
# ❌ 危険（本番環境でDEBUG=True）
DEBUG = True

# ✅ 安全
DEBUG = os.getenv("DEBUG", "False") == "True"
```

### 6. Vulnerable Components
**問題**: 古いライブラリの脆弱性

**対策**:
- 定期的なアップデート
- 依存関係スキャン（Dependabot、Snyk）
- セキュリティアドバイザリ監視

### 7. Identification and Authentication Failures
**問題**: 弱い認証、セッション管理の不備

**対策**:
- パスワードポリシー（長さ、複雑さ）
- 多要素認証（MFA）
- セッションタイムアウト
- ブルートフォース対策（レート制限）

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
```

### 8. Software and Data Integrity Failures
**問題**: コード・データの改ざん

**対策**:
- 署名検証
- CI/CDパイプラインのセキュリティ
- チェックサム検証

### 9. Security Logging and Monitoring Failures
**問題**: ログ・監視不足

**対策**:
- セキュリティイベントのログ記録
- 異常検知
- インシデント対応プラン

```python
import logging

logger = logging.getLogger(__name__)

def login(username: str, password: str):
    user = authenticate(username, password)
    if user:
        logger.info(f"Successful login: {username}")
        return user
    else:
        logger.warning(f"Failed login attempt: {username}")
        raise AuthenticationError()
```

### 10. Server-Side Request Forgery (SSRF)
**問題**: サーバーが攻撃者の指定したURLにアクセス

**対策**:
- URLホワイトリスト
- 内部IPアドレスへのアクセス禁止
- リダイレクト無効化

## XSS（Cross-Site Scripting）防止

```python
from markupsafe import escape

# ❌ 危険
html = f"<div>{user_input}</div>"

# ✅ 安全（エスケープ）
html = f"<div>{escape(user_input)}</div>"
```

## CSRF（Cross-Site Request Forgery）防止

```python
# FastAPI/Starlette例
from starlette.middleware.csrf import CSRFMiddleware

app.add_middleware(CSRFMiddleware, secret="your-secret")
```

## レート制限

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/login", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(username: str, password: str):
    # 1分間に5回まで
    pass
```

## セキュリティヘッダー

```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

## セキュリティチェックリスト

- [ ] 入力バリデーション（すべての入力）
- [ ] SQLインジェクション対策（プリペアドステートメント）
- [ ] XSS対策（エスケープ、CSP）
- [ ] CSRF対策（トークン検証）
- [ ] 認証・認可（各リクエストで確認）
- [ ] パスワードハッシュ化（bcrypt、Argon2）
- [ ] HTTPS必須
- [ ] セキュリティヘッダー設定
- [ ] レート制限
- [ ] ログ記録
- [ ] 依存関係の脆弱性スキャン
