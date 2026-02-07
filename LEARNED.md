# 学習済みルール

このファイルはlearner agentが自動追記するセクションです。

## 2025-02-04: 通信プロトコルv2.0導入
- Worker→Dispatch→Conductor の3段階通知チェーン実装
- ポーリングフォールバック追加
- 検知時間を3-5分から即座に短縮

## 2025-02-04: インフラ整合性チェック追加
- セッション名変更時の5ファイルチェックリスト運用開始
- 循環依存の早期検出ルール追加

## 2025-02-05: 構造変更時の影響調査プロトコル
- ファイルの分割・移動・リネーム前に必ず `grep` で参照箇所を調査
- 影響を受けるファイル一覧を作成してから変更を開始
- テンプレート（src/ensemble/templates/）と実ファイル（.claude/）の両方を確認

## 2025-02-05: Workerハング対策
- Worker実行中、5分以上進捗がない場合はハングの可能性
- `tmux capture-pane -t %{pane_id} -p | tail -20` で状態確認
- Photosynthesizing/Transfiguring状態が継続していたらEscapeキーで割り込み

## 2026-02-07: ローカルスクリプトとテンプレート同期
- `ensemble upgrade` 実行時、scripts/ 配下のローカルファイルもテンプレートと同期確認が必要
- 特にpane-setup.sh: セッション名変数（CONDUCTOR_SESSION/WORKERS_SESSION）を使用すべき
- テンプレート版（src/ensemble/templates/scripts/）が正、ローカル版（scripts/）が従の原則

## 2026-02-07: Worker数の動的決定
- タスク数に応じてworker_count: 2〜4を動的に決定する
- Claude Max 5並列制限: Conductor用1 + Worker用最大4
- タスク数 ≤ 2 → worker_count: 2, タスク数3 → 3, タスク数4以上 → 4
