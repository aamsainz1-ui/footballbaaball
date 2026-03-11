#!/usr/bin/env python3
"""Gen 4 lotto cards per day: หุ้นไทยเย็น, ฮานอยพิเศษ, ฮานอยปกติ, ลาวพัฒนา"""
import subprocess, json, os, base64, datetime, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = "/root/.openclaw/workspace"
CARD_SCRIPT = os.path.join(SCRIPT_DIR, "gen_lotto_card_final.js")
PRED_FILE = os.path.join(SCRIPT_DIR, "lotto_predictions.json")
GENERATE_SCRIPT = "/usr/lib/node_modules/openclaw/skills/thai-lottery-expert/scripts/daily_lotto_generate.py"

FONT_REG_PATH = "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"
BG_IMG_PATH = "/tmp/char_wide.jpg"

TH_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

# 4 lotto types to generate
LOTTO_CONFIG = [
    {"type": "หุ้นไทยเย็น", "key": "stock_evening", "time": "16:30", "brand": "บ้านหวย888", "lotto_name": "🇹🇭 หุ้นไทยเย็น"},
    {"type": "ฮานอยพิเศษ", "key": "hanoi_special", "time": "17:30", "brand": "บ้านหวย888", "lotto_name": "🇻🇳 ฮานอยพิเศษ"},
    {"type": "ฮานอยปกติ",  "key": "hanoi",         "time": "18:30", "brand": "บ้านหวย888", "lotto_name": "🇻🇳 ฮานอยปกติ"},
    {"type": "ลาวพัฒนา",   "key": "laos",          "time": "18:30", "brand": "บ้านหวย888", "lotto_name": "🇱🇦 ลาวพัฒนา"},
]


def today_th():
    d = datetime.date.today()
    return f"{TH_DAYS[d.weekday()]} {d.strftime('%-d/%m/%Y')}"


def load_fonts_and_bg():
    font_reg = base64.b64encode(open(FONT_REG_PATH, "rb").read()).decode()
    font_bold = base64.b64encode(open(FONT_BOLD_PATH, "rb").read()).decode()
    bg_img = base64.b64encode(open(BG_IMG_PATH, "rb").read()).decode()
    return font_reg, font_bold, bg_img


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


def gen_card(font_reg, font_bold, bg_img, lotto_cfg, numbers, date_str):
    """Generate a single lotto card"""
    output_path = f"{WORKSPACE}/card_lotto_{lotto_cfg['key']}.png"

    data = {
        "brand": lotto_cfg["brand"],
        "lotto_name": lotto_cfg["lotto_name"],
        "date": f"{date_str} | {lotto_cfg['time']}",
        "grid": [
            int(numbers["3_digit"][0][0]),
            int(numbers["3_digit"][0][1]),
            int(numbers["3_digit"][0][2]),
            int(numbers["3_digit"][1][0]),
            int(numbers["3_digit"][1][1]),
        ],
        "run1": numbers["running"][0],
        "run2": numbers["running"][1] if len(numbers["running"]) > 1 else numbers["running"][0],
        "nums2": numbers["2_digit"],
        "nums3": numbers["3_digit"],
        "output": output_path,
    }

    args_payload = {
        "fontReg": font_reg,
        "fontBold": font_bold,
        "bgImg": bg_img,
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
    print(f"💾 predictions saved: {target_date}")


def main():
    target_date = datetime.date.today().strftime("%Y-%m-%d")
    date_str = today_th()

    print(f"🎰 Gen 4 lotto cards for {date_str}")

    # Get predictions from daily_lotto_generate
    pred_data = get_predictions(target_date)
    if not pred_data:
        print("❌ Failed to get predictions")
        sys.exit(1)

    # Build lookup by type
    pred_lookup = {}
    for item in pred_data.get("lotteries", []):
        pred_lookup[item["lottery_type"]] = item["numbers"]

    # Load fonts/bg once
    font_reg, font_bold, bg_img = load_fonts_and_bg()

    cards = []
    predictions_map = {}

    for cfg in LOTTO_CONFIG:
        numbers = pred_lookup.get(cfg["type"])
        if not numbers:
            print(f"⚠️ No predictions for {cfg['type']}, skipping")
            continue

        path = gen_card(font_reg, font_bold, bg_img, cfg, numbers, date_str)
        if path:
            cards.append(path)
            predictions_map[cfg["key"]] = {
                "3_digit": numbers["3_digit"],
                "2_digit": numbers["2_digit"],
                "running": numbers["running"],
            }

    # Save predictions
    save_predictions(predictions_map, target_date)

    print(f"\n🎯 Generated {len(cards)}/4 cards")
    return cards


if __name__ == "__main__":
    main()
