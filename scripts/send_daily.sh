#!/bin/bash
# ส่ง card ประจำวันเข้ากลุ่ม Wo
MODE=$1  # tips_football | stats_football | tips_lotto

SCRIPT_DIR="/root/.openclaw/workspace/football-daily-analyst/football-daily-analyst/scripts"
GROUP="-1003869825051"
TOKEN=$(grep TELEGRAM_BOT_TOKEN /root/.openclaw/workspace/MaybeAgi/.env 2>/dev/null | cut -d= -f2)

send_photo() {
  local file=$1
  local caption=$2
  if [ -n "$TOKEN" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendPhoto" \
      -F "chat_id=${GROUP}" -F "photo=@${file}" -F "caption=${caption}" > /dev/null
  fi
}

case "$MODE" in
  tips_football)
    cd "$SCRIPT_DIR" && python3 daily_pipeline.py 2>/dev/null
    send_photo "/root/.openclaw/workspace/card_banker_today.png" "ตัวเต็งคืนนี้"
    send_photo "/root/.openclaw/workspace/card_step_today.png" "สเต็ปคืนนี้"
    ;;
  stats_football)
    cd "$SCRIPT_DIR" && python3 daily_pipeline.py --stats-only 2>/dev/null
    send_photo "/root/.openclaw/workspace/card_stats_today.png" "ผลบอลคืนที่ผ่านมา"
    ;;
  tips_lotto)
    cd "$SCRIPT_DIR" && python3 lotto_daily.py --tips 2>/dev/null
    send_photo "/root/.openclaw/workspace/card_lotto_thu.png" "เลขเด็ดวันนี้ บ้านหวย888"
    ;;
esac
