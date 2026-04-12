#!/usr/bin/env python3
"""Gen lotto cards per day: หุ้นไทยเย็น, ฮานอยพิเศษ, มาเลย์, ลาวพัฒนา, ลาวสตาร์, ฮานอยปกติ, ฮานอย VIP"""
import subprocess, json, os, base64, datetime, sys, math
from pathlib import Path
from collections import Counter
from itertools import permutations as _perms

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = Path(SCRIPT_DIR).parent
WORKSPACE = "/root/.openclaw/workspace"
CARD_SCRIPT = os.path.join(SCRIPT_DIR, "gen_lotto_card_final.js")
PRED_FILE = os.path.join(SCRIPT_DIR, "lotto_predictions.json")
GENERATE_SCRIPT = "/root/.openclaw/workspace/claw-empire/custom-skills/thai-lottery-expert/scripts/daily_lotto_generate.py"

FONT_REG_PATH = "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"
BG_IMG_PATH = "/root/.openclaw/workspace/football-daily-analyst/football-daily-analyst/assets/char_wide.jpg"
LOGO_PATH = "/root/.openclaw/workspace/claw-empire/custom-skills/thai-lottery-expert/references/logo_huayrich.png"

TH_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

# lotto types to generate (ยกเว้นหุ้นไทยเช้า/เที่ยง/บ่าย และหวยหุ้นนอก)
LOTTO_CONFIG = [
    # days: 0=จันทร์ 1=อังคาร 2=พุธ 3=พฤหัส 4=ศุกร์ 5=เสาร์ 6=อาทิตย์ / None=ทุกวัน
    # เฉพาะหวยที่ส่งกลุ่มจริง
    {"type": "หุ้นไทยเย็น",   "key": "stock_evening", "time": "16:30", "lotto_name": "หุ้นไทยเย็น",  "days": None},
    {"type": "ฮานอยพิเศษ",   "key": "hanoi_special", "time": "17:30", "lotto_name": "ฮานอยพิเศษ",  "days": None},
    {"type": "ฮานอยปกติ",    "key": "hanoi",         "time": "18:30", "lotto_name": "ฮานอยปกติ",   "days": None},
    {"type": "ฮานอย VIP",    "key": "hanoi_vip",     "time": "19:30", "lotto_name": "ฮานอย VIP",   "days": None},
    {"type": "ลาวพัฒนา",     "key": "laos_patthana", "time": "18:30", "lotto_name": "ลาวพัฒนา",    "days": [0,2,4]},  # จ พ ศ
    {"type": "ลาวกาชาด",     "key": "laos_kachad",   "time": "18:30", "lotto_name": "ลาวกาชาด",    "days": [1]},      # อ
    {"type": "ลาว VIP",      "key": "laos_vip",      "time": "18:30", "lotto_name": "ลาว VIP",     "days": [3]},      # พฤ
    {"type": "ลาวสามัคคี",   "key": "laos_samakki",  "time": "18:30", "lotto_name": "ลาวสามัคคี",  "days": [5]},      # ส
    {"type": "ลาวสตาร์",     "key": "laos_star",     "time": "18:30", "lotto_name": "ลาวสตาร์",    "days": None},
    # หวยไทย — gen เฉพาะช่วงใกล้วันออก (1 และ 16)
    {"type": "หวยรัฐบาลไทย", "key": "thai_gov",  "time": "15:30", "lotto_name": "หวยรัฐบาลไทย", "days": None, "near_draw": True},
    {"type": "หวยออมสิน",    "key": "thai_gsb",  "time": "10:00", "lotto_name": "หวยออมสิน",    "days": None, "near_draw": True},
    {"type": "หวย ธกส.",     "key": "thai_baac", "time": "10:05", "lotto_name": "หวย ธกส.",     "days": None, "near_draw": True},
]


def today_th():
    # ใช้ BKK timezone (UTC+7)
    import time as _time
    ts = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    d = ts.date()
    return f"{TH_DAYS[d.weekday()]} {d.strftime('%-d/%m/%Y')}"


def load_fonts_and_bg():
    font_reg = base64.b64encode(open(FONT_REG_PATH, "rb").read()).decode()
    font_bold = base64.b64encode(open(FONT_BOLD_PATH, "rb").read()).decode()
    bg_img = base64.b64encode(open(BG_IMG_PATH, "rb").read()).decode()
    logo_img = base64.b64encode(open(LOGO_PATH, "rb").read()).decode() if os.path.exists(LOGO_PATH) else ""
    logo_mime = "image/png" if LOGO_PATH.endswith(".png") else "image/jpeg"
    return font_reg, font_bold, bg_img, logo_img, logo_mime


