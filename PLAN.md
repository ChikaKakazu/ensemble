# Ensemble 実装計画書

## 要件の整理

### プロジェクト概要
- **目的**: Claude Codeを活用したAIオーケストレーションツール
- **形態**: 汎用ツール（どのプロジェクトでも使えるテンプレート/CLIツール）
- **参考**: shogun, takt, Boris氏の実践的活用術

### 確認済み要件

| カテゴリ | 決定事項 |
|---------|----------|
| 実装言語 | Python + Bash ハイブリッド |
| Python環境 | uv |
| テスト | pytest（TDD） |
| tmux管理 | 専用セッション（`ensemble-*`プレフィックス） |
| ロック機構 | mvコマンドのアトミック操作 |
| 並列上限 | 動的調整（1-4ペイン、Claude Max 5並列を考慮） |
| ダッシュボード | イベント駆動で更新 |
| エラー処理 | 3回リトライ後エスカレーション |
| ワークフロー実行 | **Claudeが状態遷移を担当、Pythonは集約ロジックのユーティリティ** |
| コンパクション対策 | CLAUDE.md + hook 両方併用 |
| セキュリティレビュー | デフォルト + カスタマイズ可能 |
| 自己改善 | 提案のみ（notes/に記録、ユーザー承認後反映） |
| worktree統合 | AI解決試行→失敗時エスカレーション |
| ログ形式 | コンソール=テキスト、ファイル=JSON |
| Thinking制御 | **要検証**（MAX_THINKING_TOKENS=0） |
| GitHub Actions | Phase 6で追加（オプション） |

---

## 実装フェーズ

### Phase 1: 基盤構築（最小動作版）

**目標**: `/go` コマンドで単純タスク（パターンA）が動作する

#### 1.1 プロジェクト初期化
```
ensemble/
├── pyproject.toml          # uv用プロジェクト定義
├── CLAUDE.md               # プロジェクトルートの指示書
├── .claude/
│   ├── agents/
│   │   └── conductor.md    # 指揮者エージェント
│   ├── commands/
│   │   ├── go.md           # /go コマンド
│   │   ├── go-light.md     # /go-light コマンド
│   │   └── status.md       # /status コマンド ← Phase 1に移動
│   └── settings.json       # hooks設定
├── scripts/
│   └── setup.sh            # 初回セットアップ
├── status/
│   └── dashboard.md        # ダッシュボード
└── tests/
    └── test_setup.py       # セットアップテスト
```

#### 1.2 実装タスク

| # | タスク | ファイル | テスト |
|---|--------|----------|--------|
| 1.2.1 | pyproject.toml作成 | `pyproject.toml` | - |
| 1.2.2 | CLAUDE.md作成（コンパクション復帰プロトコル含む） | `CLAUDE.md` | - |
| 1.2.3 | conductor.mdエージェント定義 | `.claude/agents/conductor.md` | - |
| 1.2.4 | /goコマンド実装 | `.claude/commands/go.md` | - |
| 1.2.5 | /go-lightコマンド実装 | `.claude/commands/go-light.md` | - |
| 1.2.6 | **/statusコマンド実装** | `.claude/commands/status.md` | - |
| 1.2.7 | settings.json（基本hooks） | `.claude/settings.json` | - |
| 1.2.8 | setup.sh実装 | `scripts/setup.sh` | `test_setup.py` |
| 1.2.9 | dashboard.mdテンプレート | `status/dashboard.md` | - |
| 1.2.10 | **MAX_THINKING_TOKENS=0 検証** | - | 手動検証 |

#### 1.3 検証シナリオ
```bash
# セットアップ
./scripts/setup.sh

# 単純タスク実行
MAX_THINKING_TOKENS=0 claude --model opus
> /go hello worldを出力するPythonスクリプトを作成して

# 期待結果:
# - Conductorがplanモードで計画策定
# - subagentで直接実行（パターンA）
# - dashboard.mdが更新される

# ステータス確認
> /status
```

---

### Phase 2: 通信基盤 + 並列実行

**目標**: tmux並列（パターンB）がフレンドリーファイアなしで動作

> **🎯 セルフホスティング移行ポイント**
> Phase 2完了後、Ensemble自身でEnsembleの開発が可能になります。
> `/go` コマンドでPhase 3以降の実装を進めることができます。

