#!/usr/bin/env python3
"""
gen_lotto_today.py — generate lotto card (final template v9)
"""
import subprocess, json, base64, datetime, sys, os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REG = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf","rb").read()).decode()
FONT_BOLD = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf","rb").read()).decode()
BG_IMG = base64.b64encode(open("/tmp/char_wide.jpg","rb").read()).decode()
CARD_SCRIPT = os.path.join(SCRIPTS_DIR, "gen_lotto_card_final.js")
OUTPUT = "/root/.openclaw/workspace/card_lotto_thu.png"

TH_DAYS = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]

sys.path.insert(0, SCRIPTS_DIR)
from lotto_analyzer import analyze

def gen_card(output=OUTPUT):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    day = TH_DAYS[tomorrow.weekday()]
    date_str = f"{day} {tomorrow.strftime('%-d/%m/%Y')}"

    rounds_cfg = [
        ("hanoi","ฮานอยปกติ","18:00"),
        ("hanoi_vip","ฮานอย VIP","18:55"),
        ("laos","ลาวปกติ","20:00"),
    ]

    # ใช้รูปแบบ single round card (ส่งหลาย card)
    # หรือ gen card รวมก็ได้ — ตอนนี้ gen เป็น 1 card ต่อ round แรก (ฮานอย)
    r = analyze(rounds_cfg[0][0])
    ltype, lname, ltime = rounds_cfg[0]

    # gen payload สำหรับ v9
    payload = {
        "date": date_str,
        "lotto_date": f"งวด {tomorrow.strftime('%-d/%m/%Y')}",
        "output": output,
        "rounds": [{
            "title": f"{lname} ({ltime})",
            "hot3": r["3top"], "hot2": r["2bot"], "run": r["run"],
            "nums3": [r["3top"]], "nums2": [r["2bot"]], "runs": [r["run"]],
        }]
    }

    # เขียน args ลงไฟล์ชั่วคราว
    args_file = "/tmp/lotto_today_args.json"
    full_args = {
        "fontReg": FONT_REG, "fontBold": FONT_BOLD, "bgImg": BG_IMG,
        "data": payload
    }
    with open(args_file, "w") as f:
        json.dump(full_args, f)

    res = subprocess.run(["node", CARD_SCRIPT], capture_output=True, text=True)
    if res.returncode != 0:
        print("ERROR:", res.stderr[:200])
        return False
    return True

if __name__ == "__main__":
    if gen_card():
        print(f"card saved: {OUTPUT}")
    else:
        sys.exit(1)
