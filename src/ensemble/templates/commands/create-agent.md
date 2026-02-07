---
description: |
  プロジェクトの技術スタックに応じた専門agentを自動生成するコマンド。
  フロントエンド、バックエンド、DB/インフラ、テスト専門など、
  プロジェクトに最適なagentを対話形式で作成。
---

プロジェクト固有の専門agentを作成します。

## 入力

$ARGUMENTS

（引数なしで呼び出し可能。対話形式で必要な情報を確認します）

## 実行手順

### Step 1: プロジェクト技術スタックの自動分析

プロジェクトのディレクトリとファイルを分析し、技術スタックを特定:

```bash
# パッケージマネージャーファイルの検出
ls -1 package.json go.mod Cargo.toml requirements.txt pyproject.toml composer.json 2>/dev/null
```

#### 検出パターン

| ファイル | 技術スタック |
|---------|------------|
| package.json | Node.js, JavaScript/TypeScript |
| go.mod | Go |
| Cargo.toml | Rust |
| requirements.txt, pyproject.toml | Python |
| composer.json | PHP |

#### フレームワーク検出

```bash
# package.jsonの場合
grep -E "(react|next|vue|angular|svelte)" package.json

# go.modの場合
grep -E "(gin|echo|fiber|chi)" go.mod

# requirements.txtの場合
grep -E "(django|flask|fastapi)" requirements.txt
```

結果を表示:

```markdown
## プロジェクト技術スタック

検出されたスタック:
- 言語: {TypeScript, Go, Python 等}
- フレームワーク: {React, Next.js, Gin, FastAPI 等}
- DB: {PostgreSQL, MySQL, MongoDB 等}

---
```

### Step 2: agent種別の提案

技術スタックに基づいて、最適なagent種別を提案:

#### agent種別一覧

| 種別 | 役割 | 推奨技術スタック |
|------|------|-----------------|
| frontend-specialist | フロントエンド専門 | React, Vue, Angular, Svelte |
| backend-specialist | バックエンド専門 | Go, Python, Node.js API |
| fullstack-specialist | フルスタック | Next.js, Remix, SvelteKit |
| db-specialist | DB/インフラ専門 | PostgreSQL, MySQL, Redis |
| test-specialist | テスト専門 | Jest, Pytest, Go test |
| devops-specialist | CI/CD専門 | GitHub Actions, Docker |

提案を表示:

```markdown
## 推奨agent種別

プロジェクトの技術スタックから、以下のagentが推奨されます:

1. **{種別}** (推奨度: HIGH)
   - 理由: {理由}
   - 担当範囲: {範囲}

2. **{種別}** (推奨度: MEDIUM)
   - 理由: {理由}
   - 担当範囲: {範囲}

---

どのagentを作成しますか？ [1/2/その他]
```

### Step 3: agent名の決定

選択されたagent種別から、agent名を決定:

```
入力例: frontend-specialist
       ↓
agent名: frontend-specialist
ファイル名: .claude/agents/frontend-specialist.md
```

既に同名のagentが存在する場合は警告:

```bash
ls .claude/agents/ | grep "^${AGENT_NAME}.md$"
```

### Step 4: agentスケルトンの生成

選択されたagent種別に応じたスケルトンを生成:

#### フロントエンド専門agent (frontend-specialist)

```markdown
---
name: frontend-specialist
description: |
  フロントエンド専門agent。React/Vue/Angular等のUIコンポーネント、
  状態管理、パフォーマンス最適化を担当。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

あなたはフロントエンド専門のWorkerです。

## 担当範囲

- UIコンポーネントの実装
- 状態管理（Redux, Zustand, Pinia等）
- スタイリング（CSS, Tailwind, styled-components等）
- パフォーマンス最適化
- アクセシビリティ対応

## 技術スタック

{検出された技術スタックを記載}

## 実装ガイドライン

### コンポーネント設計
- 単一責任の原則を守る
- propsは最小限に
- 再利用性を考慮

### 状態管理
- ローカルステートとグローバルステートを適切に分離
- 必要以上にグローバル化しない

### スタイリング
- {プロジェクトのスタイリング方針を記載}

## 禁止事項

- バックエンドAPIの実装（backend-specialistの担当）
- DB操作（db-specialistの担当）
- 担当外のファイル編集
```

#### バックエンド専門agent (backend-specialist)

```markdown
---
name: backend-specialist
description: |
  バックエンド専門agent。API実装、ビジネスロジック、
  データ処理、認証/認可を担当。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

あなたはバックエンド専門のWorkerです。

## 担当範囲

- REST/GraphQL API実装
- ビジネスロジック
- 認証/認可
- データバリデーション
- エラーハンドリング

## 技術スタック

{検出された技術スタックを記載}

## 実装ガイドライン

### API設計
- RESTful原則に従う
- エラーレスポンスの一貫性
- バージョニング戦略

### セキュリティ
- 入力バリデーション必須
- SQLインジェクション対策
- 認証トークンの適切な管理

### パフォーマンス
- N+1クエリの回避
- キャッシング戦略
- 非同期処理の活用

## 禁止事項

- フロントエンドコンポーネントの実装（frontend-specialistの担当）
- DB スキーマ設計（db-specialistの担当）
- 担当外のファイル編集
```

