# worktree-manager

Git worktreeを使った並列開発を管理するスキル。

## 概要

複数のworktreeを作成・管理し、独立した機能開発を並列で行い、
最終的にメインブランチに統合する。

## コマンド

### worktree作成

```bash
.claude/scripts/worktree-create.sh <branch-name> [base-branch]
```

- `branch-name`: 作成するブランチ名（ensemble/接頭辞が自動付与）
- `base-branch`: ベースとなるブランチ（デフォルト: main）

例:
```bash
.claude/scripts/worktree-create.sh feature-auth main
# → ../ensemble-feature-auth ディレクトリにworktreeが作成される
# → ブランチ名: ensemble/feature-auth
```

### worktreeマージ

```bash
.claude/scripts/worktree-merge.sh <worktree-path>
```

- `worktree-path`: マージするworktreeのパス

例:
```bash
.claude/scripts/worktree-merge.sh ../ensemble-feature-auth
# → メインブランチにマージ
# → コンフリクトがあれば報告
```

### worktree一覧

```bash
git worktree list
```

### worktree削除

```bash
git worktree remove <worktree-path>
git branch -d <branch-name>
```

## ワークフロー

### 1. 並列開発の準備

```
Conductor → Dispatch:
  「3つの機能（auth, api, ui）を並列開発」

Dispatch:
  1. worktree-create.sh feature-auth
  2. worktree-create.sh feature-api
  3. worktree-create.sh feature-ui
  4. 各worktreeでClaude Codeを起動
```

### 2. 開発フェーズ

各worktreeで独立して開発:

```
ensemble-feature-auth/
  └── Coder: 認証機能を実装

ensemble-feature-api/
  └── Coder: API機能を実装

ensemble-feature-ui/
  └── Coder: UI機能を実装
```

### 3. 統合フェーズ

```
Integrator:
  1. worktree-merge.sh ../ensemble-feature-auth
  2. worktree-merge.sh ../ensemble-feature-api
  3. worktree-merge.sh ../ensemble-feature-ui
  4. コンフリクト解決
  5. 相互レビュー調整
```

## コンフリクト解決

### 自動解決可能

- インポート文の追加
- 独立した関数/クラスの追加
- 設定ファイルの独立した項目追加

### エスカレーション

- 同じコードブロックの競合
- 削除と修正の競合
- アーキテクチャ変更の競合

## Pythonユーティリティ

```python
from ensemble.worktree import (
    list_worktrees,
    detect_conflicts,
    ConflictReport,
    merge_worktree,
)

# worktree一覧
worktrees = list_worktrees()

# コンフリクト検出
report = detect_conflicts("../ensemble-feature-auth")

# マージ実行
result = merge_worktree("../ensemble-feature-auth", auto_resolve=True)
```

## ディレクトリ構造

```
project-root/
├── ensemble/                    # メインリポジトリ
│   ├── .git/
│   ├── .claude/scripts/
│   │   ├── worktree-create.sh
│   │   └── worktree-merge.sh
│   └── src/
│
├── ensemble-feature-auth/       # worktree 1
│   ├── .git → ../ensemble/.git
│   └── src/
│
├── ensemble-feature-api/        # worktree 2
│   ├── .git → ../ensemble/.git
│   └── src/
│
└── ensemble-feature-ui/         # worktree 3
    ├── .git → ../ensemble/.git
    └── src/
```

## 注意事項

1. **ブランチ命名**: `ensemble/` プレフィックスを使用
2. **worktree配置**: メインリポジトリと同じ親ディレクトリに配置
3. **クリーンアップ**: マージ後は必ずworktreeとブランチを削除
4. **同時編集**: 同じファイルの同時編集は避ける（コンフリクトの原因）
