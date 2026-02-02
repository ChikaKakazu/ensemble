# Ensemble リファクタリング進捗レポート

**日時**: 2026-02-03
**フェーズ**: 通信基盤リファクタリング

---

## 完了した作業

### 1. 通信基盤の構築

| ディレクトリ | 用途 | 状態 |
|-------------|------|------|
| `queue/conductor/` | Conductor → Dispatch 指示 | ✅ |
| `queue/tasks/` | Dispatch → Worker タスク配信 | ✅ |
| `queue/ack/` | Worker 受領確認 | ✅ |
| `queue/reports/` | Worker 完了報告 | ✅ |

### 2. エージェント定義の整備

| エージェント | ファイル | 主な追加内容 |
|-------------|----------|-------------|
| Conductor | `.claude/agents/conductor.md` | 待機プロトコル、起動トリガー |
| Dispatch | `.claude/agents/dispatch.md` | 待機プロトコル、起動トリガー、タスク配信手順 |
| Worker | `.claude/agents/worker.md` | 新規作成、ACK/完了報告プロトコル |

### 3. スクリプトの改善

| スクリプト | 変更内容 |
|-----------|----------|
| `launch.sh` | `--agent` フラグ追加（conductor, dispatch） |
| `pane-setup.sh` | `--agent worker` 追加、WORKER_ID設定、待機時間追加 |

### 4. テンプレートの作成

- `templates/dispatch-instruction.yaml` - Conductor → Dispatch 指示フォーマット
- `templates/worker-task.yaml` - タスク配信フォーマット
- `templates/worker-report.yaml` - 完了報告フォーマット

### 5. 動作確認済みの機能

- ✅ `--agent` フラグによるエージェント定義の自動読み込み
- ✅ パターンB（tmux並列）の基本フロー
- ✅ ワーカーペインの動的追加
- ✅ タスクファイルの配信
- ✅ ACKファイルの作成
- ✅ 完了報告の作成（プロトコル準拠）
- ✅ 複数タスクの並列実行（greet.py, farewell.py, add.py, multiply.py, power.py, modulo.py）

---

## 残っている課題

### 課題1: send-keys の自動実行問題（優先度: 高）

**現象**:
`tmux send-keys -t pane "テキスト" Enter` を送っても、Claudeが自動的に実行しない。
入力欄にテキストが入った状態で止まり、手動でEnterを押すと動作する。

**原因**:
- Claudeが起動中・出力中の場合、send-keysのEnterが処理されない
- Claudeが「入力待ち状態」になるタイミングが予測できない

**試した対策**:
- `C-m` → `Enter` に変更 → 効果なし
- `select-pane` でフォーカス移動 → 効果なし
- 待機時間の追加（3秒、10秒、15秒）→ 不十分

**検討中の対策**:
1. より長い待機時間（30秒以上）を設ける
2. エージェント定義を簡素化し、起動時の出力を最小化
3. 半自動運用（通知後に手動でEnter）

### 課題2: タイミング依存の不安定さ（優先度: 中）

**現象**:
- Dispatchがワーカー起動直後に指示を送ると、ワーカーがまだ起動完了していない
- タイムアウト → リトライで最終的には動作するが、前の指示が残る問題

**原因**:
- Claudeの起動完了タイミングが不定
- 起動完了を検知する仕組みがない

### 課題3: shogunとの違い（参考）

shogun（参考実装）では動作している理由:
- 起動直後の「入力待ち状態」でsend-keysを送信
- エージェントが処理完了後、自然に入力待ち状態に戻る
- そのタイミングで次のsend-keysが届く

Ensembleとの違い:
- `--agent`フラグでエージェント定義を読み込む際、初期メッセージが出力される
- その出力中にsend-keysを送ると無視される

---

## 現在の運用フロー（半自動）

```
1. Conductor → dispatch-instruction.yaml 作成
2. Conductor → Dispatchに通知 (send-keys)
3. 👤 Dispatchペインに移動してEnter
4. Dispatch → ワーカー起動 + タスク配信
5. 👤 各ワーカーペインに移動してEnter
6. Workers → タスク実行 → ACK + 完了報告
7. Dispatch → Conductorに報告
8. 👤 Conductorペインに移動してEnter
```

**👤 = 手動でEnter押下が必要な箇所**

---

## 今後の改善案

### 案A: 待機時間の最適化

```bash
# 通知送信後、十分な待機時間を設ける
tmux send-keys -t pane "テキスト"
sleep 10  # Claudeの出力完了を待つ
tmux send-keys -t pane Enter
```

**メリット**: 実装が簡単
**デメリット**: 待機時間が長くなる、確実性に欠ける

### 案B: エージェント定義の簡素化

起動時に出力を最小化し、純粋な入力待ち状態を維持する。

```markdown
## 起動時の行動
何も出力せず、入力を待つ。
```

**メリット**: 根本的な解決
**デメリット**: デバッグが困難になる

### 案C: ファイル監視方式

`inotifywait` でキューディレクトリを監視し、新ファイル検知時に処理を開始。

```bash
inotifywait -m queue/tasks/ -e create | while read; do
  # 新タスク処理
done
```

**メリット**: 確実な検知
**デメリット**: 実装が複雑、Claudeとの連携が必要

### 案D: 半自動運用の受け入れ

現状の半自動運用をドキュメント化し、正式な運用フローとする。

**メリット**: すぐに使える
**デメリット**: 手動操作が必要

---

## 作成されたファイル一覧

```
.claude/agents/
├── conductor.md (更新)
├── dispatch.md (更新)
├── worker.md (新規)
├── integrator.md (更新)
├── learner.md
├── reviewer.md
└── security-reviewer.md

queue/
├── conductor/
│   └── dispatch-instruction.yaml
├── tasks/
│   ├── worker-1-task.yaml
│   └── worker-2-task.yaml
├── ack/
│   ├── task-301.ack
│   └── task-302.ack
└── reports/
    ├── task-301.yaml
    └── task-302.yaml

scripts/
├── launch.sh (更新)
├── pane-setup.sh (更新)
└── dashboard-update.sh (新規)

templates/
├── dispatch-instruction.yaml (新規)
├── worker-task.yaml (新規)
└── worker-report.yaml (新規)

# テストで作成されたファイル
greet.py
farewell.py
add.py
multiply.py
power.py
modulo.py
```

---

## 次のアクション候補

1. **案A〜Dのいずれかを実装** - 自動化の改善
2. **パターンCのテスト** - git worktree分離の検証
3. **変更をコミット** - 現在の進捗を保存
4. **ドキュメント整備** - 使い方ガイドの作成
