# 実装計画: Ensemble配布形式への変換

## 要件整理

### 目標
- Ensembleを他プロジェクトで利用可能な形式に変換
- `pip install ensemble-ai` / `uvx ensemble-ai` でインストール可能に
- `ensemble init` / `ensemble launch` コマンドを提供

### 参考設計（Shogun + Takt ハイブリッド）

| 観点 | Shogun方式 | Takt方式 | Ensemble採用 |
|------|-----------|----------|-------------|
| インストール | git clone | npm install | **pip/uv** |
| 起動 | 常駐型 | オンデマンド | **両方対応** |
| 設定場所 | リポジトリ内固定 | グローバル + ローカル | **グローバル + ローカル** |

---

## 現状の構造

```
ensemble/
├── .claude/
│   ├── agents/        # 7ファイル（conductor, dispatch, worker等）
│   ├── commands/      # 5ファイル（go, go-light, status等）
│   └── settings.json
├── src/ensemble/      # Pythonユーティリティ（10ファイル）
├── scripts/           # シェルスクリプト（6ファイル）
├── workflows/         # YAML定義（4ファイル）
├── queue/             # 通信キュー
├── status/            # ダッシュボード
└── pyproject.toml     # 既存（hatchling使用）
```

---

## 実装フェーズ

### Phase 1: CLIエントリーポイント作成
**概要**: `ensemble` コマンドを作成

**作成ファイル**:
- `src/ensemble/cli.py` - メインCLIエントリーポイント
- `src/ensemble/commands/init.py` - init コマンド
- `src/ensemble/commands/launch.py` - launch コマンド

**変更ファイル**:
- `pyproject.toml` - エントリーポイント追加、依存関係追加

**完了条件**:
- `ensemble --help` が動作する
- `ensemble init --help` が動作する
- `ensemble launch --help` が動作する

---

### Phase 2: テンプレートファイルのパッケージ同梱
**概要**: agents, commands, workflows をパッケージに同梱

**作成ファイル**:
- `src/ensemble/templates/` ディレクトリ
  - `agents/` - エージェント定義テンプレート
  - `commands/` - コマンド定義テンプレート
  - `workflows/` - ワークフロー定義テンプレート
  - `scripts/` - シェルスクリプトテンプレート

**変更ファイル**:
- `pyproject.toml` - package-data設定追加

**完了条件**:
- パッケージインストール後にテンプレートにアクセス可能
- `python -c "from ensemble.templates import get_template_path; print(get_template_path('agents'))"` が動作

---

### Phase 3: `ensemble init` 実装
**概要**: 対象プロジェクトに必要なファイルを配置

**機能**:
1. `.ensemble/` ディレクトリ作成
2. `queue/`, `status/` サブディレクトリ作成
3. `CLAUDE.md` 追記または作成
4. `.gitignore` 追記

**オプション**:
- `--full`: 全エージェント定義をローカルにコピー

**完了条件**:
- `cd /tmp/test-project && ensemble init` が成功
- `.ensemble/queue/`, `.ensemble/status/` が作成される
- `CLAUDE.md` にEnsembleセクションが追加される

---

### Phase 4: `ensemble launch` 実装
**概要**: tmuxセッションを起動

**機能**:
1. 現在ディレクトリを対象プロジェクトとして認識
2. グローバル設定 + ローカル設定をマージ
3. tmuxセッション作成（既存launch.shのロジック移植）

**設定読み込み優先順位**:
1. `./.ensemble/agents/*.md` （あれば）
2. `~/.config/ensemble/agents/*.md` （あれば）
3. パッケージ同梱テンプレート

**完了条件**:
- `ensemble launch` でtmuxセッションが起動
- Conductor, Dispatch, Dashboardペインが作成される

---

### Phase 5: グローバル設定サポート
**概要**: `~/.config/ensemble/` のサポート

**機能**:
1. 初回起動時にグローバル設定ディレクトリ作成
2. デフォルトエージェント定義をコピー
3. `config.yaml` でカスタマイズ可能に

