# 学習済みルール

このファイルはlearner agentが自動追記するセクションです。

<!-- learner agentが自動追記する際は、適切なカテゴリの末尾に追記すること -->

## 通信・インフラ

### 2025-02-08: shellスクリプトでのsource上書き防止
- `source`で外部ファイルを読み込む前に、スクリプト引数やローカル変数を別名で退避すること
- panes.envには前回実行時の状態（WORKER_COUNT等）が含まれるため、意図しない上書きが発生する
- パターン: `REQUESTED_VAR="${1:-default}"` → source → `VAR="$REQUESTED_VAR"`

### 2025-02-08: 完了待機中のエスカレーション自動検知
- Conductorの完了待機ループでは `completion-summary.yaml` だけでなく `escalation-*.yaml` も同時監視すること
- エスカレーション検知後: YAML読み込み → 修正 → Dispatch再開指示 → YAML削除 → ポーリング再開
- 完了のみ監視するとエスカレーション通知を見逃し、ユーザーの手動介入が必要になる

### 2025-02-04: 通信プロトコルv2.0導入
- Worker→Dispatch→Conductor の3段階通知チェーン実装
- ポーリングフォールバック追加
- 検知時間を3-5分から即座に短縮

### 2025-02-04: インフラ整合性チェック追加
- セッション名変更時の5ファイルチェックリスト運用開始
- 循環依存の早期検出ルール追加

## ワークフロー

### 2025-02-05: 構造変更時の影響調査プロトコル
- ファイルの分割・移動・リネーム前に必ず `grep` で参照箇所を調査
- 影響を受けるファイル一覧を作成してから変更を開始
- テンプレート（src/ensemble/templates/）と実ファイル（.claude/）の両方を確認

### 2025-02-08: エスカレーション対応フロー
- Dispatchがエスカレーション報告（queue/reports/escalation-*.yaml）を作成
- Conductorが完了待機ループ内で自動検知（手動介入不要）
- 修正実施後、Dispatchに再開指示を送信
- 修正はインフラ整合性チェック（5ファイル）に従うこと

### 2025-02-08: 新コマンド追加時のドキュメント同期（再確認）
- /rpi-research, /rpi-plan, /rpi-implementの追加時にREADME.md, USAGE.md, docs/ARCHITECTURE.mdの更新が漏れた
- ドキュメント同期は機能実装タスクに含めてWorkerに指示すべき（後追い更新は漏れる）
- 既存ルール（2025-02-08: 機能追加時のドキュメント同期ルール）の徹底

### 2026-02-07: Worker数の動的決定
- タスク数に応じてworker_count: 2〜4を動的に決定する
- Claude Max 5並列制限: Conductor用1 + Worker用最大4
- タスク数 ≤ 2 → worker_count: 2, タスク数3 → 3, タスク数4以上 → 4

### 2025-02-08: 機能追加時のドキュメント同期ルール
- 新コマンド/機能を追加した際は、以下3ファイルを必ず同時更新すること:
  1. USAGE.md（日本語、詳細な使用例）
  2. README.md（英語、コマンド一覧テーブル）
  3. docs/ARCHITECTURE.md（日本語、技術詳細）
- 特にCLIコマンド一覧とSkillコマンド一覧のテーブルを確認

## コード品質

（該当ルールなし）

## ツール・環境

### 2025-02-05: Workerハング対策
- Worker実行中、5分以上進捗がない場合はハングの可能性
- `tmux capture-pane -t %{pane_id} -p | tail -20` で状態確認
- Photosynthesizing/Transfiguring状態が継続していたらEscapeキーで割り込み

### 2026-02-07: ローカルスクリプトとテンプレート同期
- `ensemble upgrade` 実行時、scripts/ 配下のローカルファイルもテンプレートと同期確認が必要
- 特にpane-setup.sh: セッション名変数（CONDUCTOR_SESSION/WORKERS_SESSION）を使用すべき
- テンプレート版（src/ensemble/templates/scripts/）が正、ローカル版（scripts/）が従の原則

### 2025-02-08: ダッシュボード監視にはwatchを使用
- `less +F` はファイル末尾への追記のみ検知。全体上書き（truncate+write）は反映されない
- `watch -n 5 -t cat <file>` で5秒間隔の全体再読込を使用すること
- ファイル監視ツール選択時は更新パターン（追記 vs 上書き）を確認すること
