# プロジェクト: Ensemble AI Orchestration

## 概要
このプロジェクトはEnsemble AIオーケストレーションシステムを使用しています。

## 作業再開プロトコル
1. `PROGRESS.md` を読み、現在のフェーズと次のアクションを確認
2. `PLAN.md` で詳細な計画を確認
3. 作業開始

## 基本ルール
- /go コマンドでタスクを開始する
- /go-light で軽量ワークフロー（コスト最小）
- 実行パターンはConductorが自動判定する
- 自己改善フェーズを必ず実行する
- Pythonスクリプト実行時は `uv run` を使用する（例: `uv run python script.py`, `uv run pytest`）

## デプロイ手順

「デプロイして」と言われたら以下を実行:

### 1. バージョンアップ（mainブランチで）

以下の2ファイルのバージョンを更新（パッチバージョンを+1）:
- `pyproject.toml` の `version = "x.y.z"`
- `src/ensemble/__init__.py` の `__version__ = "x.y.z"`

```bash
# コミット＆プッシュ
git add pyproject.toml src/ensemble/__init__.py
git commit -m "chore: bump version to x.y.z"
git push
```

### 2. deploy/productionにマージ

```bash
# deploy/productionブランチに切り替え
git checkout deploy/production

# mainをマージ
git merge main

# プッシュ（CIがPyPIにpublish）
git push

# mainブランチに戻る
git checkout main
```

**注意**: 必ず最後にmainブランチに戻ること

## ⚠️ コンパクション復帰プロトコル（全エージェント必須）

コンパクション後は、作業を再開する前に**必ず**以下を実行せよ:

1. **自分のペイン名を確認する**:
   ```bash
   tmux display-message -p '#W'
   ```

2. **対応するエージェント定義を読み直す**:
   - conductor → `.claude/agents/conductor.md`
   - dispatch → `.claude/agents/dispatch.md`
   - reviewer → `.claude/agents/reviewer.md`
   - （その他、自分の役割に対応するファイル）

3. **禁止事項を確認してから作業開始**

4. **現在のタスクをダッシュボードで確認**:
   ```bash
   cat status/dashboard.md
   ```

summaryの「次のステップ」を見てすぐ作業してはならぬ。
**まず自分が誰かを確認せよ。**

## 通信プロトコル v2.0

### 基本原則
- エージェント間の指示・報告はファイルベースキュー（queue/）経由
- ファイル作成後、send-keysで即座に通知（プライマリ）
- 通知失敗時はポーリングでフォールバック

### 通知チェーン
```
Worker完了 → queue/reports/に報告 → Dispatchにsend-keys通知
                                          ↓
                                    Dispatch集約
                                          ↓
                        completion-summary.yaml作成 → Conductorにsend-keys通知
```

### タイムアウト設定
- Dispatch: 3分待機後にqueue/reports/をポーリング（30秒間隔）
- Conductor: 完了通知を受信、または30分でタイムアウト

### 効果
- 検知時間: 3-5分待機 → 即座（通知により）
- 信頼性: ポーリングフォールバックで100%確実

## 実行パターン
- パターンA: 単純タスク → subagentで直接実行
- パターンB: 中規模タスク → tmux多ペインで並列実行
- パターンC: 大規模タスク → git worktreeで分離 + 各worktree内並列

## インフラ整合性チェック（必須）

セッション名・ウィンドウ名・ペイン構造を変更する際は、以下の5ファイル全てを確認せよ:

### チェックリスト
| ファイル | 確認項目 |
|---------|---------|
| src/ensemble/commands/_launch_impl.py | セッション名、ペイン分割、panes.env出力 |
| src/ensemble/templates/scripts/launch.sh | 同上（シェル版） |
| src/ensemble/templates/scripts/pane-setup.sh | セッション参照、ウィンドウ名 |
| .claude/agents/conductor.md | ASCII図、セッション説明 |
| src/ensemble/templates/agents/conductor.md | 同上（テンプレート版） |

### 変更時の手順
1. 上記5ファイルを全てgrepで検索
2. 変更対象を特定
3. 全ファイルを同時に修正（不整合防止）
4. テスト実行で動作確認

### 過去の教訓（2025-02-04）
セッション名変更（ensemble:workers → ensemble-workers:main）で
pane-setup.shの参照が不一致となり、循環依存が発生。
Criticalエスカレーションとなり、手動対応が必要になった。

## 曖昧語禁止ルール（全エージェント共通）

報告・コミュニケーションでは以下の曖昧表現を禁止。必ず具体的な数値・名称・場所を記載せよ。

| 禁止表現 | 代替表現の例 |
|---------|-------------|
| 多発 | 3回発生 |
| 一部 | src/api/auth.py の 45-52行目 |
| 適宜 | 5分後に再確認 |
| 概ね | 87% |
| いくつか | 4件 |
| しばらく | 30秒後 |
| 偏り | Worker-2に4件集中（全体の80%） |
| 既知の問題 | Issue #123 で報告済み |

**報告に必ず含めるべき情報:**
- **誰が**: Worker-1, Conductor など具体名
- **何件**: 数値で記載
- **何割**: パーセンテージで記載
- **どこで**: ファイルパス:行番号

## 学習済みルール（自動追記）
<!-- learner agentが自動追記するセクション -->

### 2025-02-04: 通信プロトコルv2.0導入
- Worker→Dispatch→Conductor の3段階通知チェーン実装
- ポーリングフォールバック追加
- 検知時間を3-5分から即座に短縮

### 2025-02-04: インフラ整合性チェック追加
- セッション名変更時の5ファイルチェックリスト運用開始
- 循環依存の早期検出ルール追加

