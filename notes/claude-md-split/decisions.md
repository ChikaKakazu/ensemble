# 判断ログ: CLAUDE.md分割

## 判断1: 分割構成

**選択肢**:
1. CLAUDE.md + LEARNED.md の2ファイル構成
2. CLAUDE.md + .claude/rules/* + LEARNED.md の分離構成
3. 全て .claude/rules/ に移動

**決定**: 選択肢2

**理由**:
- CLAUDE.mdは常に読まれるため、最小限に
- .claude/rules/ はClaude Codeが自動読み込み
- LEARNED.mdは自動追記用に分離

---

## 判断2: pathsの不採用

**選択肢**:
1. pathsを使って条件付き読み込み
2. pathsを使わず常時読み込み

**決定**: 選択肢2（pathsなし）

**理由**:
- Ensembleはマルチエージェントシステム
- 通信プロトコル、インフラ情報は常時必要
- コンテキスト削減効果は約14%と限定的
- 複雑さが増すリスクの方が大きい

---

## 判断3: Worker分担

**選択肢**:
1. 1 Workerで6ファイル順次処理
2. 2 Workerで3ファイルずつ並列処理
3. 6 Workerで1ファイルずつ並列処理

**決定**: 選択肢2

**理由**:
- 実ファイルとテンプレートで自然に分割可能
- Claude Max 5並列制限を考慮（Conductor含め4以下が安全）
- オーバーヘッドと並列効果のバランス
