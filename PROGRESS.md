# PROGRESS.md

## 現在のフェーズ
Phase 4: git worktree統合

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

- [x] Phase 2: 通信基盤 + 並列実行（全タスク完了 ✅）
  - [x] 2.2.1 dispatch.mdエージェント定義 ✅
  - [x] 2.2.2 reviewer.mdエージェント定義 ✅
  - [x] 2.2.3 アトミックロック実装 (src/ensemble/lock.py) ✅
  - [x] 2.2.4 キュー操作実装 (src/ensemble/queue.py) ✅
  - [x] 2.2.5 ログ出力実装 (src/ensemble/logger.py) ✅
  - [x] 2.2.6 pane-setup.sh実装 ✅
  - [x] 2.2.7 launch.sh実装（Dispatch起動 + queue/クリーンアップ） ✅
  - [x] 2.2.8 ACK機構実装 (src/ensemble/ack.py) ✅
  - [x] 2.2.9 dashboard更新ロジック (src/ensemble/dashboard.py) ✅
  - [x] 2.2.10 統合テスト（launch.sh実行確認） ✅

- [x] Phase 3: 並列レビュー（全タスク完了 ✅）
  - [x] 3.2.1 security-reviewer.md エージェント定義 ✅
  - [x] 3.2.2 default.yaml（parallel step）既に定義済み ✅
  - [x] 3.2.3 simple.yaml 既に定義済み ✅
  - [x] 3.2.4 集約ロジックユーティリティ (src/ensemble/workflow.py) ✅ (17テスト、82%カバレッジ)
  - [x] 3.2.5 /reviewコマンド実装 ✅

## 進行中
- [ ] Phase 4: git worktree統合
  - [ ] 4.2.1 integrator.md エージェント定義
  - [ ] 4.2.2 worktree-manager skill
  - [ ] 4.2.3 worktree-create.sh
  - [ ] 4.2.4 worktree-merge.sh
  - [ ] 4.2.5 worktree.yaml
  - [ ] 4.2.6 コンフリクト検出・報告 (src/ensemble/worktree.py)

## 未着手
- [ ] Phase 5: 自己改善 + コスト管理
- [ ] Phase 6: GitHub Actions統合（オプション）

## 決定事項（実装中に判明したこと）
| 項目 | 状態 | 備考 |
|------|------|------|
| MAX_THINKING_TOKENS=0 | ✅ 動作確認済み | 正常に動作 |
| setup.sh | ✅ 動作確認済み | 8/8 テストパス |
| /go コマンド | ✅ 動作確認済み | パターンA正常動作 |
| settings.json hooks | ✅ 修正済み | PreCompact, SessionStart hooks追加 |
| ワークフロー実行方式 | 決定済み | Claudeが状態遷移、Pythonは集約ユーティリティ |
| ロック機構 | ✅ 実装済み | アトミックmv操作、lock.py |
| ログ形式 | ✅ 実装済み | コンソール=テキスト、ファイル=JSON、logger.py |
| キュー操作 | ✅ 実装済み | queue.py (10テスト、94%カバレッジ) |
| ACK機構 | ✅ 実装済み | ack.py (8テスト、100%カバレッジ) |
| ダッシュボード | ✅ 実装済み | dashboard.py (8テスト、100%カバレッジ) |
| Phase 2 テスト | ✅ 54テストパス | 全体カバレッジ94% |
| Phase 2 統合テスト | ✅ 成功 | 3ウィンドウ起動、ログ出力、queue/クリーンアップ確認 |
| Phase 3 テスト | ✅ 71テストパス | 全体カバレッジ91% |
| workflow.py | ✅ 実装完了 | aggregate_results, parse_review_results, merge_findings |

## 次のアクション
1. Phase 4 開始（git worktree統合）
   - integrator.md 作成
   - worktree-manager skill
   - worktree-create.sh / worktree-merge.sh
   - worktree.yaml

## セルフホスティング移行ポイント
Phase 2完了 ✅ → Ensemble自身でEnsembleの開発が可能になりました。
