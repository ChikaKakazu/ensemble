# スキル化候補: CLAUDE.md分割タスクから

## 候補1: template-sync

**用途**: `.claude/` と `src/ensemble/templates/` の同期

**トリガー**:
- `.claude/agents/*.md` または `.claude/commands/*.md` を編集した時
- `src/ensemble/templates/` 配下のファイルを編集した時

**処理**:
1. 編集されたファイルを検出
2. 対応するペア（実ファイル↔テンプレート）を特定
3. 差分を確認し、同期を提案

**推奨度**: YES（二重管理のミス防止）

---

## 候補2: impact-analysis

**用途**: ファイル構造変更前の影響調査

**トリガー**:
- `mv`, `rm`, `rename` などの構造変更を検出した時
- 「分割」「移動」「リネーム」などのキーワード

**処理**:
1. 対象ファイルへの参照を `grep` で検索
2. 影響を受けるファイル一覧を生成
3. 修正計画を提案

**推奨度**: MAYBE（頻度が低い可能性）

---

## 候補3: worker-health-check

**用途**: Workerのハング検知と自動復旧

**トリガー**:
- Worker起動後、一定時間（5分）ACKがない場合
- Worker実行中、一定時間（10分）進捗がない場合

**処理**:
1. `tmux capture-pane` で状態確認
2. Photosynthesizing/Transfiguring状態が長時間継続を検知
3. 自動でEscapeキー送信 or Conductorにエスカレーション

**推奨度**: YES（今回のハング問題の再発防止）