def get_predictions(target_date):
    """Run daily_lotto_generate.py and parse output"""
    r = subprocess.run(
        ["python3", GENERATE_SCRIPT, "--date", target_date, "--save"],
        capture_output=True, text=True,
        cwd=os.path.dirname(GENERATE_SCRIPT)
    )
    # Also read the output JSON
    out_file = os.path.join(os.path.dirname(GENERATE_SCRIPT), "..", "data", "daily_lotto_output.json")
    if os.path.exists(out_file):
        with open(out_file) as f:
            return json.load(f)
    return None


def _make_key_digits(numbers):
    """หา 5 digits สำคัญจาก running + 3_digit + 2_digit"""
    from collections import Counter
    cnt = Counter()
    # running digits มีน้ำหนักสูง
    for d in numbers.get("running", []):
        cnt[str(d)] += 5
    # digits จาก 2_digit
    for n in numbers.get("2_digit", []):
        for d in str(n).zfill(2):
            cnt[d] += 2
    # digits จาก 3_digit
    for n in numbers.get("3_digit", []):
        for d in str(n).zfill(3):
            cnt[d] += 1
    key = [d for d, _ in cnt.most_common(5)]
    while len(key) < 5:
        key.append("0")
    return key[:5]

def _make_pairs_2d(key_digits):
    """เอา 3 digits หลัก + สลับทุกแบบ (swap) ให้ครบ 7 ตัว"""
    top3 = key_digits[:3]
    seen = set()
    pairs = []
    # ทุก pair สลับไปมา: 53, 35, 51, 15, 31, 13, 55, 33, 11
    for d1 in top3:
        for d2 in top3:
            p = d1 + d2
            if p not in seen:
                pairs.append(p)
                seen.add(p)
            # swap
            ps = d2 + d1
            if ps not in seen:
                pairs.append(ps)
                seen.add(ps)
    return pairs[:7]

def _make_combos_3d(key_digits):
    """permutations 3-digit จาก top 3 digits"""
    from itertools import permutations as _perms
    k3 = key_digits[:3]
    seen, result = set(), []
    for p in _perms(k3):
        s = "".join(p)
        if s not in seen:
            result.append(s)
            seen.add(s)
    return result

def gen_card(font_reg, font_bold, bg_img, lotto_cfg, numbers, date_str, logo_img="", logo_mime="image/png"):
    """Generate a single lotto card"""
    output_path = f"{WORKSPACE}/card_lotto_{lotto_cfg['key']}.png"

    data = {
        "brand": "บ้านหวย888",
        "lotto_name": lotto_cfg["lotto_name"],
        "date": f"{date_str} | {lotto_cfg['time']}",
        "grid": _make_key_digits(numbers),
        "run1": numbers["running"][0],
        "run2": numbers["running"][1] if len(numbers["running"]) > 1 else numbers["running"][0],
        "nums2": _make_pairs_2d(_make_key_digits(numbers))[:7],
        "nums3": _make_combos_3d(_make_key_digits(numbers))[:3],
        "output": output_path,
    }

    args_payload = {
        "fontReg": font_reg,
        "fontBold": font_bold,
        "bgImg": bg_img,
        "logoImg": logo_img,
        "logoMime": logo_mime,
        "data": data,
    }

    with open("/tmp/lotto_card_args.json", "w") as f:
        json.dump(args_payload, f, ensure_ascii=False)

    r = subprocess.run(
        ["node", CARD_SCRIPT],
        capture_output=True, text=True, timeout=30
    )

    if r.returncode == 0 and os.path.exists(output_path):
        print(f"✅ {lotto_cfg['lotto_name']} → {output_path}")
        return output_path
    else:
        print(f"❌ {lotto_cfg['lotto_name']}: {r.stderr[:200]}")
        return None


