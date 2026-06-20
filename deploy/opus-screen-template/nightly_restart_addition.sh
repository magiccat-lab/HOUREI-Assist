#!/bin/bash
# --- opus screen 追加分 ---
# 既存の nightly_restart.sh に以下を追加

OPUS_SCREEN="secretary-opus"
OPUS_MODEL="opus"  # or opus-4-6

# opus screen 停止
screen -ls | grep "\\.${OPUS_SCREEN}" | awk '{print $1}' | xargs -I{} screen -S {} -X quit 2>/dev/null
sleep 2

# opus screen 起動
screen -dmS "$OPUS_SCREEN" bash -c "claude --model $OPUS_MODEL --dangerously-skip-permissions"

echo "$(date): opus screen started as $OPUS_SCREEN" >> /tmp/nightly.log