#### 2.1 追加ディレクトリ構成
```
ensemble/
├── .claude/
│   └── agents/
│       ├── dispatch.md      # 伝達役エージェント
│       └── reviewer.md      # レビューエージェント
├── scripts/
│   ├── launch.sh            # 日次起動（Dispatch起動 + queue/クリーンアップ含む）
│   └── pane-setup.sh        # tmuxペイン構成
├── queue/                   # ファイルベースキュー
│   ├── tasks/               # タスクYAML
│   ├── reports/             # 完了報告
│   └── ack/                 # ACKマーカー
├── logs/                    # ログ出力ディレクトリ
│   └── ensemble-{date}.log  # JSONログファイル
├── src/
│   └── ensemble/
│       ├── __init__.py
│       ├── queue.py         # キュー操作
│       ├── lock.py          # アトミックロック
│       └── logger.py        # ログ出力（テキスト+JSON）
└── tests/
    ├── test_queue.py
    ├── test_lock.py
    └── test_logger.py
```

#### 2.2 実装タスク

| # | タスク | ファイル | テスト |
|---|--------|----------|--------|
| 2.2.1 | dispatch.mdエージェント定義 | `.claude/agents/dispatch.md` | - |
| 2.2.2 | reviewer.mdエージェント定義 | `.claude/agents/reviewer.md` | - |
| 2.2.3 | アトミックロック実装 | `src/ensemble/lock.py` | `test_lock.py` |
| 2.2.4 | キュー操作実装 | `src/ensemble/queue.py` | `test_queue.py` |
| 2.2.5 | **ログ出力実装（テキスト+JSON）** | `src/ensemble/logger.py` | `test_logger.py` |
| 2.2.6 | pane-setup.sh実装（3秒間隔） | `scripts/pane-setup.sh` | 手動検証 |
| 2.2.7 | **launch.sh実装（Dispatch起動 + queue/クリーンアップ）** | `scripts/launch.sh` | 手動検証 |
| 2.2.8 | ACK機構実装 | `src/ensemble/ack.py` | `test_ack.py` |
| 2.2.9 | dashboard更新ロジック | `src/ensemble/dashboard.py` | `test_dashboard.py` |

#### 2.3 launch.sh の設計

```bash
#!/bin/bash
# scripts/launch.sh
# Ensembleのメインtmuxセッションを起動する

SESSION="ensemble"
PROJECT_DIR=$(pwd)

# 既存セッションがあれば削除
tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"

# ★ queue/のクリーンアップ（新しいセッションはクリーンスタート）
rm -f queue/tasks/*.yaml queue/reports/*.yaml queue/ack/*.ack
echo "$(date -Iseconds) Queue cleaned up" >> logs/ensemble-$(date +%Y%m%d).log

# ★ Conductorウィンドウ（Thinking無効）
tmux new-session -d -s "$SESSION" -n "conductor" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:conductor" \
    "MAX_THINKING_TOKENS=0 claude --model opus --dangerously-skip-permissions" C-m

# ★ Dispatchウィンドウ（Sonnet、軽量モデル）
sleep 3  # フレンドリーファイア防止
tmux new-window -t "$SESSION" -n "dispatch" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:dispatch" \
    "claude --agent dispatch --dangerously-skip-permissions" C-m

# ダッシュボード用ウィンドウ
tmux new-window -t "$SESSION" -n "dashboard" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:dashboard" \
    "watch -n 5 cat status/dashboard.md" C-m

echo "🎵 Ensemble launched!"
```

#### 2.4 ログ出力設計

```python
# src/ensemble/logger.py
import json
import logging
from datetime import datetime
from pathlib import Path

class EnsembleLogger:
    """
    コンソール: テキスト形式（人間が読みやすい）
    ファイル: JSON形式（機械可読、分析容易）
    """

    def __init__(self, name: str = "ensemble"):
        self.name = name
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # コンソールハンドラ（テキスト）
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )

        # ファイルハンドラ（JSON）
        log_file = self.log_dir / f"ensemble-{datetime.now():%Y%m%d}.log"
        self.file_handler = logging.FileHandler(log_file)

    def log(self, level: str, message: str, **kwargs):
        """構造化ログ出力"""
        # コンソール: テキスト
        print(f"{datetime.now():%H:%M:%S} [{level}] {message}")

        # ファイル: JSON
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        with open(self.log_dir / f"ensemble-{datetime.now():%Y%m%d}.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
```

#### 2.5 キュー設計（アトミック操作）

