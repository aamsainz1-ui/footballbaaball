"""
 Tip Card Generator — สร้างการ์ดทีเด็ดบอลแชร์ได้
ใช้ Pillow สร้างรูป PNG พร้อมโลโก้ 

Usage:
  python tip_card_gen.py "อาร์เซนอล" "แมนยู" "พรีเมียร์ลีก" "21:00" "เจ้าบ้านเต็ง" "★★★"
  python tip_card_gen.py --from-json analysis.json
"""

import sys, os, io, json, argparse
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

TZ = timezone(timedelta(hours=7))
NOW = datetime.now(TZ)

# Card dimensions (Instagram/LINE friendly)
W, H = 1080, 1350
BG_COLOR = (10, 15, 30)  # Dark navy
ACCENT = (255, 165, 0)   #  orange
WHITE = (255, 255, 255)
GRAY = (150, 160, 180)
GREEN = (34, 197, 94)
RED = (239, 68, 68)
GOLD = (250, 204, 21)

def get_font(size, bold=False):
    """Try to load Thai-compatible font, fallback to default"""
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                pass
    return ImageFont.load_default()

def draw_rounded_rect(draw, xy, radius, fill, outline=None):
    """Draw rounded rectangle"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)

def create_tip_card(home, away, league, kick_time, tip, confidence, extra_info=None, output_path=None):
    """Create a tip card image"""
    img = Image.new('RGB', (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(48, bold=True)
    font_team = get_font(56, bold=True)
    font_league = get_font(32)
    font_time = get_font(36, bold=True)
    font_tip = get_font(40, bold=True)
    font_small = get_font(24)
    font_brand = get_font(44, bold=True)
    font_conf = get_font(60, bold=True)

    y = 40

    # Header bar
    draw_rounded_rect(draw, (0, 0, W, 120), 0, fill=(20, 30, 60))
    draw.text((W//2, 60), "⚽ ทีเด็ดบอลวันนี้", fill=GOLD, font=font_title, anchor="mm")
    y = 130

    # Date
    day_names = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]
    date_str = f"วัน{day_names[NOW.weekday()]}ที่ {NOW.strftime('%d/%m/%Y')}"
    draw.text((W//2, y + 20), date_str, fill=GRAY, font=font_small, anchor="mm")
    y += 60

    # League badge
    draw_rounded_rect(draw, (100, y, W-100, y+50), 25, fill=(30, 45, 80))
    draw.text((W//2, y+25), f"🏆 {league}", fill=WHITE, font=font_league, anchor="mm")
    y += 80

    # VS section
    draw_rounded_rect(draw, (40, y, W-40, y+280), 20, fill=(15, 25, 50), outline=(40, 60, 100))

    # Home team
    draw.text((W//2, y+50), home, fill=WHITE, font=font_team, anchor="mm")

    # VS
    draw_rounded_rect(draw, (W//2-40, y+90, W//2+40, y+140), 20, fill=ACCENT)
    draw.text((W//2, y+115), "VS", fill=BG_COLOR, font=get_font(32, True), anchor="mm")

    # Away team
    draw.text((W//2, y+190), away, fill=WHITE, font=font_team, anchor="mm")

    # Kick time
    draw.text((W//2, y+245), f"⏰ เวลาเตะ {kick_time} น.", fill=GOLD, font=font_time, anchor="mm")
    y += 310

    # Confidence stars
    conf_color = GREEN if "★★★" in confidence else GOLD if "★★" in confidence else RED
    draw_rounded_rect(draw, (200, y, W-200, y+80), 15, fill=(20, 35, 60))
    draw.text((W//2, y+40), confidence, fill=conf_color, font=font_conf, anchor="mm")
    y += 110

    # Tip / prediction
    draw_rounded_rect(draw, (60, y, W-60, y+120), 15, fill=(25, 40, 70), outline=ACCENT)
    draw.text((W//2, y+30), "💡 ทีเด็ด:", fill=ACCENT, font=font_small, anchor="mm")
    draw.text((W//2, y+75), tip, fill=WHITE, font=font_tip, anchor="mm")
    y += 150

    # Extra info (optional)
    if extra_info:
        for line in extra_info[:4]:
            draw.text((W//2, y+10), line, fill=GRAY, font=font_small, anchor="mm")
            y += 35
        y += 20

    # Footer -  branding
    draw_rounded_rect(draw, (0, H-180, W, H), 0, fill=(20, 30, 60))

    # Warning text
    draw.text((W//2, H-155), "⚠️ วิเคราะห์ประกอบการตัดสินใจเท่านั้น", fill=GRAY, font=font_small, anchor="mm")

    # Brand
    draw_rounded_rect(draw, (250, H-120, W-250, H-50), 15, fill=ACCENT)
    draw.text((W//2, H-85), ".com", fill=BG_COLOR, font=font_brand, anchor="mm")

    # Tagline
    draw.text((W//2, H-25), "ฝากถอนออโต้ 24 ชม. 🔥", fill=GOLD, font=font_small, anchor="mm")

    # Save
    if not output_path:
        safe_name = f"{home}_vs_{away}".replace(" ", "_")
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"card_{safe_name}.png")

    img.save(output_path, 'PNG', quality=95)
    print(f"✅ การ์ดทีเด็ดบันทึกที่: {output_path}", file=sys.stderr)
    return output_path

def create_parlay_card(matches, output_path=None):
    """Create a parlay (step) tip card with multiple matches"""
    img = Image.new('RGB', (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = get_font(44, bold=True)
    font_match = get_font(32, bold=True)
    font_small = get_font(24)
    font_brand = get_font(40, bold=True)
    font_conf = get_font(36, bold=True)

    # Header
    draw_rounded_rect(draw, (0, 0, W, 120), 0, fill=(20, 30, 60))
    draw.text((W//2, 60), f"🎯 ทีเด็ดสเต็ป {len(matches)} คู่", fill=GOLD, font=font_title, anchor="mm")

    y = 140
    day_names = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]
    draw.text((W//2, y), f"วัน{day_names[NOW.weekday()]}ที่ {NOW.strftime('%d/%m/%Y')}", fill=GRAY, font=font_small, anchor="mm")
    y += 50

    for i, m in enumerate(matches[:5]):
        draw_rounded_rect(draw, (40, y, W-40, y+160), 15, fill=(15, 25, 50), outline=(40, 60, 100))

        # Match number
        draw_rounded_rect(draw, (60, y+10, 110, y+45), 10, fill=ACCENT)
        draw.text((85, y+27), f"#{i+1}", fill=BG_COLOR, font=font_small, anchor="mm")

        # Teams
        home = m.get('home', '?')
        away = m.get('away', '?')
        draw.text((W//2, y+35), f"{home} vs {away}", fill=WHITE, font=font_match, anchor="mm")

        # League + time
        league = m.get('league', '')
        time_str = m.get('time', '')
        draw.text((W//2, y+75), f"🏆 {league}  ⏰ {time_str}", fill=GRAY, font=font_small, anchor="mm")

        # Tip
        tip = m.get('tip', '')
        conf = m.get('confidence', '★★')
        conf_color = GREEN if "★★★" in conf else GOLD if "★★" in conf else RED
        draw.text((W//2, y+115), f"💡 {tip}", fill=ACCENT, font=font_small, anchor="mm")
        draw.text((W-80, y+115), conf, fill=conf_color, font=font_conf, anchor="mm")

        y += 180

    # Footer
    draw_rounded_rect(draw, (0, H-150, W, H), 0, fill=(20, 30, 60))
    draw.text((W//2, H-125), "⚠️ เดิมพันอย่างมีสติ", fill=GRAY, font=font_small, anchor="mm")
    draw_rounded_rect(draw, (300, H-95, W-300, H-40), 12, fill=ACCENT)
    draw.text((W//2, H-67), ".com", fill=BG_COLOR, font=font_brand, anchor="mm")
    draw.text((W//2, H-15), "ฝากถอนออโต้ 24 ชม. 🔥", fill=GOLD, font=font_small, anchor="mm")

    if not output_path:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_parlay.png")

    img.save(output_path, 'PNG', quality=95)
    print(f"✅ การ์ดสเต็ปบันทึกที่: {output_path}", file=sys.stderr)
    return output_path


if __name__ == "__main__":
    # Fix encoding
    if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description=" Tip Card Generator")
    parser.add_argument("--single", nargs=6, metavar=("HOME", "AWAY", "LEAGUE", "TIME", "TIP", "CONF"),
                        help="สร้างการ์ดเดี่ยว: ทีมเหย้า ทีมเยือน ลีก เวลา ทีเด็ด ความมั่นใจ")
    parser.add_argument("--parlay-json", type=str, help="สร้างการ์ดสเต็ปจาก JSON file")
    parser.add_argument("--demo", action="store_true", help="สร้างการ์ดตัวอย่าง")
    args = parser.parse_args()

    if args.single:
        create_tip_card(*args.single)
    elif args.parlay_json:
        with open(args.parlay_json, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        create_parlay_card(matches)
    elif args.demo:
        # Demo single card
        path1 = create_tip_card(
            "อาร์เซนอล", "แมนยู", "พรีเมียร์ลีก 🏴",
            "21:00", "เจ้าบ้านเต็งหนัก", "★★★",
            extra_info=["ฟอร์ม 5 นัด: 🟢🟢🟢🟡🟢", "สถิติเจอกัน: อาร์เซนอล ชนะ 4/5", "อาร์เซนอล ยิงเฉลี่ย 2.1 ลูก/นัด"]
        )
        # Demo parlay card
        path2 = create_parlay_card([
            {"home": "อาร์เซนอล", "away": "แมนยู", "league": "พรีเมียร์ลีก", "time": "21:00", "tip": "เจ้าบ้านชนะ", "confidence": "★★★"},
            {"home": "บาร์ซ่า", "away": "เรอัลมาดริด", "league": "ลาลีกา", "time": "02:00", "tip": "สูง 2.5", "confidence": "★★"},
            {"home": "บาเยิร์น", "away": "ดอร์ทมุนด์", "league": "บุนเดสลีกา", "time": "23:30", "tip": "เจ้าบ้าน -1", "confidence": "★★★"},
        ])
        print(f"Demo cards: {path1}, {path2}")
    else:
        parser.print_help()
