#!/usr/bin/env python3
"""วิเคราะห์ pattern หวย + ใบ้เลข"""
import json, os, datetime, random
from collections import Counter
from lotto_scraper import get_history

def analyze(lotto_type="hanoi"):
    history = get_history(lotto_type, days=30)

    if len(history) < 3:
        # ไม่มีข้อมูลพอ — ใช้ random analysis
        return _random_analysis(lotto_type)

    tops = [h[lotto_type]["3top"] for h in history if h.get(lotto_type)]
    bots = [h[lotto_type]["2bot"] for h in history if h.get(lotto_type)]

    # วิเคราะห์เลขท้าย 2 ตัว
    bot_counter = Counter(bots)
    top_counter = Counter(tops)

    # เลขที่ออกบ่อย
    hot_2 = bot_counter.most_common(3)
    hot_3 = top_counter.most_common(3)

    # pattern คู่/คี่
    last5_bots = bots[-5:]
    even_count = sum(1 for b in last5_bots if int(b) % 2 == 0)
    odd_count = 5 - even_count
    next_parity = "คู่" if odd_count > even_count else "คี่"

    # pattern สูง/ต่ำ (ท้าย 2 ตัว ≥ 50 = สูง)
    high_count = sum(1 for b in last5_bots if int(b) >= 50)
    next_height = "สูง" if high_count < 3 else "ต่ำ"

    # สร้างเลขเด็ด 2 ตัวล่าง
    # ใช้เลขที่ยังไม่ออกนาน (เลขที่ hot_2 ไม่มี)
    all_bots = set(f"{i:02d}" for i in range(100))
    recent_bots = set(bots[-10:])
    cold_bots = list(all_bots - recent_bots)
    
    pred_2bot = cold_bots[0] if cold_bots else hot_2[0][0]

    # เลขเด็ด 3 ตัวบน
    last3 = tops[-3:]
    digits = []
    for t in last3:
        digits.extend(list(t))
    digit_count = Counter(digits)
    hot_digits = [d for d, _ in digit_count.most_common(5)]
    if len(hot_digits) >= 3:
        pred_3top = ''.join(hot_digits[:3])
    else:
        pred_3top = tops[-1] if tops else "000"

    # วิ่งบน = เลขหลักร้อยที่ออกบ่อย
    hundreds = [t[0] for t in tops]
    run = Counter(hundreds).most_common(1)[0][0] if hundreds else "5"

    name_map = {"hanoi": "ฮานอย", "laos": "ลาว", "hanoi_vip": "ฮานอย VIP"}
    reason = (f"วิเคราะห์จาก {len(history)} งวดล่าสุด · "
              f"pattern {next_parity}/{next_height} · "
              f"เลขท้ายที่ออกบ่อย: {', '.join([x[0] for x in hot_2[:2]])}")

    return {
        "lotto_type": lotto_type,
        "name": name_map.get(lotto_type, lotto_type),
        "3top": pred_3top,
        "2bot": pred_2bot,
        "run": run,
        "reason": reason,
        "history_count": len(history),
    }

def _random_analysis(lotto_type):
    """ใช้เมื่อไม่มีข้อมูลพอ"""
    name_map = {"hanoi": "ฮานอย", "laos": "ลาว", "hanoi_vip": "ฮานอย VIP"}
    import random
    random.seed(datetime.date.today().toordinal() + hash(lotto_type) % 100)
    d1, d2, d3 = random.randint(0,9), random.randint(0,9), random.randint(0,9)
    b1, b2 = random.randint(0,9), random.randint(0,9)
    return {
        "lotto_type": lotto_type,
        "name": name_map.get(lotto_type, lotto_type),
        "3top": f"{d1}{d2}{d3}",
        "2bot": f"{b1}{b2}",
        "run": str(d1),
        "reason": "เลขใหม่รอบนี้",
        "history_count": 0,
    }

if __name__ == "__main__":
    for t in ["hanoi", "laos"]:
        r = analyze(t)
        print(f"{r['name']}: 3ตัวบน={r['3top']} 2ตัวล่าง={r['2bot']} วิ่ง={r['run']}")
        print(f"  เหตุผล: {r['reason']}")
