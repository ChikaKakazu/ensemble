---
description: |
  GitHubのIssueを取得し、/goコマンドで実装を開始する。
  Issue一覧から選択するか、番号を直接指定できる。
  mainブランチから作業ブランチを作成し、完了後はPR作成を確認する。

  使用例:
    /go-issue              - Issue一覧から選択
    /go-issue 123          - Issue #123を直接指定
    /go-issue --url <URL>  - URLでIssueを指定
---

以下のワークフローでIssueベースの開発を行います。

## 入力

$ARGUMENTS

## ワークフロー

### Step 1: Issue取得

1. **引数の解析**:
   - 引数なし → Issue一覧を取得して表示
   - 番号あり → その番号のIssueを直接取得
   - `--url` → URLからIssueを取得

2. **Issue一覧の場合** (`gh issue list --json number,title,body,url,state,labels`):
   - 0件: 「オープンなIssueがありません」で終了
   - 1件: 確認後に自動選択
   - 2件以上: 番号付きリストで表示し、ユーザーに選択させる

   表示例:
   ```
   オープンなIssue一覧:

   1. #42 [bug] ログイン時にエラーが発生する
   2. #38 [feature] ダークモード対応
   3. #35 [docs] READMEの更新

   実装するIssueの番号を入力してください (1-3):
   ```

3. **Issue詳細の確認**:
   - タイトル、本文、ラベルを表示
   - 「このIssueで作業を開始しますか？」と確認

### Step 2: ブランチ作成

1. **現在の状態確認**:
   ```bash
   git status --porcelain
   ```
   - 未コミットの変更がある場合は警告し、続行するか確認

2. **mainブランチに移動して最新化**:
   ```bash
   git checkout main
   git pull origin main
   ```

3. **作業ブランチを作成**:
   ```bash
   git checkout -b issue/<番号>-<slug>
   ```
   例: `issue/42-fix-login-bug`

4. **作成完了を報告**:
   ```
   ブランチ 'issue/42-fix-login-bug' を作成しました。
   ```

### Step 3: /goコマンドに委譲

以下の形式でタスクを構築し、/goコマンドの処理を実行する:

```
## Issue #<番号>: <タイトル>

### 説明
<Issue本文>

### ラベル
<ラベル一覧>

### 完了条件
- このIssueで要求された機能/修正を実装する
- テストを追加する（必要に応じて）
- コードレビューに通るコードを書く
```

**注意**: `/go`コマンドのskillを呼び出すのではなく、このコマンド内でConductorとして計画・実行を行う。

### Step 4: PR作成確認

実装完了後:

1. **変更のサマリーを表示**:
   ```bash
   git diff main --stat
   ```

2. **PR作成の確認**:
   ```
   実装が完了しました。Pull Requestを作成しますか？

   [Y] 作成する
   [N] 後で作成する
   [E] コミットメッセージを編集してから作成
   ```

3. **PR作成** (Yの場合):
   ```bash
   gh pr create --title "Fix: <Issueタイトル>" --body "Closes #<番号>

   ## 変更内容
   <自動生成されたサマリー>

   ## テスト
   - [ ] 単体テスト追加
   - [ ] 手動テスト実施
   "
   ```

4. **PR URLを表示**:
   ```
   Pull Request を作成しました:
   https://github.com/owner/repo/pull/XX
   ```

## プロバイダー対応

現在対応しているプロバイダー:
- **GitHub** (`gh` CLI): 完全対応
- **GitLab** (`glab` CLI): 今後対応予定

プロバイダーは自動検出する:
1. `gh` コマンドが利用可能 → GitHub
2. `glab` コマンドが利用可能 → GitLab
3. どちらも利用不可 → エラー

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| `gh`/`glab` 未インストール | インストール方法を案内して終了 |
| リポジトリ外で実行 | 「Gitリポジトリで実行してください」 |
| オープンなIssueなし | 「オープンなIssueがありません」で終了 |
| 指定番号のIssueなし | 「Issue #XX は見つかりませんでした」 |
| ブランチ作成失敗 | エラー詳細を表示、手動での対応を案内 |
| PR作成失敗 | エラー詳細を表示、`gh pr create`コマンドを案内 |

## 注意事項

- Conductorは自分でコードを書かず、適切なエージェントに委譲する
- Issue本文が曖昧な場合は、ユーザーに追加情報を求める
- 大規模なIssueはサブタスクに分解することを提案する
