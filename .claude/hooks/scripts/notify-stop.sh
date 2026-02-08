#!/bin/bash
# notify-stop.sh
# Stop hook: エージェント作業完了時の通知

# ターミナルベルを鳴らす（最もポータブルな方法）
echo -e '\a'

# completion-summary.yamlが存在するか確認
if [ -f "queue/reports/completion-summary.yaml" ]; then
    echo "🎉 全タスク完了"
else
    echo "✓ エージェント作業完了"
fi
