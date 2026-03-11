#!/usr/bin/env python3
"""Pipeline หวยรายวัน — gen card + เช็คผล"""
import subprocess, json, os, base64, datetime, sys
from lotto_analyzer import analyze
from lotto_scraper import fetch_today_results, get_history

FONT_REG = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf","rb").read()).decode()
FONT_BOLD = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf","rb").read()).decode()
CARD_SCRIPT = "/tmp/gen_lotto_card3.js"
STATS_FILE = os.path.join(os.path.dirname(__file__), "lotto_stats.json")

TH_DAYS = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]

def today_th():
    d = datetime.date.today()
    day = TH_DAYS[d.weekday()]
    return f"{day} {d.strftime('%-d/%m/%Y')}"

def gen_tips_card(output=None):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    day = TH_DAYS[tomorrow.weekday()]
    date_str = f"{day} {tomorrow.strftime('%-d/%m/%Y')}"

    lottos = []
    for t in ["hanoi", "laos"]:
        r = analyze(t)
        lottos.append({
            "name": r["name"],
            "numbers": [
                {"label": "3 ตัวบน", "value": r["3top"]},
                {"label": "2 ตัวล่าง", "value": r["2bot"]},
                {"label": "วิ่งบน", "value": r["run"]},
            ],
            "reason": r["reason"],
        })

    if output is None:
        output = f"/root/.openclaw/workspace/card_lotto_{tomorrow.strftime('%a').lower()}.png"

    payload = {
        "date": date_str,
        "time": "18:00 / 20:00",
        "round": tomorrow.strftime("%-d/%m/%Y"),
        "pattern_hit": 65,
        "output": output,
        "lottos": lottos,
    }

    r = subprocess.run(
        ["node", CARD_SCRIPT, FONT_REG, FONT_BOLD, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print(f"lotto_card:{output}")
        return output
    else:
        print("error:", r.stderr[:200])
        return None

def check_results():
    """เช็คผลจริงหลังหวยออก แล้ว gen stats card"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    results = fetch_today_results()

    stats = []
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            stats = json.load(f)

    for ltype in ["hanoi", "laos"]:
        actual = results.get(ltype)
        if not actual:
            continue
        pred = analyze(ltype)
        correct_3 = pred["3top"] == actual["3top"]
        correct_2 = pred["2bot"] == actual["2bot"]
        entry = {
            "date": today,
            "lotto": ltype,
            "predicted_3top": pred["3top"],
            "actual_3top": actual["3top"],
            "predicted_2bot": pred["2bot"],
            "actual_2bot": actual["2bot"],
            "correct_3top": correct_3,
            "correct_2bot": correct_2,
        }
        stats = [s for s in stats if not (s["date"] == today and s["lotto"] == ltype)]
        stats.append(entry)
        result_str = "WIN" if correct_2 else "LOSS"
        print(f"{ltype}: {actual['3top']}/{actual['2bot']} | เดา {pred['3top']}/{pred['2bot']} | {result_str}")

    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return results

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--tips"
    if mode == "--tips":
        gen_tips_card()
    elif mode == "--check":
        check_results()
    elif mode == "--both":
        gen_tips_card()
        check_results()
