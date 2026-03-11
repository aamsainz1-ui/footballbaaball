#!/bin/bash
# Daily Football Tips — auto gen card + ส่งกลุ่ม Wo
# รัน 15:00 Bangkok (08:00 UTC) ทุกวัน

SCRIPT_DIR="/root/.openclaw/workspace/football-daily-analyst/football-daily-analyst/scripts"
OUTPUT="/root/.openclaw/workspace/card_daily.png"
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN /root/.openclaw/workspace/MaybeAgi/.env 2>/dev/null | cut -d= -f2)
GROUP_ID="-1003869825051"

cd "$SCRIPT_DIR"

# Gen card
python3 auto_card_gen.py 2>/dev/null
if [ ! -f "$OUTPUT" ]; then
    echo "card gen failed"
    exit 1
fi

# ส่งกลุ่ม
if [ -n "$BOT_TOKEN" ]; then
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto" \
        -F "chat_id=${GROUP_ID}" \
        -F "photo=@${OUTPUT}" \
        -F "caption=ทีเด็ดบอลประจำวัน" \
        > /dev/null
    echo "sent to group"
else
    echo "no BOT_TOKEN — card saved at $OUTPUT"
fi