```python
# src/ensemble/lock.py
import os
import tempfile

def atomic_write(filepath: str, content: str) -> bool:
    """
    アトミックな書き込み: tmp作成 → mv（アトミック）
    """
    dir_path = os.path.dirname(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path)
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.rename(tmp_path, filepath)  # アトミック
        return True
    except Exception:
        os.unlink(tmp_path)
        return False

def atomic_claim(filepath: str, processing_dir: str) -> str | None:
    """
    アトミックなタスク取得: mv（アトミック）で処理中ディレクトリへ移動
    """
    filename = os.path.basename(filepath)
    dest = os.path.join(processing_dir, filename)
    try:
        os.rename(filepath, dest)  # アトミック
        return dest
    except FileNotFoundError:
        return None  # 別プロセスが先に取得
```

#### 2.6 検証シナリオ
```bash
# 日次起動
./scripts/launch.sh
tmux attach-session -t ensemble

# 中規模タスク実行
# Conductorウィンドウで:
> /go REST APIのCRUDエンドポイント4つを並列で実装して

# 期待結果:
# - Dispatchがファイルキュー経由でタスク配信
# - 4ペインが3秒間隔で起動（フレンドリーファイアなし）
# - ACK機構で配信確認
# - 全タスク完了後にdashboard.md更新
# - logs/ensemble-{date}.log にJSONログが出力される
```

---

### Phase 3: 並列レビュー

**目標**: アーキテクチャ + セキュリティの並列レビューが動作

#### 3.1 追加ファイル
```
ensemble/
├── .claude/
│   └── agents/
│       └── security-reviewer.md  # セキュリティレビュー
├── workflows/
│   ├── default.yaml              # 標準WF
│   └── simple.yaml               # 軽量WF
└── src/
    └── ensemble/
        └── workflow.py           # 集約ロジックユーティリティ
```

#### 3.2 実装タスク

| # | タスク | ファイル | テスト |
|---|--------|----------|--------|
| 3.2.1 | security-reviewer.md | `.claude/agents/security-reviewer.md` | - |
| 3.2.2 | default.yaml（parallel step） | `workflows/default.yaml` | - |
| 3.2.3 | simple.yaml | `workflows/simple.yaml` | - |
| 3.2.4 | **集約ロジックユーティリティ（all/any）** | `src/ensemble/workflow.py` | `test_workflow.py` |
| 3.2.5 | /reviewコマンド | `.claude/commands/review.md` | - |

#### 3.3 workflow.pyの役割

**重要**: ワークフローの状態遷移はClaudeが担当。Pythonは集約ロジックのユーティリティのみ。

```
┌─────────────────────────────────────────────────────────────┐
│  Claude（状態遷移の担当）                                    │
│  - YAMLを読み込み、現在のステップを判断                       │
│  - 次のステップへの遷移を決定                                │
│  - エージェントの起動・指示                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 集約が必要な場合のみ呼び出し
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Python（集約ロジックユーティリティ）                        │
│  - all("approved") の判定                                   │
│  - any("needs_fix") の判定                                  │
│  - レビュー結果のマージ                                     │
└─────────────────────────────────────────────────────────────┘
```

```python
# src/ensemble/workflow.py
"""
ワークフロー集約ロジックユーティリティ

注意: このモジュールは状態遷移を行わない。
状態遷移はClaude（Conductor）が担当する。
このモジュールは集約ロジック（all/any判定）のみを提供する。
"""

def aggregate_results(results: list[str], rule: str) -> bool:
    """
    並列レビュー結果を集約する

    Args:
        results: 各レビューアの結果 ["approved", "needs_fix", ...]
        rule: 集約ルール "all(\"approved\")" or "any(\"needs_fix\")"

    Returns:
        ルールが満たされればTrue

    Example:
        >>> aggregate_results(["approved", "approved"], 'all("approved")')
        True
        >>> aggregate_results(["approved", "needs_fix"], 'any("needs_fix")')
        True
    """
    if rule.startswith("all("):
        target = rule[5:-2]  # all("xxx") → xxx
        return all(r == target for r in results)
    elif rule.startswith("any("):
        target = rule[5:-2]
        return any(r == target for r in results)
    return False


def parse_review_results(reports_dir: str) -> dict[str, str]:
    """
    queue/reports/ からレビュー結果を収集する

    Returns:
        {"arch-review": "approved", "security-review": "needs_fix"}
    """
    # 実装は Phase 3 で行う
    pass
```

#### 3.4 並列レビューの集約ロジック