#### DB/インフラ専門agent (db-specialist)

```markdown
---
name: db-specialist
description: |
  DB/インフラ専門agent。DBスキーマ設計、マイグレーション、
  クエリ最適化、インフラ構成を担当。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

あなたはDB/インフラ専門のWorkerです。

## 担当範囲

- DBスキーマ設計
- マイグレーション作成
- クエリ最適化
- インデックス設計
- インフラ構成（Docker, Kubernetes等）

## 技術スタック

{検出された技術スタックを記載}

## 実装ガイドライン

### スキーマ設計
- 正規化と非正規化のバランス
- 外部キー制約の適切な使用
- インデックス戦略

### マイグレーション
- ロールバック可能な設計
- ダウンタイムを最小化
- データ整合性の確保

### パフォーマンス
- スロークエリの特定と最適化
- インデックスの適切な配置
- コネクションプーリング

## 禁止事項

- ビジネスロジックの実装（backend-specialistの担当）
- UI実装（frontend-specialistの担当）
- 担当外のファイル編集
```

#### テスト専門agent (test-specialist)

```markdown
---
name: test-specialist
description: |
  テスト専門agent。単体テスト、統合テスト、E2Eテスト、
  テストカバレッジ向上を担当。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

あなたはテスト専門のWorkerです。

## 担当範囲

- 単体テスト作成
- 統合テスト作成
- E2Eテスト作成
- テストカバレッジ向上
- モック/スタブ作成

## 技術スタック

{検出された技術スタックを記載}

## 実装ガイドライン

### テストカバレッジ
- 最低80%を目標
- 重要なビジネスロジックは100%

### テスト設計
- Arrange-Act-Assert パターン
- テストの独立性を確保
- エッジケースを網羅

### モック戦略
- 外部依存は必ずモック
- DBは統合テストで実際に使用
- APIモックはレスポンス検証付き

## 禁止事項

- プロダクションコードの実装（他specialistの担当）
- テスト以外のファイル編集
```

### Step 5: ユーザー確認

生成されたagent定義を表示し、確認を求める:

```markdown
## 生成されたagent定義

{生成内容のプレビュー}

---

以下のファイルを作成します:
- `.claude/agents/{agent名}.md`

作成してよろしいですか？ [y/N]
```

### Step 6: ファイル作成

ユーザーが承認した場合のみファイルを作成:

```bash
# 作成先ディレクトリの確認
mkdir -p .claude/agents

# ファイル作成
# （Step 4のスケルトンを書き込む）
```

### Step 7: 活用方法の案内

作成完了後、Conductorでの活用方法を案内:

```markdown
## 作成完了

✅ `.claude/agents/{agent名}.md` を作成しました

### Conductorでの活用方法

専門agentをWorkerとして活用するには、以下の2つの方法があります:

#### 方法1: タスク分解時に専門agentを指定

Conductorがタスク分解する際、以下のように専門agentを指定:

```yaml
# queue/tasks/worker-1-task.yaml
id: task-001
instruction: "フロントエンド実装"
worker_agent: frontend-specialist  # ← 専門agentを指定
files:
  - "src/components/UserList.tsx"
```

#### 方法2: conductor.mdで専門化パターンを定義

`.claude/agents/conductor.md` に専門化ルールを追加:

```markdown
## Worker割り当て戦略

ファイルの種類に応じて専門agentを割り当てる:

| ファイルパターン | 割り当てagent |
|-----------------|--------------|
| src/components/**/*.tsx | frontend-specialist |
| src/api/**/*.go | backend-specialist |
| migrations/*.sql | db-specialist |
| **/*.test.* | test-specialist |
```

### 次のステップ

1. `.claude/agents/{agent名}.md` を編集してプロジェクト固有のガイドラインを追加
2. 実際のタスクで専門agentを試す:
   ```
   /go --parallel フロントエンドとバックエンドの同時実装
   ```

3. 効果を測定し、必要に応じて改善
```

## 注意事項

- **対話形式**: 技術スタックを自動検出し、最適なagentを提案
- **プロジェクト固有**: 検出された技術に特化したスケルトンを生成
- **段階的導入**: まず1つのagentから始め、効果を確認してから拡張
- **conductor.mdとの連携**: 専門agentの活用方法を明示

## トラブルシューティング

### 技術スタックが検出できない

```
警告: 技術スタックを自動検出できませんでした

手動で技術スタックを指定してください:
1. フロントエンド: React, Vue, Angular
2. バックエンド: Go, Python, Node.js
3. フルスタック: Next.js, Remix
4. その他
```

### 既存agentと役割が重複

```
警告: 既に類似のagentが存在します
- .claude/agents/{既存agent}.md

新しいagentを作成しますか？ [y/N]
（代わりに既存agentを編集することを推奨します）
```
