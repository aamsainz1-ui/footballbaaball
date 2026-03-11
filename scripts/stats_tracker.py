#!/usr/bin/env python3
"""Stats Tracker — บันทึกผลทีเด็ดแต่ละวัน"""
import json, os, datetime

STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")

def _load():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return []

def _save(data):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_picks(picks, date=None):
    """Save picks for a date. picks = [{"match":"A vs B","pick":"A ต่อ 1 ลูก"}]"""
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")
    data = _load()
    # Remove existing entry for same date
    data = [d for d in data if d["date"] != date]
    entry = {
        "date": date,
        "picks": [{"match": p["match"], "pick": p["pick"], "result": None} for p in picks],
        "correct": 0,
        "total": len(picks)
    }
    data.append(entry)
    data.sort(key=lambda x: x["date"])
    _save(data)
    return entry

def update_result(date, match, result):
    """Update result for a specific match. result = 'win' | 'loss'"""
    data = _load()
    for entry in data:
        if entry["date"] == date:
            for p in entry["picks"]:
                if p["match"] == match:
                    p["result"] = result
            # Recalculate correct count
            entry["correct"] = sum(1 for p in entry["picks"] if p["result"] == "win")
            break
    _save(data)

def get_stats(days=7):
    """Get stats for last N days. Returns {correct, total, pct, entries}"""
    data = _load()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [d for d in data if d["date"] >= cutoff]
    correct = sum(d["correct"] for d in recent)
    total = sum(d["total"] for d in recent)
    decided = sum(
        1 for d in recent for p in d["picks"] if p["result"] is not None
    )
    pct = round(correct / decided * 100, 1) if decided > 0 else 0
    return {"correct": correct, "total": total, "decided": decided, "pct": pct, "entries": recent}

def get_today_picks():
    """Get today's picks entry"""
    data = _load()
    today = datetime.date.today().strftime("%Y-%m-%d")
    for d in data:
        if d["date"] == today:
            return d
    return None

if __name__ == "__main__":
    # Test
    print("Stats 7d:", get_stats(7))
    print("Stats 30d:", get_stats(30))
    t = get_today_picks()
    print("Today:", t)


def update_score(date, match, home_score, away_score):
    """บันทึกสกอร์จริงหลังเกมจบ"""
    data = load_stats()
    for d in data:
        if d["date"] == date:
            for p in d["picks"]:
                if p["match"] == match:
                    p["score"] = f"{home_score}-{away_score}"
                    break
    save_stats(data)
