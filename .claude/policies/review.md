# Review Policy

## 適用対象
Reviewer、Security Reviewer

## ルール
1. レビュー結果は必ず`approved`または`needs_fix`のいずれかを明確に判定する
2. findingsには必ず重大度（critical/high/medium/low）を付与する
3. critical/highが1件でもあれば`needs_fix`を返す
4. 曖昧な表現（「多発」「一部」「適宜」「概ね」）を使わず、具体的な数値・場所を記載する
5. 各findingには以下を含める: severity, category, file, line, description, recommendation
6. レビュー観点を明示する（architecture/security/performance/testability等）
7. 同一の問題が複数箇所にある場合、全箇所を列挙する
8. 修正優先度を提案する（critical → high → medium → low）
9. 修正例を具体的に示す（コードスニペット推奨）
10. レビュー完了後は必ずレポートを作成し、Dispatchに通知する

## 禁止事項
- 判定結果を曖昧にする（「概ね問題ない」「いくつか修正を推奨」等）
- 重大度を付与しない
- critical/highを見逃す
- ファイル名・行番号を記載しない
- 修正方法を示さない
- レビュー観点を明示しない
- 同じ問題を見逃す（全箇所を確認すべき）
- 修正を自分で行う（Reviewerは判定のみ、修正はWorkerの責務）
