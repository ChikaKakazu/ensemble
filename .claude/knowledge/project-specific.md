# Project-Specific Knowledge

## Ensemble アーキテクチャ

### コンポーネント構成

```
Conductor (opus)     - 計画・判断・委譲
    ↓
Dispatch (sonnet)    - タスク配信・ACK確認・完了報告集約
    ↓
Workers (sonnet×N)   - コード実装・テスト実行
    ↓
Reviewers (sonnet)   - コードレビュー・品質チェック
    ↓
Integrator (sonnet)  - Worktreeマージ・統合テスト
    ↓
Learner (sonnet)     - 自己改善・MEMORY.md更新
```

### 通信プロトコル

- **ファイルベースキュー**: queue/ ディレクトリでタスク管理
- **send-keys通知**: tmux send-keysで即座に通知（プライマリ）
- **ポーリングフォールバック**: 通知失敗時はポーリングで検知

### ディレクトリ構造

```
.ensemble/
├── panes.env           # ペインID環境変数
├── logs/               # NDJSONログ
queue/
├── tasks/              # 保留中タスク
├── processing/         # 処理中タスク
├── reports/            # 完了報告
├── ack/                # ACK確認
├── reviews/            # レビュー結果
└── conductor/          # Conductor指示
```

### 実行パターン

- **パターンA**: subagent直接（ファイル数 ≤ 3）
- **パターンB**: tmux並列（ファイル数 4〜10）
- **パターンC**: worktree分離（ファイル数 > 10）
- **モードT**: Agent Teams（調査・レビュー専用）

### ワークフロー

- **simple**: 軽量（テスト・レビューなし）
- **default**: 標準（実装 + テスト）
- **heavy**: 重量級（実装 + テスト + レビュー + 改善）

## 技術スタック

- **言語**: Python 3.11+
- **パッケージマネージャー**: uv
- **テスト**: pytest
- **tmux**: エージェント管理
- **Claude Code**: 各エージェントのランタイム

## コマンド規約

### Pythonスクリプト実行

```bash
uv run python script.py
uv run pytest tests/
```

### Git操作

```bash
git add .
git commit -m "message"
git push
```

### tmux操作

```bash
# ペインID使用（推奨）
source .ensemble/panes.env
tmux send-keys -t "$DISPATCH_PANE" 'メッセージ'
tmux send-keys -t "$DISPATCH_PANE" Enter

# ペイン番号使用（禁止）
tmux send-keys -t ensemble:main.0 'メッセージ' Enter  # NG
```

## プロジェクト固有の制約

- **CLAUDE.mdは150行以内**: 超過すると指示が守られにくくなる
- **曖昧語禁止**: 「多発」→「3回発生」、「一部」→「src/api/auth.py の 45-52行目」など具体的に記載
- **アトミック操作**: マルチステップワークフローでは各ステップの完了を確認してから次に進む
- **コンパクション復帰**: /clear後は必ずエージェント定義を読み直す
