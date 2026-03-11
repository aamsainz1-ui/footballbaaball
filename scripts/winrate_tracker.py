"""
 Win Rate Tracker — บันทึก+ติดตามสถิติทายถูก/ผิด

Usage:
  python winrate_tracker.py --log HOME AWAY PREDICTION  บันทึกทำนาย
  python winrate_tracker.py --result HOME AWAY RESULT    บันทึกผลจริง (home/away/draw)
  python winrate_tracker.py --stats                      แสดงสถิติ win rate
  python winrate_tracker.py --stats-text                 แสดงสถิติแบบข้อความ (สำหรับโพสต์)
"""

import json, os, sys, io, argparse
from datetime import datetime, timezone, timedelta

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

TZ = timezone(timedelta(hours=7))
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions.json")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"predictions": [], "stats": {"total": 0, "correct": 0, "wrong": 0, "pending": 0}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_prediction(home, away, prediction):
    data = load_data()
    entry = {
        "date": datetime.now(TZ).strftime("%Y-%m-%d"),
        "time": datetime.now(TZ).strftime("%H:%M"),
        "home": home,
        "away": away,
        "prediction": prediction,
        "result": None,
        "correct": None,
    }
    data["predictions"].append(entry)
    data["stats"]["total"] += 1
    data["stats"]["pending"] += 1
    save_data(data)
    print(f"✅ บันทึกทำนาย: {home} vs {away} → {prediction}")

def log_result(home, away, result):
    data = load_data()
    found = False
    for p in reversed(data["predictions"]):
        if p["home"] == home and p["away"] == away and p["result"] is None:
            p["result"] = result

            # Check if prediction was correct
            pred = p["prediction"].lower()
            if result == "home" and ("เจ้าบ้าน" in pred or "ชนะ" in pred or home.lower() in pred):
                p["correct"] = True
            elif result == "away" and ("เยือน" in pred or away.lower() in pred):
                p["correct"] = True
            elif result == "draw" and ("เสมอ" in pred or "ดรอว์" in pred):
                p["correct"] = True
            elif "สูง" in pred and result in ("over", "สูง"):
                p["correct"] = True
            elif "ต่ำ" in pred and result in ("under", "ต่ำ"):
                p["correct"] = True
            else:
                p["correct"] = False

            data["stats"]["pending"] -= 1
            if p["correct"]:
                data["stats"]["correct"] += 1
            else:
                data["stats"]["wrong"] += 1

            found = True
            status = "✅ ถูก!" if p["correct"] else "❌ ผิด"
            print(f"{status} {home} vs {away}: ทำนาย={p['prediction']}, ผลจริง={result}")
            break

    if not found:
        print(f"⚠️ ไม่พบทำนายสำหรับ {home} vs {away}")

    save_data(data)

def show_stats():
    data = load_data()
    s = data["stats"]
    total = s["total"]
    correct = s["correct"]
    wrong = s["wrong"]
    pending = s["pending"]
    rate = (correct / (correct + wrong) * 100) if (correct + wrong) > 0 else 0

    print(f"\n📊 สถิติทำนาย ")
    print(f"━" * 30)
    print(f"📈 Win Rate: {rate:.1f}%")
    print(f"✅ ถูก: {correct} คู่")
    print(f"❌ ผิด: {wrong} คู่")
    print(f"⏳ รอผล: {pending} คู่")
    print(f"📋 ทั้งหมด: {total} คู่")
    print(f"━" * 30)

    # Recent 10
    recent = [p for p in data["predictions"] if p["result"] is not None][-10:]
    if recent:
        print(f"\n🔄 10 คู่ล่าสุด:")
        for p in reversed(recent):
            icon = "✅" if p["correct"] else "❌"
            print(f"  {icon} {p['date']} {p['home']} vs {p['away']}: {p['prediction']} → {p['result']}")

def stats_text():
    """Generate stats text for Telegram posting"""
    data = load_data()
    s = data["stats"]
    correct = s["correct"]
    wrong = s["wrong"]
    rate = (correct / (correct + wrong) * 100) if (correct + wrong) > 0 else 0

    # Recent streak
    recent = [p for p in data["predictions"] if p["result"] is not None][-10:]
    streak = ""
    for p in recent:
        streak += "🟢" if p["correct"] else "🔴"

    lines = [
        f"📊 สถิติทำนาย ",
        f"━" * 20,
        f"📈 Win Rate: {rate:.1f}%",
        f"✅ ถูก {correct} / ❌ ผิด {wrong}",
        f"🎯 ฟอร์ม 10 นัดล่าสุด: {streak}",
        f"",
        f"💰 เดิมพันอย่างมีสติ",
        f"🔥 .com — ค่าน้ำดีที่สุด",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=" Win Rate Tracker")
    parser.add_argument("--log", nargs=3, metavar=("HOME", "AWAY", "PREDICTION"), help="บันทึกทำนาย")
    parser.add_argument("--result", nargs=3, metavar=("HOME", "AWAY", "RESULT"), help="บันทึกผลจริง (home/away/draw/over/under)")
    parser.add_argument("--stats", action="store_true", help="แสดงสถิติ")
    parser.add_argument("--stats-text", action="store_true", help="แสดงสถิติแบบข้อความโพสต์")
    args = parser.parse_args()

    if args.log:
        log_prediction(*args.log)
    elif args.result:
        log_result(*args.result)
    elif args.stats:
        show_stats()
    elif args.stats_text:
        stats_text()
    else:
        parser.print_help()
