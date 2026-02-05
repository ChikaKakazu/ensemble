# インフラ整合性チェック（必須）

セッション名・ウィンドウ名・ペイン構造を変更する際は、以下の5ファイル全てを確認せよ:

## チェックリスト
| ファイル | 確認項目 |
|---------|---------|
| src/ensemble/commands/_launch_impl.py | セッション名、ペイン分割、panes.env出力 |
| src/ensemble/templates/scripts/launch.sh | 同上（シェル版） |
| src/ensemble/templates/scripts/pane-setup.sh | セッション参照、ウィンドウ名 |
| .claude/agents/conductor.md | ASCII図、セッション説明 |
| src/ensemble/templates/agents/conductor.md | 同上（テンプレート版） |

## 変更時の手順
1. 上記5ファイルを全てgrepで検索
2. 変更対象を特定
3. 全ファイルを同時に修正（不整合防止）
4. テスト実行で動作確認

## 過去の教訓（2025-02-04）
セッション名変更（ensemble:workers → ensemble-workers:main）で
pane-setup.shの参照が不一致となり、循環依存が発生。
Criticalエスカレーションとなり、手動対応が必要になった。

---

# インフラリファレンス

## tmuxセッション/ウィンドウ命名規則

| 項目 | 名前 | 説明 |
|------|------|------|
| セッション1 | `ensemble-conductor` | Conductor + Dashboard |
| セッション2 | `ensemble-workers` | Dispatch + Workers |
| ウィンドウ名 | `main` | 両セッションとも |

## Ensembleエージェント一覧

| エージェント | モデル | 役割 |
|-------------|--------|------|
| **Conductor** | opus | 指揮者。計画立案・タスク分解・判断・委譲を行う。コードは書かない。 |
| **Dispatch** | sonnet | 伝達役。タスク配信・ACK確認・完了報告集約を行う。判断はしない。 |
| **Worker** | sonnet | 実行者。コード実装・テスト・修正を行う。完了後に報告。 |
| **Reviewer** | sonnet | レビュアー。コードレビュー・品質チェックを行う。 |
| **Security-Reviewer** | sonnet | セキュリティ専門レビュアー。脆弱性チェックを行う。 |
| **Integrator** | sonnet | 統合担当。worktreeマージ・コンフリクト解決を行う。 |
| **Learner** | sonnet | 学習担当。タスク完了後の自己改善・CLAUDE.md更新を行う。 |

## ペインレイアウト

**Session 1: ensemble-conductor**
```
+------------------+------------------+
|   Conductor      |   dashboard      |
|   (claude/opus)  |   (less +F)      |
|   60%            |   40%            |
+------------------+------------------+
```

**Session 2: ensemble-workers**
```
+------------------+------------------+
|   dispatch       |   worker-1       |
|   (claude/sonnet)|   (claude/sonnet)|
|                  +------------------+
|                  |   worker-2       |
|   60%            |   40%            |
+------------------+------------------+
```

## ペインID環境変数（.ensemble/panes.env）

```bash
# セッション名
CONDUCTOR_SESSION=ensemble-conductor
WORKERS_SESSION=ensemble-workers

# ペインID（tmux send-keys -t で使用）
CONDUCTOR_PANE=%0      # Conductorペイン
DASHBOARD_PANE=%1      # ダッシュボードペイン
DISPATCH_PANE=%2       # Dispatchペイン
WORKER_AREA_PANE=%3    # ワーカーエリア（初期）
WORKER_1_PANE=%3       # Worker-1（起動後）
WORKER_2_PANE=%4       # Worker-2（起動後）
WORKER_COUNT=2         # 現在のワーカー数
```

## ペイン操作の正しい方法

```bash
# ✅ 正しい: panes.envを読み込んでペインIDを使用
source .ensemble/panes.env
tmux send-keys -t "$CONDUCTOR_PANE" 'メッセージ'
tmux send-keys -t "$CONDUCTOR_PANE" Enter

# ❌ 間違い: ペイン番号を直接使用（設定依存で動かない）
tmux send-keys -t ensemble-conductor:main.0 'メッセージ' Enter
```

## インフラ状態確認コマンド

```bash
# セッション一覧
tmux list-sessions

# ペイン一覧（全セッション）
tmux list-panes -a -F '#{session_name}:#{window_name}.#{pane_id} #{pane_title}'

# 特定セッションのペイン
tmux list-panes -t ensemble-conductor -F '#{pane_id} #{pane_current_command}'
tmux list-panes -t ensemble-workers -F '#{pane_id} #{pane_current_command}'
```
