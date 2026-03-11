#!/usr/bin/env python3
"""ดึงผลหวยจาก web"""
import requests, json, os, datetime, re
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(SCRIPT_DIR, "lotto_history.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_today_results():
    today = datetime.date.today().strftime("%Y-%m-%d")
    result = {"date": today, "hanoi": None, "laos": None, "hanoi_vip": None}

    sources = [
        "https://lotto432ab.com",
        "https://www.lottoresult.info",
    ]

    for url in sources:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text()

            # ฮานอย
            hanoi = re.search(r'ฮานอย[^0-9]*([0-9]{3})[^0-9]*([0-9]{2})', text)
            if hanoi:
                result["hanoi"] = {"3top": hanoi.group(1), "2bot": hanoi.group(2)}

            # ลาว
            laos = re.search(r'ลาว[^0-9]*([0-9]{3})[^0-9]*([0-9]{2})', text)
            if laos:
                result["laos"] = {"3top": laos.group(1), "2bot": laos.group(2)}

            if result["hanoi"] or result["laos"]:
                break
        except Exception as e:
            continue

    # บันทึกลง history
    if result["hanoi"] or result["laos"]:
        history = load_history()
        history = [h for h in history if h["date"] != today]
        history.append(result)
        history = sorted(history, key=lambda x: x["date"])[-60:]
        save_history(history)

    return result

def get_history(lotto_type="hanoi", days=30):
    history = load_history()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    return [h for h in history if h["date"] >= cutoff and h.get(lotto_type)]

if __name__ == "__main__":
    r = fetch_today_results()
    print(json.dumps(r, ensure_ascii=False, indent=2))