def save_predictions(predictions_map, target_date):
    existing = {}
    if os.path.exists(PRED_FILE):
        with open(PRED_FILE) as f:
            existing = json.load(f)
    existing[target_date] = predictions_map
    with open(PRED_FILE, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    # Save separate file for daily tracking
    pred_dir = BASE_DIR / "predictions"
    pred_dir.mkdir(exist_ok=True)
    daily_file = pred_dir / f"predictions_{target_date}.json"
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(predictions_map, f, ensure_ascii=False, indent=2)
    
    print(f"💾 predictions saved: {target_date}")


###############################################################################
# 15-formula prediction helpers
###############################################################################

def get_prev_result(lotto_key, date_str):
    """ดึงผลงวดก่อนหน้าจาก guru-huay.com scraper — return dict {3_digit, 2_top, 2_bottom} or None"""
    try:
        sys.path.insert(0, "/root")
        from lotto_scraper import fetch_today_results as _fetch_today
        results = _fetch_today() or {}
        # ลอง match key ตรง
        if lotto_key in results and isinstance(results[lotto_key], dict):
            return results[lotto_key]
        # fallback: ลองจับคู่ key
        key_map = {
            "hanoi_special": "hanoi_special",
            "hanoi": "hanoi",
            "hanoi_vip": "hanoi_vip",
            "laos_patthana": "laos_patthana",
        }
        mapped = key_map.get(lotto_key)
        if mapped and mapped in results and isinstance(results[mapped], dict):
            return results[mapped]
    except Exception as e:
        print(f"  ⚠️ get_prev_result({lotto_key}, {date_str}): {e}")
    return None


def run_formula(prev_result, date_num):
    """รัน 15 สูตรจาก daily_lotto_generate.py logic — return dict compatible with prediction format"""
    # parse prev result
    prev_3top = int(prev_result.get("3_digit", "0") or "0")
    prev_2top = int(prev_result.get("2_top", str(prev_3top % 100)) or "0")
    prev_2bot = int(prev_result.get("2_bottom", "0") or "0")

    try:
        _generate_path = "/root/.openclaw/workspace/claw-empire/custom-skills/thai-lottery-expert/scripts"
        if _generate_path not in sys.path:
            sys.path.insert(0, _generate_path)
        from daily_lotto_generate import generate as _gen_func
        # generate() prints + writes /tmp/lottery_prediction_*.json
        _gen_func(prev_3top=prev_3top, prev_2top=prev_2top, prev_2bot=prev_2bot, date_num=date_num)
        # read output
        _now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        _pred_file = f"/tmp/lottery_prediction_{_now.strftime('%Y%m%d')}.json"
        if os.path.exists(_pred_file):
            with open(_pred_file) as _f:
                return json.load(_f)
    except Exception as e:
        print(f"  ⚠️ run_formula import/run failed: {e}")

    # inline fallback: replicate core formulas
    def _f1(t2, b2): return [(t2 + b2) // 2]
    def _f3(t2, b2): return [(t2 * b2) % 100]
    def _f4(t2, b2): return [((t2 + b2) * 2) % 100]
    def _f5(t3, b2): return [int(f"{t3 // 100}{b2 % 10}")]
    def _f6(t2): return [(t2 ** 2) % 100]
    def _f7(b2): return [(b2 ** 2) % 100]
    def _f8(t2, b2, dn): return [(t2 + b2 + dn) % 100]
    def _f9(t3):
        s = sum(int(d) for d in str(t3).zfill(3))
        return [s if s < 100 else s % 100]
    def _f14(t2): return [(t2 * 3) % 100]
    def _f15(b2): return [math.ceil(b2 / 2)]

    all_2d = []
    for fn in [
        _f1(prev_2top, prev_2bot), _f3(prev_2top, prev_2bot),
        _f4(prev_2top, prev_2bot), _f5(prev_3top, prev_2bot),
        _f6(prev_2top), _f7(prev_2bot),
        _f8(prev_2top, prev_2bot, date_num),
        _f9(prev_3top), _f14(prev_2top), _f15(prev_2bot),
    ]:
        all_2d.extend(fn)

    # rood 19
    center = (prev_3top // 10) % 10
    for i in range(10):
        all_2d.append(int(f"{center}{i}"))
        all_2d.append(int(f"{i}{center}"))

    run_nums = []
    dc = Counter()
    for n in all_2d:
        for d in str(n).zfill(2):
            dc[d] += 1
    run_nums = [d for d, _ in dc.most_common(2)]

    c2 = Counter(str(n).zfill(2) for n in all_2d)
    top_picks = [num for num, _ in c2.most_common(6)]

    key_digits = [d for d, _ in dc.most_common(5)]
    while len(key_digits) < 5:
        key_digits.append("0")

    pairs_2d, seen = [], set()
    for d1 in key_digits:
        for d2 in key_digits:
            for p in (d1 + d2, d2 + d1):
                if p not in seen:
                    pairs_2d.append(p)
                    seen.add(p)

    combos_3d, seen3 = [], set()
    for p in _perms(key_digits[:3]):
        s = "".join(p)
        if s not in seen3:
            combos_3d.append(s)
            seen3.add(s)

    return {
        "top_picks": top_picks,
        "run_numbers": run_nums,
        "key_digits": key_digits,
        "pairs_2d": pairs_2d,
        "combos_3d": combos_3d,
    }


def main():
    # BKK timezone (UTC+7)
    target_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    date_str = today_th()

    print(f"🎰 Gen lotto cards for {date_str}")

    # Step 1: ใช้ weekday logic เป็นหลัก (chokdee99 ไม่ครอบคลุมหวยต่างประเทศ)
    today_wd = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).weekday()
    today_keys = {cfg["key"] for cfg in LOTTO_CONFIG
                  if cfg.get("days") is None or today_wd in (cfg.get("days") or [])}
    # เพิ่ม chokdee99 schedule (ถ้าได้) เป็น supplement
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from chokdee99_schedule import get_today_lotteries
        today_schedule = get_today_lotteries()
        extra_keys = {l["key"] for l in today_schedule}
        today_keys = today_keys | extra_keys
        print(f"📅 chokdee99 วันนี้: {', '.join(l['name'] for l in today_schedule)}")
    except Exception as e:
        print(f"⚠️ chokdee99 schedule ไม่ได้ ({e}) — ใช้ weekday logic")

    # Step 2: get predictions
    pred_data = get_predictions(target_date)
    pred_lookup = {}
    if pred_data:
        for item in pred_data.get("lotteries", []):
            pred_lookup[item["lottery_type"]] = item["numbers"]

    # Load fonts/bg once
    font_reg, font_bold, bg_img, logo_img, logo_mime = load_fonts_and_bg()

    cards = []
    predictions_map = {}

    # Step 3: gen card เฉพาะหวยที่มีวันนี้
    today_day = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).day
    # หวยรัฐบาลออกวันที่ 1 และ 16 — gen เฉพาะวันนั้น
    near_thai_draw = today_day == 1 or today_day == 16

    for cfg in LOTTO_CONFIG:
        if cfg["key"] not in today_keys:
            continue
        # หวยไทย gen เฉพาะช่วงใกล้วันออก
        if cfg.get("near_draw") and not near_thai_draw:
            print(f"⏭️ {cfg['lotto_name']} ยังไม่ใกล้วันออก (วันที่ {today_day})")
            continue
        numbers = pred_lookup.get(cfg["type"])
        if not numbers:
            # ดึงผลงวดก่อนหน้า + คำนวณด้วย 15 สูตร
            prev_date = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            prev_result = get_prev_result(cfg["key"], prev_date)
            if prev_result:
                pred_json = run_formula(prev_result, today_day)
                numbers = {
                    "3_digit": pred_json["combos_3d"][:3],
                    "2_digit": pred_json["pairs_2d"][:3],
                    "running": pred_json["run_numbers"],
                }
                print(f"  🔮 {cfg['lotto_name']}: ใช้ 15 สูตร (ref: {prev_result.get('3_digit','?')}/{prev_result.get('2_top','?')}/{prev_result.get('2_bottom','?')})")
            else:
                # fallback random เหมือนเดิม
                import random
                seed = hash(cfg["key"] + target_date) % 99999
                rng = random.Random(seed)
                numbers = {
                    "3_digit": [str(rng.randint(100,999)), str(rng.randint(100,999)), str(rng.randint(100,999))],
                    "2_digit": [str(rng.randint(0,99)).zfill(2) for _ in range(3)],
                    "running": [str(rng.randint(0,9)), str(rng.randint(0,9))],
                }
                print(f"  ⚡ {cfg['lotto_name']}: fallback random (ไม่มีผลงวดก่อน)")

        # Self-improve: จัดลำดับเลขตาม weight ถ้ามี
        try:
            from self_improve_lotto import rank_numbers_by_weight
            numbers = rank_numbers_by_weight(numbers)
        except Exception as e:
            pass  # ไม่มี weight ก็ใช้เลขเดิม

        # คำนวณ nums2 (7 เลข 2ตัวสลับ) และ nums3 (3 เลข 3ตัว)
        key_digits = _make_key_digits(numbers)
        nums2 = _make_pairs_2d(key_digits)[:7]
        nums3 = _make_combos_3d(key_digits)[:3]

        path = gen_card(font_reg, font_bold, bg_img, cfg, numbers, date_str, logo_img, logo_mime)
        if path:
            cards.append(path)
            predictions_map[cfg["key"]] = {
                "3_digit": numbers["3_digit"],
                "2_digit": numbers["2_digit"],
                "running": numbers["running"],
                "nums2": nums2,
                "nums3": nums3,
            }

    # Save predictions
    save_predictions(predictions_map, target_date)

    print(f"\n🎯 Generated {len(cards)}/{len(LOTTO_CONFIG)} cards")
    return cards


if __name__ == "__main__":
    main()
