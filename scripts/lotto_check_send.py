#!/usr/bin/env python3
"""เช็คผลหวยแต่ละรอบ → เทียบกับ predictions → gen card สถิติ → ส่งกลุ่ม"""
import sys, os, subprocess, json, datetime, requests, base64

LOTTO_TOKEN = "8077699310:AAEJHmRk9pxAdUZv98PfazXhqcoz-hxJZBY"
GROUP_ID    = "-1003869825051"
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
WORKSPACE   = "/root/.openclaw/workspace"
PRED_FILE   = os.path.join(SCRIPT_DIR, "lotto_predictions.json")
STATS_FILE  = os.path.join(SCRIPT_DIR, "lotto_stats.json")
STATS_CARD_SCRIPT = "/tmp/gen_lotto_stats_card.js"
FONT_REG    = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf","rb").read()).decode()
FONT_BOLD   = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf","rb").read()).decode()

LOTTO_MAP = {
    "hanoi_special": "ฮานอยพิเศษ",
    "hanoi":         "ฮานอยปกติ",
    "hanoi_vip":     "ฮานอย VIP",
    "laos":          "ลาวปกติ",
}

def gemini_fetch(lotto_name, date_str):
    q = f"ผล{lotto_name}วันที่ {date_str} 3ตัวบน=XXX 2ตัวล่าง=XX ตอบแค่ตัวเลข"
    try:
        r = subprocess.run(["gemini","--sandbox","false","--yolo","--prompt",q],
            capture_output=True, text=True, timeout=40)
        return r.stdout.strip()
    except: return ""

def parse_result(text):
    import re
    m3 = re.search(r'3ตัวบน[=:\s]*([0-9]{3})', text)
    m2 = re.search(r'2ตัวล่าง[=:\s]*([0-9]{2})', text)
    if not m3: m3 = re.search(r'\b([0-9]{3})\b', text)
    if not m2: m2 = re.search(r'\b([0-9]{2})\b', text)
    return m3.group(1) if m3 else None, m2.group(1) if m2 else None

def load_predictions():
    if os.path.exists(PRED_FILE):
        with open(PRED_FILE) as f:
            return json.load(f)
    return {}

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return []

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def calc_stats(stats, lotto_type, days):
    """คำนวณ stats X วันย้อนหลังสำหรับ lotto_type"""
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    entries = [s for s in stats if s["lotto"] == lotto_type and s["date"] >= cutoff]
    total = len(entries)
    correct_2bot = sum(1 for e in entries if e.get("hit_2bot"))
    pct = round(correct_2bot / total * 100) if total > 0 else 0
    return {"correct_2bot": correct_2bot, "total": total, "pct": pct}

def record_stats(lotto_type, pred, actual):
    """บันทึกผลเทียบลง lotto_stats.json"""
    stats = load_stats()
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    hit_3top = pred.get("3top") == actual.get("3top")
    hit_2bot = pred.get("2bot") == actual.get("2bot")

    entry = {
        "date": today_str,
        "lotto": lotto_type,
        "predicted_3top": pred.get("3top", "?"),
        "actual_3top": actual.get("3top", "?"),
        "predicted_2bot": pred.get("2bot", "?"),
        "actual_2bot": actual.get("2bot", "?"),
        "hit_3top": hit_3top,
        "hit_2bot": hit_2bot,
    }

    # Replace existing entry for same date+lotto
    stats = [s for s in stats if not (s["date"] == today_str and s["lotto"] == lotto_type)]
    stats.append(entry)
    save_stats(stats)

    return hit_3top, hit_2bot, stats

