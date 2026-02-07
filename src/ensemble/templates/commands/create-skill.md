---
description: |
  プロジェクト固有のskillを効率的に作成するコマンド。
  既存skillを分析して最適なパターンを提案し、スケルトンを自動生成。

  使用例:
    /create-skill my-skill "説明文"
    /create-skill frontend-optimizer "Reactコンポーネントのパフォーマンス最適化"
---

プロジェクト固有のskillを作成します。

## 入力

$ARGUMENTS

## 引数解析

入力から以下を抽出してください:

```
/create-skill <skill名> <説明>
```

- **skill名**: ハイフン区切り (例: my-skill, frontend-optimizer)
- **説明**: 1行の説明文（引用符で囲む）

引数が不足している場合は対話形式で確認してください。

## 実行手順

### Step 1: 入力検証

1. skill名の形式チェック:
   - ハイフン区切り（アンダースコア不可）
   - 小文字のみ
   - 既存skillと重複しないか確認

```bash
# 既存skillの確認
ls ~/.claude/skills/
```

2. 既に同名のコマンドが存在する場合は警告:
   ```bash
   ls .claude/commands/ | grep "^${SKILL_NAME}.md$"
   ```

### Step 2: 既存skillの分析

プロジェクト内の既存skillとグローバルskillを分析:

1. パターンの検出:
   ```bash
   # プロジェクト固有skill
   ls .claude/skills/ 2>/dev/null || echo "なし"

   # グローバルskill
   ls ~/.claude/skills/
   ```

2. 説明文から類似skillを検索:
   - 技術スタック（React, Next.js, Go等）
   - 用途（テスト、デプロイ、レビュー等）
   - 推奨度を3段階評価（HIGH/MEDIUM/LOW）

3. ユーザーに提案:
   ```markdown
   ## 類似skillの検出結果

   以下のskillが参考になる可能性があります:

   | skill名 | 類似度 | 理由 |
   |---------|--------|------|
   | {skill-name} | HIGH | {理由} |
   ```

### Step 3: スケルトン生成

`.claude/commands/{skill名}.md` を以下の形式で生成:

```markdown
---
description: |
  {説明}

  使用例:
    /{skill名} 引数の例
---

{skill名}を実行します。

## 入力

$ARGUMENTS

## 実行手順

### Step 1: タスクの分析

1. {TODO: タスク内容を記載}

### Step 2: 実行

1. {TODO: 実装手順を記載}

### Step 3: 検証

1. {TODO: 検証手順を記載}

## 注意事項

- {TODO: 制約や前提条件を記載}
```

### Step 4: ユーザー確認

生成されたスケルトンを表示し、確認を求める:

```markdown
## 生成されたスケルトン

{生成内容のプレビュー}

---

以下のファイルを作成します:
- `.claude/commands/{skill名}.md`

作成してよろしいですか？ [y/N]
```

### Step 5: ファイル作成

ユーザーが承認した場合のみファイルを作成:

```bash
# 作成先ディレクトリの確認
mkdir -p .claude/commands

# ファイル作成
# （Step 3のスケルトンを書き込む）
```

### Step 6: 次のステップの案内

作成完了後、以下を表示:

```markdown
## 作成完了

✅ `.claude/commands/{skill名}.md` を作成しました

### 次のステップ

1. ファイルを編集してTODO部分を実装してください
2. 実装後、以下のコマンドでテスト:
   ```
   /{skill名} テスト引数
   ```

3. 他のプロジェクトでも使う場合:
   ```bash
   # グローバルskillとしてコピー
   cp .claude/commands/{skill名}.md ~/.claude/skills/
   ```

### 参考にすべき既存コマンド

{類似skillがある場合のみ}
- `.claude/commands/{類似skill}.md`
- `~/.claude/skills/{類似skill}.md`
```

## 注意事項

- **自動で上書きしない**: 必ずユーザー確認を取る
- **既存skillを分析**: パターンを提案して学習を促進
- **プロジェクト固有**: `.claude/commands/` に作成（グローバル化は後から）
- **TODO形式**: スケルトンはプレースホルダーで生成、実装はユーザーに委ねる

## トラブルシューティング

### skill名が不正な形式

```
エラー: skill名は小文字とハイフン（-）のみ使用できます
例: my-skill, frontend-optimizer
```

### 既存skillと重複

```
警告: 同名のskillが既に存在します
- .claude/commands/{skill名}.md

上書きしますか？ [y/N]
```
