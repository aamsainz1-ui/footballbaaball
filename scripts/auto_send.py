#!/usr/bin/env python3
"""ส่ง card เข้ากลุ่มผ่าน Bot Token"""
import subprocess, sys, os, datetime, requests, glob

BAABALL_TOKEN = "8735951403:AAGZw2vM4FCKZMRiMcIVjp5PH64OHaz8B2Y"
LOTTO_TOKEN   = "8077699310:AAEJHmRk9pxAdUZv98PfazXhqcoz-hxJZBY"
GROUP_ID      = "-1003869825051"
WORKSPACE     = "/root/.openclaw/workspace"
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))

TH_DAYS = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]

def today_th():
    d = datetime.date.today()
    return f"{TH_DAYS[d.weekday()]} {d.strftime('%-d/%m/%Y')}"

def send_photo(token, path, caption):
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": GROUP_ID, "caption": caption},
            files={"photo": f},
            timeout=15
        )
    ok = r.json().get("ok")
    print(f"{'sent' if ok else 'error'}: {os.path.basename(path)}")
    return ok

mode = sys.argv[1] if len(sys.argv) > 1 else "football"

if mode == "football":
    subprocess.run(["python3", f"{SCRIPT_DIR}/daily_pipeline.py"], capture_output=True)
    send_photo(BAABALL_TOKEN, f"{WORKSPACE}/card_banker_today.png", f"ตัวเต็งคืนนี้ — Baaball\n{today_th()}")
    send_photo(BAABALL_TOKEN, f"{WORKSPACE}/card_step_today.png", f"สเต็ปคืนนี้ — Baaball\n{today_th()}")

elif mode == "football_stats":
    subprocess.run(["python3", f"{SCRIPT_DIR}/daily_pipeline.py", "--stats-only"], capture_output=True)
    send_photo(BAABALL_TOKEN, f"{WORKSPACE}/card_stats_today.png", f"ผลบอลคืนที่ผ่านมา — Baaball\n{today_th()}")

elif mode == "lotto":
    subprocess.run(["python3", f"{SCRIPT_DIR}/gen_lotto_all.py"], capture_output=True)
    lotto_labels = {
        "stock_evening": "🇹🇭 หุ้นไทยเย็น",
        "hanoi_special": "🇻🇳 ฮานอยพิเศษ",
        "hanoi": "🇻🇳 ฮานอยปกติ",
        "laos": "🇱🇦 ลาวพัฒนา",
    }
    for key, label in lotto_labels.items():
        card_path = f"{WORKSPACE}/card_lotto_{key}.png"
        if os.path.exists(card_path):
            send_photo(LOTTO_TOKEN, card_path, f"{label} — บ้านหวย888\n{today_th()}")
