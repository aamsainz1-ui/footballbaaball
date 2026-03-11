#!/usr/bin/env python3
"""เช็คผลหวยด้วย Gemini CLI + สรุปด้วย MiniMax"""
import subprocess, json, datetime, os, re, requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(SCRIPT_DIR, "lotto_history.json")

MINIMAX_KEY = "sk-cp-rXcB1WPEaulA3lvnKFTxwjKQcYvp4K5qjBy-YT4Q9DwRhZshfcq7gMCCGAW7QayYfLIln_ffmJh6A1J3WyqPF5ujnhmY45NSEvdAQQRGTdSG5umuW6WbP-U"
MINIMAX_URL = "https://api.minimax.io/v1/chat/completions"

def gemini_fetch(query, timeout=40):
    try:
        r = subprocess.run(
            ["gemini", "--sandbox", "false", "--yolo", "--prompt", query],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""

def fetch_results_gemini(date_str=None):
    if not date_str:
        d = datetime.date.today()
        date_str = d.strftime("%-d %B %Y")

    results = {}

    for lotto_name, key in [("ฮานอยปกติ", "hanoi"), ("หวยลาว", "laos"), ("ฮานอย VIP", "hanoi_vip")]:
        q = f"ผล{lotto_name}วันที่ {date_str} 3 ตัวบน และ 2 ตัวล่าง คืออะไร ตอบเฉพาะตัวเลขเท่านั้น format: 3ตัวบน=XXX 2ตัวล่าง=XX"
        ans = gemini_fetch(q, timeout=35)
        print(f"Gemini {lotto_name}: {ans[:100]}")

        m3 = re.search(r'3ตัวบน[=:\s]*([0-9]{3})', ans)
        m2 = re.search(r'2ตัวล่าง[=:\s]*([0-9]{2})', ans)
        if not m3:
            m3 = re.search(r'([0-9]{3})', ans)
        if not m2:
            m2 = re.search(r'\b([0-9]{2})\b', ans)

        if m3 and m2:
            results[key] = {"3top": m3.group(1), "2bot": m2.group(1)}

    return results

def minimax_summarize(predictions, actuals):
    """สรุปผลด้วย MiniMax"""
    lines = []
    for key, act in actuals.items():
        pred = predictions.get(key, {})
        name = {"hanoi":"ฮานอย","laos":"ลาว","hanoi_vip":"ฮานอย VIP"}.get(key, key)
        hit2 = pred.get("2bot") == act.get("2bot")
        hit3 = pred.get("3top") == act.get("3top")
        lines.append(f"{name}: ออก {act['3top']}/{act['2bot']} | ทาย {pred.get('3top','?')}/{pred.get('2bot','?')} | {'ถูก' if hit2 else 'พลาด'} 2ตัวล่าง")

    prompt = "สรุปผลหวยคืนนี้แบบสั้นกระชับ เป็นภาษาไทย นักวิเคราะห์หวย:\n" + "\n".join(lines)

    try:
        r = requests.post(MINIMAX_URL,
            headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
            json={"model": "MiniMax-M2.5", "messages": [{"role": "user", "content": prompt}]},
            timeout=15)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "\n".join(lines)

def save_results(results):
    today = datetime.date.today().strftime("%Y-%m-%d")
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    history = [h for h in history if h["date"] != today]
    entry = {"date": today}
    entry.update(results)
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"saved: {today}")

if __name__ == "__main__":
    import sys
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    print("Fetching results via Gemini...")
    results = fetch_results_gemini(date_str)
    print("Results:", json.dumps(results, ensure_ascii=False))
    if results:
        save_results(results)
    print("Done")
