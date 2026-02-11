# Ensemble Progress

**現在のバージョン**: 0.5.2
**最終更新**: 2025-02-12

## 完了済み

- [x] P0: 通信インフラ強化 (v0.5.0)
  - [x] P0-1: イベント駆動通信 (inbox_watcher.sh + inotifywait)
  - [x] P0-2: 排他制御 (flock + atomic write)
  - [x] P0-3: 3段階自動エスカレーション
- [x] P1: ワークフロー進化
  - [x] P1-1: ループ検知 (LoopDetector, CycleDetector)
  - [x] P1-2: 依存関係管理 (DependencyResolver)
  - [x] P1-3: NDJSONログ
- [x] CI/CDパイプラインモード (ensemble pipeline)
- [x] Issue #7: Conductorセッションのdashboard更新不具合修正
- [x] Issue #8: Anthropic記事調査 + 自律ループモード (ensemble loop)
- [x] Issue #10: ensemble scan コマンド (CodebaseScanner)

## 進行中

- [x] `/go` Phase 6: タスク完了後の次タスク探索（`--continuous`オプション）
- [ ] ensemble investigate コマンド (scan結果のAgent Teams調査)
- [ ] scannerのテストファイル除外オプション

## 未着手（ロードマップ）

- [ ] P2: プロンプト設計改善 (v0.7.0)
  - [ ] エージェント定義のテンプレート分離
  - [ ] Faceted Prompting統合
- [ ] P3: 運用機能充実 (v0.8.0)
  - [ ] P3-1: CI/CDパイプライン強化
  - [ ] P3-2: Bloom's Taxonomy モデル選択最適化
  - [ ] P3-3: Skills Discovery自動化
- [ ] Conductor自律ループ: scan→計画→実行→レビュー→scan の自動継続モード
- [ ] `ensemble loop`とマルチエージェント構成の統合
- [ ] Worker完了後のDispatch経由次タスク自動プッシュ
- [ ] ensemble scan → investigate → 実行 の自動パイプライン
- [ ] dashboard-update.sh 複数ペイン対応

## 既知の課題

- [ ] PLAN.mdのテンプレート部分に未チェック項目が残っている（実際のタスクではない）
- [ ] scanがテストファイル内のTODO/FIXMEを拾ってしまう（ノイズ）
- [ ] Agent Teamsとscanの連携フローが未実装
