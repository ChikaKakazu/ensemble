# PROGRESS.md

## 現在のフェーズ
Phase 2: 通信基盤 + 並列実行

## 完了済み
- [x] Phase 1: 基盤構築（全タスク完了 ✅）
  - [x] 1.2.1 pyproject.toml作成
  - [x] 1.2.2 CLAUDE.md作成（コンパクション復帰プロトコル含む）
  - [x] 1.2.3 conductor.mdエージェント定義
  - [x] 1.2.4 /goコマンド実装
  - [x] 1.2.5 /go-lightコマンド実装
  - [x] 1.2.6 /statusコマンド実装
  - [x] 1.2.7 settings.json（基本hooks）→ hooksは後で修正
  - [x] 1.2.8 setup.sh実装 ✅ (8/8 テストパス)
  - [x] 1.2.9 dashboard.mdテンプレート
  - [x] 1.2.10 MAX_THINKING_TOKENS=0 検証 ✅ 動作確認済み
  - [x] workflows/simple.yaml
  - [x] workflows/default.yaml
  - [x] `/go "hello world"` でPythonスクリプトが生成される ✅
  - [x] `/status` コマンド実装済み

## 進行中
- [ ] Phase 2: 通信基盤 + 並列実行
  - [ ] 2.2.1 dispatch.mdエージェント定義
  - [ ] 2.2.2 reviewer.mdエージェント定義
  - [ ] 2.2.3 アトミックロック実装 (src/ensemble/lock.py)
  - [ ] 2.2.4 キュー操作実装 (src/ensemble/queue.py)
  - [ ] 2.2.5 ログ出力実装 (src/ensemble/logger.py)
  - [ ] 2.2.6 pane-setup.sh実装
  - [ ] 2.2.7 launch.sh実装（Dispatch起動 + queue/クリーンアップ）
  - [ ] 2.2.8 ACK機構実装 (src/ensemble/ack.py)
  - [ ] 2.2.9 dashboard更新ロジック (src/ensemble/dashboard.py)

## 未着手
- [ ] Phase 3: 並列レビュー
- [ ] Phase 4: git worktree統合
- [ ] Phase 5: 自己改善 + コスト管理
- [ ] Phase 6: GitHub Actions統合（オプション）

## 決定事項（実装中に判明したこと）
| 項目 | 状態 | 備考 |
|------|------|------|
| MAX_THINKING_TOKENS=0 | ✅ 動作確認済み | 正常に動作 |
| setup.sh | ✅ 動作確認済み | 8/8 テストパス |
| /go コマンド | ✅ 動作確認済み | パターンA正常動作 |
| settings.json hooks | ⚠️ 要修正 | フォーマットエラー、Phase 2で対応 |
| ワークフロー実行方式 | 決定済み | Claudeが状態遷移、Pythonは集約ユーティリティ |
| ロック機構 | 決定済み | アトミックmv操作 |
| ログ形式 | 決定済み | コンソール=テキスト、ファイル=JSON |

## 次のアクション
1. Phase 2のTDD開始
   - `src/ensemble/logger.py` から着手
2. settings.json の hooks フォーマット修正

## セルフホスティング移行ポイント
Phase 2完了後、Ensemble自身でEnsembleの開発が可能になります。