def gen_stats_card(lotto_type, lotto_name, pred, actual, hit_3top, hit_2bot, stats, output):
    """gen card สถิติด้วย gen_lotto_stats_card.js"""
    today = datetime.date.today().strftime("%-d/%m/%Y")
    stats_7d = calc_stats(stats, lotto_type, 7)
    stats_30d = calc_stats(stats, lotto_type, 30)

    payload = {
        "date": today,
        "lotto_name": lotto_name,
        "pred": {"3top": pred.get("3top","?"), "2bot": pred.get("2bot","?")},
        "actual": {"3top": actual.get("3top","?"), "2bot": actual.get("2bot","?")},
        "hit_3top": hit_3top,
        "hit_2bot": hit_2bot,
        "stats_7d": stats_7d,
        "stats_30d": stats_30d,
        "output": output,
    }

    r = subprocess.run(
        ["node", STATS_CARD_SCRIPT, FONT_REG, FONT_BOLD, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"stats card error: {r.stderr[:300]}")
        return None
    return output

def send_photo(path, caption):
    with open(path,"rb") as f:
        resp = requests.post(f"https://api.telegram.org/bot{LOTTO_TOKEN}/sendPhoto",
            data={"chat_id":GROUP_ID,"caption":caption},
            files={"photo":f}, timeout=15)
    print(f"telegram send: {resp.status_code}")

def check(lotto_type, mock_data=None):
    today = datetime.date.today()
    date_str = today.strftime("%-d %B %Y")
    today_str = today.strftime("%Y-%m-%d")
    lotto_name = LOTTO_MAP.get(lotto_type, lotto_type)

    # Get actual results
    if mock_data:
        top3, bot2 = mock_data["3top"], mock_data["2bot"]
    else:
        print(f"Checking {lotto_name}...")
        text = gemini_fetch(lotto_name, date_str)
        top3, bot2 = parse_result(text)

    if not top3:
        print(f"No result found for {lotto_name}")
        return

    actual = {"3top": top3, "2bot": bot2}

    # Load prediction
    preds = load_predictions()
    pred = preds.get(today_str, {}).get(lotto_type, {"3top": "?", "2bot": "?"})

    # Record stats
    hit_3top, hit_2bot, all_stats = record_stats(lotto_type, pred, actual)
    print(f"{lotto_name}: ใบ้ {pred.get('3top','?')}/{pred.get('2bot','?')} vs ออก {top3}/{bot2} | 3top:{'WIN' if hit_3top else 'MISS'} 2bot:{'WIN' if hit_2bot else 'MISS'}")

    # Gen result card (existing)
    result_output = f"{WORKSPACE}/card_result_{lotto_type}.png"
    gen_result_card(lotto_type, lotto_name, pred, actual, result_output)

    # Gen stats card
    stats_output = f"{WORKSPACE}/card_lotto_stats_{lotto_type}.png"
    gen_stats_card(lotto_type, lotto_name, pred, actual, hit_3top, hit_2bot, all_stats, stats_output)

    if not mock_data:
        # Send result card
        caption = f"ผล{lotto_name}\nออก: {top3} / {bot2}"
        if hit_2bot:
            caption += "\n2 ตัวล่าง WIN!"
        send_photo(result_output, caption)

        # Send stats card
        stats_7d = calc_stats(all_stats, lotto_type, 7)
        stats_caption = f"สถิติ{lotto_name}\n7 วัน: {stats_7d['correct_2bot']}/{stats_7d['total']} ({stats_7d['pct']}%)"
        send_photo(stats_output, stats_caption)

    print(f"done: {lotto_name}")

def gen_result_card(lotto_type, lotto_name, pred, actual, output):
    hit3 = pred.get("3top") == actual.get("3top")
    hit2 = pred.get("2bot") == actual.get("2bot")
    today = datetime.date.today().strftime("%-d/%m/%Y")

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@font-face{{font-family:'NT';src:url('data:font/ttf;base64,{FONT_REG}') format('truetype');font-weight:400}}
@font-face{{font-family:'NT';src:url('data:font/ttf;base64,{FONT_BOLD}') format('truetype');font-weight:700}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:540px;font-family:'NT',sans-serif;background:#08080f}}
.card{{background:#0c0c1e;overflow:hidden}}
.header{{background:linear-gradient(135deg,#1a0533,#3d0066);padding:18px 24px;border-bottom:3px solid #bf00ff;display:flex;justify-content:space-between;align-items:center}}
.brand{{font-size:22px;font-weight:700;color:#e040fb;letter-spacing:2px}}
.sub{{font-size:11px;color:#9c6aaa;margin-top:2px}}
.badge{{background:rgba(224,64,251,0.15);border:1px solid #bf00ff;color:#e040fb;font-size:11px;font-weight:700;padding:5px 12px;border-radius:5px}}
.body{{padding:20px 24px}}
.lotto-name{{font-size:14px;font-weight:700;color:#d1a0e0;margin-bottom:16px;text-align:center}}
.nums-row{{display:flex;gap:12px;margin-bottom:16px}}
.num-box{{flex:1;border-radius:10px;padding:14px;text-align:center}}
.num-box.pred{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1)}}
.num-box.actual{{background:rgba(224,64,251,0.08);border:2px solid #9c27b0}}
.num-label{{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.num-val{{font-size:32px;font-weight:700;color:#fff;line-height:1}}
.result-row{{display:flex;gap:10px}}
.res-box{{flex:1;border-radius:8px;padding:12px;text-align:center}}
.res-win{{background:rgba(0,200,83,0.12);border:1px solid #00c853}}
.res-loss{{background:rgba(213,0,0,0.12);border:1px solid #d50000}}
.res-label{{font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}}
.res-val{{font-size:20px;font-weight:700}}
.footer{{background:#06060f;padding:10px 24px;text-align:center;border-top:1px solid rgba(255,255,255,0.04)}}
.footer-text{{font-size:10px;color:#333}}
</style></head><body><div class="card">
<div class="header">
  <div><div class="brand">บ้านหวย888</div><div class="sub">ผลตรวจหวย</div></div>
  <div class="badge">{today}</div>
</div>
<div class="body">
  <div class="lotto-name">{lotto_name}</div>
  <div class="nums-row">
    <div class="num-box pred"><div class="num-label">ใบ้ไป</div><div class="num-val">{pred.get('3top','?')}</div></div>
    <div class="num-box actual"><div class="num-label">ออกจริง</div><div class="num-val">{actual.get('3top','?')}</div></div>
  </div>
  <div class="nums-row">
    <div class="num-box pred"><div class="num-label">2 ตัวล่าง (ใบ้)</div><div class="num-val">{pred.get('2bot','?')}</div></div>
    <div class="num-box actual"><div class="num-label">2 ตัวล่าง (จริง)</div><div class="num-val">{actual.get('2bot','?')}</div></div>
  </div>
  <div class="result-row">
    <div class="res-box {'res-win' if hit3 else 'res-loss'}">
      <div class="res-label" style="color:{'#00c853' if hit3 else '#d50000'}">3 ตัวบน</div>
      <div class="res-val" style="color:{'#00c853' if hit3 else '#d50000'}">{'WIN' if hit3 else 'MISS'}</div>
    </div>
    <div class="res-box {'res-win' if hit2 else 'res-loss'}">
      <div class="res-label" style="color:{'#00c853' if hit2 else '#d50000'}">2 ตัวล่าง</div>
      <div class="res-val" style="color:{'#00c853' if hit2 else '#d50000'}">{'WIN' if hit2 else 'MISS'}</div>
    </div>
  </div>
</div>
<div class="footer"><div class="footer-text">บ้านหวย888 · ตรวจผลอัตโนมัติ</div></div>
</div></body></html>"""

    with open("/tmp/result_card.html", "w") as f:
        f.write(html)

    js = f"""const {{chromium}} = require('/usr/lib/node_modules/openclaw/node_modules/playwright-core');
(async()=>{{
  const b = await chromium.launch({{headless:true,args:['--no-sandbox','--disable-gpu']}});
  const p = await b.newPage();
  await p.setViewportSize({{width:540,height:600}});
  await p.setContent(require('fs').readFileSync('/tmp/result_card.html','utf8'),{{waitUntil:'load'}});
  await p.waitForTimeout(300);
  await (await p.$('.card')).screenshot({{path:'{output}'}});
  await b.close();
  console.log('done');
}})();"""
    with open("/tmp/result_card.js","w") as f:
        f.write(js)
    subprocess.run(["node","/tmp/result_card.js"], capture_output=True)

if __name__ == "__main__":
    lotto = sys.argv[1] if len(sys.argv) > 1 else "hanoi"

    # Mock mode for testing
    if "--mock" in sys.argv:
        # Create mock prediction
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        preds = load_predictions()
        if today_str not in preds or lotto not in preds.get(today_str, {}):
            preds.setdefault(today_str, {})[lotto] = {"3top": "165", "2bot": "07", "run": "0"}
            with open(PRED_FILE, "w") as f:
                json.dump(preds, f, ensure_ascii=False, indent=2)
            print(f"Mock prediction saved: {today_str}/{lotto}")

        # Mock actual result (2bot matches for test)
        mock = {"3top": "482", "2bot": "07"}
        check(lotto, mock_data=mock)

        # Copy stats card for test output
        import shutil
        src = f"{WORKSPACE}/card_lotto_stats_{lotto}.png"
        dst = f"{WORKSPACE}/card_lotto_stats_test.png"
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"test output: {dst}")
    else:
        check(lotto)