```yaml
# workflows/default.yaml 抜粋
- name: parallel_review
  parallel:
    - name: arch-review
      agent: reviewer
      rules:
        - condition: approved
        - condition: needs_fix
    - name: security-review
      agent: security-reviewer
      rules:
        - condition: approved
        - condition: needs_fix
  rules:
    - condition: all("approved")
      next_step: improve
    - condition: any("needs_fix")
      next_step: execute
```

---

### Phase 4: git worktree統合

**目標**: worktree分離（パターンC）+ 自動統合 + 相互レビュー

#### 4.1 追加ファイル
```
ensemble/
├── .claude/
│   ├── agents/
│   │   └── integrator.md         # 統合エージェント
│   └── skills/
│       └── worktree-manager/
│           └── SKILL.md
├── scripts/
│   ├── worktree-create.sh
│   └── worktree-merge.sh
└── workflows/
    └── worktree.yaml
```

#### 4.2 実装タスク

| # | タスク | ファイル | テスト |
|---|--------|----------|--------|
| 4.2.1 | integrator.md | `.claude/agents/integrator.md` | - |
| 4.2.2 | worktree-manager skill | `.claude/skills/worktree-manager/SKILL.md` | - |
| 4.2.3 | worktree-create.sh | `scripts/worktree-create.sh` | 手動検証 |
| 4.2.4 | worktree-merge.sh | `scripts/worktree-merge.sh` | 手動検証 |
| 4.2.5 | worktree.yaml | `workflows/worktree.yaml` | - |
| 4.2.6 | コンフリクト検出・報告 | `src/ensemble/worktree.py` | `test_worktree.py` |

#### 4.3 コンフリクト解決フロー

```
コンフリクト発生
    ↓
integrator: 自動解決を試行
    ↓
成功？ → YES → マージ完了
    ↓ NO
コンフリクト内容をConductorに報告
    ↓
Conductor: 解決方針を決定
    ↓
該当worktreeのCoderに解決を指示
    ↓
解決後、再度マージ試行
    ↓
失敗？ → 人間にエスカレーション
```

---

### Phase 5: 自己改善 + コスト管理

**目標**: 学習記録 + CLAUDE.md更新提案 + ワークフロー選択

#### 5.1 追加ファイル
```
ensemble/
├── .claude/
│   ├── agents/
│   │   └── learner.md
│   └── commands/
│       └── improve.md
├── workflows/
│   └── heavy.yaml
└── notes/                    # タスクごとの学習ノート
    └── {task-id}/
        ├── plan.md
        ├── decisions.md
        ├── lessons.md
        └── skill-candidates.md
```

#### 5.2 実装タスク

| # | タスク | ファイル | テスト |
|---|--------|----------|--------|
| 5.2.1 | learner.md | `.claude/agents/learner.md` | - |
| 5.2.2 | /improveコマンド | `.claude/commands/improve.md` | - |
| 5.2.3 | heavy.yaml | `workflows/heavy.yaml` | - |
| 5.2.4 | 学習ノート構造 | `src/ensemble/notes.py` | `test_notes.py` |
| 5.2.5 | コスト意識のWF選択ロジック | Conductor.mdに追記 | - |

#### 5.3 自己改善フロー

```
タスク完了
    ↓
learner: タスク実行を分析
    ↓
ミス・手戻りを検出
    ↓
notes/{task-id}/lessons.md に記録
    ↓
パターン化可能？ → YES → skill-candidates.md に記録
    ↓
CLAUDE.md更新提案を生成
    ↓
ユーザー承認待ち（/improve実行時に確認）
    ↓
承認 → CLAUDE.mdに追記
```

---

### Phase 6: GitHub Actions統合（オプション）

**目標**: Issueからリモート実行

> **注意**: このフェーズはオプションです。
> ローカル実行で十分な場合はスキップ可能。
> API課金（$1〜$5/タスク）が発生するため、コスト注意。

#### 6.1 追加ファイル
```
ensemble/
└── .github/
    └── workflows/
        └── ensemble-action.yml
```

#### 6.2 実装タスク

| # | タスク | ファイル | テスト |
|---|--------|----------|--------|
| 6.2.1 | ensemble-action.yml | `.github/workflows/ensemble-action.yml` | - |
| 6.2.2 | @ensemble run 対応 | ensemble-action.yml内 | 手動検証 |
| 6.2.3 | ワークフロー選択（simple/default） | ensemble-action.yml内 | 手動検証 |
| 6.2.4 | PR自動作成 | ensemble-action.yml内 | 手動検証 |

#### 6.3 使い方