**完了条件**:
- `~/.config/ensemble/agents/` にテンプレートがコピーされる
- グローバル設定がローカル設定で上書き可能

---

### Phase 6: パッケージ公開準備
**概要**: PyPI公開に向けた整備

**作業内容**:
1. `pyproject.toml` のメタデータ整備
2. LICENSE ファイル追加
3. README.md 更新（インストール手順）
4. テスト追加

**完了条件**:
- `pip install -e .` でローカルインストール成功
- `ensemble --version` がバージョン表示
- 基本的なテストが通る

---

## ファイル構成（実装後）

### パッケージ内

```
src/ensemble/
├── __init__.py
├── cli.py                    # メインCLI
├── commands/
│   ├── __init__.py
│   ├── init.py               # ensemble init
│   └── launch.py             # ensemble launch
├── config.py                 # 設定読み込み
├── templates/
│   ├── __init__.py
│   ├── agents/               # エージェント定義テンプレート
│   │   ├── conductor.md
│   │   ├── dispatch.md
│   │   ├── worker.md
│   │   ├── reviewer.md
│   │   ├── security-reviewer.md
│   │   ├── integrator.md
│   │   └── learner.md
│   ├── commands/             # コマンド定義テンプレート
│   │   ├── go.md
│   │   ├── go-light.md
│   │   ├── status.md
│   │   ├── review.md
│   │   └── improve.md
│   ├── workflows/            # ワークフロー定義
│   │   ├── simple.yaml
│   │   ├── default.yaml
│   │   ├── heavy.yaml
│   │   └── worktree.yaml
│   └── scripts/              # シェルスクリプト
│       ├── launch.sh
│       ├── pane-setup.sh
│       ├── worktree-create.sh
│       └── worktree-merge.sh
└── # 既存ユーティリティ（dashboard.py, queue.py等）
```

### ユーザー環境（インストール後）

```
~/.config/ensemble/           # グローバル設定
├── agents/                   # カスタマイズ用（オプション）
├── workflows/                # カスタマイズ用（オプション）
└── config.yaml               # グローバル設定

my-project/                   # 対象プロジェクト
├── .ensemble/                # ensemble init で作成
│   ├── agents/               # --full オプション時のみ
│   ├── queue/
│   │   ├── conductor/
│   │   ├── tasks/
│   │   ├── reports/
│   │   └── ack/
│   └── status/
│       └── dashboard.md
├── CLAUDE.md                 # Ensembleセクション追記
└── .gitignore                # queue/等を除外
```

---

## 依存関係

### 必須
- Python >= 3.11
- click >= 8.0 （CLI フレームワーク）
- pyyaml >= 6.0 （既存）

### オプション
- rich >= 13.0 （美しいターミナル出力）

---

## リスク評価

| リスク | 影響度 | 対策 |
|--------|--------|------|
| テンプレートの同梱漏れ | 高 | MANIFEST.in / pyproject.toml で明示指定 |
| パス解決の複雑化 | 中 | importlib.resources を使用 |
| 既存scripts/との整合性 | 中 | 段階的移行、後方互換性維持 |
| Claude Code の --agent オプション | 低 | .claude/agents/ へのコピーで対応 |

---

## 見積もり

| フェーズ | 変更ファイル数 | 新規ファイル数 |
|----------|--------------|--------------|
| Phase 1 | 1 | 3 |
| Phase 2 | 1 | 20+ |
| Phase 3 | 0 | 1 |
| Phase 4 | 0 | 1 |
| Phase 5 | 0 | 1 |
| Phase 6 | 2 | 2 |
| **合計** | **4** | **28+** |

---

## 確認事項

1. **パッケージ名**: `ensemble-ai` でよいか？（PyPIで `ensemble` は取得済みの可能性）
2. **Python バージョン**: 3.11+ でよいか？（3.10も対応すべきか）
3. **Claude Code の --agent オプション**: `.claude/agents/` にコピーする方式でよいか？
4. **`ensemble run` の実装**: Phase 7 として後回しでよいか？

---

**承認待ち**: この計画で進めてよろしいですか？
