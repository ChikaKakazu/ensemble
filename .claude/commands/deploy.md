---
description: |
  Ensembleをデプロイする。バージョンアップ、コミット、
  deploy/productionへのマージ、PyPIへのpublishを自動実行。
---

Ensembleのデプロイを実行します。

## 引数

$ARGUMENTS

（引数なし: パッチバージョン +1、`major`/`minor`/`patch` で指定可能）

## 実行手順

### Step 1: 事前確認

```bash
# mainブランチにいることを確認
git branch --show-current

# 未コミットの変更がないことを確認
git status --short
```

**中断条件**:
- mainブランチでない場合 → エラー終了
- 未コミットの変更がある場合 → ユーザーに確認

### Step 2: 現在のバージョン取得

```bash
# pyproject.tomlからバージョン取得
grep -E '^version = ' pyproject.toml
```

### Step 3: 新バージョン計算

- 引数なし or `patch`: x.y.z → x.y.(z+1)
- `minor`: x.y.z → x.(y+1).0
- `major`: x.y.z → (x+1).0.0

### Step 4: バージョン更新

以下の2ファイルを更新:
1. `pyproject.toml` の `version = "x.y.z"`
2. `src/ensemble/__init__.py` の `__version__ = "x.y.z"`

### Step 5: コミット＆プッシュ

```bash
git add pyproject.toml src/ensemble/__init__.py
git commit -m "chore: bump version to {new_version}"
git push
```

### Step 6: deploy/productionにマージ

```bash
# deploy/productionブランチに切り替え
git checkout deploy/production

# mainをマージ
git merge main --no-edit

# プッシュ（CIがPyPIにpublish）
git push

# mainブランチに戻る
git checkout main
```

### Step 7: 完了報告

```
✅ デプロイ完了

バージョン: {old_version} → {new_version}
PyPI: https://pypi.org/project/ensemble-ai/{new_version}/

※ CIのpublishが完了するまで1-2分かかります
```

## 注意事項

- 必ず最後にmainブランチに戻ること
- CIが失敗した場合はGitHub Actionsを確認
- 各ステップの完了を確認してから次に進む（アトミック操作）
