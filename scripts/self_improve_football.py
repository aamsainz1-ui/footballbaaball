#!/usr/bin/env python3
"""Self-Improvement: วิเคราะห์ picks ย้อนหลัง อัพเดท weight สำหรับ tded/tdedai"""
import json, os, re
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PICKS_LOG = os.path.join(SCRIPT_DIR, "picks_log.json")
WEIGHTS_FILE = os.path.join(SCRIPT_DIR, "football_weights.json")

def load_picks():
    if not os.path.exists(PICKS_LOG):
        return []
    with open(PICKS_LOG) as f:
        return json.load(f)

def analyze():
    picks = load_picks()
    if not picks:
        print("no picks data")
        return

    pattern_stats = defaultdict(lambda: {"win": 0, "loss": 0, "half_win": 0})

    for entry in picks:
        for pick in entry.get("picks", []):
            result = pick.get("result", "")
            prediction = pick.get("prediction", "").lower()

            # จับ pattern
            if "สูง" in prediction:
                key = "สูง"
            elif "ต่ำ" in prediction:
                key = "ต่ำ"
            elif "ต่อครึ่ง" in prediction:
                key = "ต่อครึ่ง"
            elif "ต่อ" in prediction:
                key = "ราคาต่อ"
            elif "รอง" in prediction:
                key = "รอง"
            else:
                key = "อื่นๆ"

            if result == "win":
                pattern_stats[key]["win"] += 1
            elif result == "half_win":
                pattern_stats[key]["half_win"] += 1
            else:
                pattern_stats[key]["loss"] += 1

    weights = {}
    for key, stat in pattern_stats.items():
        total = stat["win"] + stat["loss"] + stat["half_win"] * 0.5
        wins = stat["win"] + stat["half_win"] * 0.5
        weights[key] = round(wins / total, 3) if total > 0 else 0.5
        print(f"  {key}: {stat['win']}W/{stat['loss']}L/{stat['half_win']}HW → weight={weights[key]}")

    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)
    print(f"✅ บันทึก weights → {WEIGHTS_FILE}")
    return weights

if __name__ == "__main__":
    print("🧠 Self-Improvement Football")
    analyze()

def run():
    return analyze()
