# デプロイ手順

「デプロイして」と言われたら以下を実行:

## 1. バージョンアップ（mainブランチで）

以下の2ファイルのバージョンを更新（パッチバージョンを+1）:
- `pyproject.toml` の `version = "x.y.z"`
- `src/ensemble/__init__.py` の `__version__ = "x.y.z"`

```bash
# コミット＆プッシュ
git add pyproject.toml src/ensemble/__init__.py
git commit -m "chore: bump version to x.y.z"
git push
```

## 2. deploy/productionにマージ

```bash
# deploy/productionブランチに切り替え
git checkout deploy/production

# mainをマージ
git merge main

# プッシュ（CIがPyPIにpublish）
git push

# mainブランチに戻る
git checkout main
```

**注意**: 必ず最後にmainブランチに戻ること