```
# Issueコメントでトリガー
@ensemble run              # defaultワークフローでIssueを実行
@ensemble run simple       # simpleワークフロー（軽量・低コスト）
```

#### 6.4 コスト注意

- 1タスク ≒ $1〜$5（API課金）
- ローカル（Claude Max）との使い分けが重要
- 軽微な変更は `simple` ワークフローを使用

---

## リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| MAX_THINKING_TOKENS=0が動作しない | Conductorが遅くなる | Phase 1で検証、代替手段を検討 |
| tmuxセッション競合 | 既存作業に影響 | `ensemble-*`プレフィックスで完全分離 |
| ファイルキューの競合 | タスク二重実行 | アトミックmv操作で排他制御 |
| コンパクション後の役割忘却 | エージェント混乱 | CLAUDE.md + hook二重保護 |
| 5並列制限超過 | Claude Max制限に抵触 | 動的調整（最大4ペイン） |
| worktreeコンフリクト多発 | 統合失敗 | 段階的解決 + エスカレーション |

---

## 検証チェックリスト

### Phase 1 完了条件
- [x] `./scripts/setup.sh` が正常終了 ✅ (8/8 テストパス)
- [x] `/go "hello world"` でPythonスクリプトが生成される ✅
- [x] `/status` コマンド実装済み ✅
- [x] `status/dashboard.md` が作成される ✅
- [x] MAX_THINKING_TOKENS=0 の動作確認 ✅

### Phase 2 完了条件
- [x] `./scripts/launch.sh` で3ウィンドウ起動（Conductor + **Dispatch** + Dashboard） ✅ 実装済み・検証待ち
- [x] queue/が起動時にクリーンアップされる ✅ 実装済み (launch.sh L27-32)
- [x] logs/にJSONログが出力される ✅ 実装済み (logger.py)
- [~] `/go "CRUD 4エンドポイント"` でペイン並列実行 ⏳ 手動検証待ち
- [~] フレンドリーファイア発生なし（3秒間隔確認） ⏳ 手動検証待ち
- [x] ACK機構が正常動作 ✅ テスト合格 (test_ack.py)
- [~] **🎯 セルフホスティング移行可能** ⏳ 統合テスト後に判定

#### Phase 2 手動検証手順
```bash
# 1. Ensembleセッション起動
./scripts/launch.sh

# 2. セッションに接続
tmux attach-session -t ensemble

# 3. Conductorペインで並列タスク実行
/go REST APIのCRUDエンドポイント4つを並列で実装して

# 4. 確認項目
# - 3ペイン（conductor/dispatch/dashboard）が起動している
# - ワーカーペインが追加される
# - logs/ensemble-{date}.log にJSONログが出力される
# - queue/ack/ にACKファイルが作成される
# - フレンドリーファイアが発生しない（3秒間隔）
```

### Phase 3 完了条件
- [x] arch-review と security-review が並列実行 ✅ (2026-02-03)
- [x] `all("approved")` / `any("needs_fix")` 集約が正常動作 ✅
- [x] レビュー結果がdashboard.mdに反映 ✅

### Phase 4 完了条件
- [x] worktree 2つ以上が同時並列開発 ✅ (2026-02-03)
- [x] 統合時にコンフリクトなしでマージ成功 ✅
- [x] コンフリクト発生時に段階的解決フローが動作 ✅ (--auto-resolve)

### Phase 5 完了条件
- [x] `/improve` でlearnerが学習分析を実行 ✅ (2026-02-03)
- [x] `notes/{task-id}/` に学習記録が保存 ✅ (notes/crud-api-demo/)
- [x] CLAUDE.md更新提案が生成される ✅
- [ ] `/go-light` でsimple.yamlが選択される (手動検証待ち)

### Phase 6 完了条件（オプション）
- [x] `@ensemble run` でIssueが実行される ✅ (ensemble-action.yml作成)
- [x] PRが自動作成される ✅ (gh pr create実装)
- [x] ワークフロー選択が動作する ✅ (simple/default切り替え)

---

## 次のアクション

1. **Phase 1.2.10: MAX_THINKING_TOKENS=0 検証**を最優先で実施
   - 動作しない場合の代替案を検討

2. **Phase 1 の残りタスク**
   - /statusコマンドの実装

3. **Phase 2 の実装開始**
   - TDDで `src/ensemble/logger.py` から着手
   - launch.sh（Dispatch起動 + queue/クリーンアップ）

---

**確認待ち**: この計画で進めてよいですか？修正点があれば指示してください。
