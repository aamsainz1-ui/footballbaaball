#!/usr/bin/env python3
"""Auto card generator — วิเคราะห์แล้วเลือก 1 ราคาต่อคู่"""
import urllib.request, json, datetime, subprocess, os, base64, sys

API_KEY = os.environ.get("FOOTBALLDATA_KEY", "0b5856b21f964b398ecc12918f22c7a2")
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"
CARD_SCRIPT = "/tmp/gen_card4.js"
OUTPUT = "/root/.openclaw/workspace/card_auto.png"

TEAM_NAMES = {
    "Arsenal FC": "อาร์เซนอล",
    "Bayer 04 Leverkusen": "เลเวอร์คูเซ่น",
    "Paris Saint-Germain FC": "เปแอสเช",
    "Chelsea FC": "เชลซี",
    "Real Madrid CF": "เรอัล มาดริด",
    "Manchester City FC": "แมนเชสเตอร์ ซิตี้",
    "FK Bodø/Glimt": "โบดอ/กลิมต์",
    "Sporting Clube de Portugal": "สปอร์ติ้ง",
}

def thai(name):
    return TEAM_NAMES.get(name, name)

def fetch_standings(comp_code):
    url = f"https://api.football-data.org/v4/competitions/{comp_code}/standings"
    req = urllib.request.Request(url)
    req.add_header("X-Auth-Token", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        standings = {}
        for group in data.get("standings", []):
            for t in group.get("table", []):
                standings[t["team"]["id"]] = {
                    "pos": t["position"],
                    "pts": t["points"],
                    "gf": t["goalsFor"],
                    "ga": t["goalsAgainst"],
                    "played": t["playedGames"],
                    "won": t["won"],
                }
        return standings
    except:
        return {}

def analyze_pick(home, away, home_id, away_id, standings):
    hs = standings.get(home_id, {})
    as_ = standings.get(away_id, {})

    if not hs or not as_:
        return {"tip": f"{thai(home)} ชนะ", "handicap": "ต่อครึ่ง", "ou": None, "confidence": 65}

    hp = hs.get("played", 1) or 1
    ap = as_.get("played", 1) or 1
    h_avg_gf = hs.get("gf", 0) / hp
    a_avg_gf = as_.get("gf", 0) / ap
    h_pos = hs.get("pos", 10)
    a_pos = as_.get("pos", 10)
    pos_diff = abs(h_pos - a_pos)
    total_avg_goals = h_avg_gf + a_avg_gf

    # เลือก 1 ราคา
    if pos_diff >= 5:
        # ต่างมาก → Handicap
        if a_pos < h_pos:
            stronger = thai(away)
            handicap = f"{stronger} ต่อ 1 ลูก" if pos_diff >= 8 else f"{stronger} ต่อครึ่ง"
        else:
            stronger = thai(home)
            handicap = f"{stronger} ต่อ 1 ลูก" if pos_diff >= 8 else f"{stronger} ต่อครึ่ง"
        conf = min(90, 65 + pos_diff * 2)
        return {"tip": handicap, "handicap": handicap, "ou": None, "confidence": conf}
    else:
        # สูสี → สูง/ต่ำ
        line = 2.5 if total_avg_goals >= 2.5 else 2.0
        direction = "สูง" if total_avg_goals >= line else "ต่ำ"
        ou = f"{direction} {line}"
        conf = min(82, 62 + int(abs(total_avg_goals - line) * 10))
        return {"tip": ou, "handicap": None, "ou": ou, "confidence": conf}

def main():
    today = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/matches?date={today}&competitions=CL,PL,BL1,SA,PD"
    req = urllib.request.Request(url)
    req.add_header("X-Auth-Token", API_KEY)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())

    matches = data.get("matches", [])
    # กรองเฉพาะ UCL ก่อน
    ucl = [m for m in matches if m["competition"]["code"] == "CL"]
    target = ucl if ucl else matches[:5]

    # fetch standings UCL
    standings = fetch_standings("CL") if ucl else {}

    picks = []
    for m in target[:5]:
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        comp = m["competition"]["name"].replace("UEFA Champions League","UCL")
        time_str = m["utcDate"][11:16]
        # +7 Bangkok
        h, mn = int(time_str[:2]), int(time_str[3:])
        h = (h + 7) % 24
        local_time = f"{h:02d}:{mn:02d}"

        pick_data = analyze_pick(home, away, home_id, away_id, standings)
        pick = {
            "home": thai(home),
            "away": thai(away),
            "league": comp,
            "time": local_time,
            "tip": pick_data["tip"],
            "confidence": pick_data["confidence"],
        }
        if pick_data["handicap"]:
            pick["handicap"] = pick_data["handicap"]
        if pick_data["ou"]:
            pick["ou"] = pick_data["ou"]
        picks.append(pick)

    # mark banker = highest confidence
    if picks:
        banker = max(picks, key=lambda x: x["confidence"])
        banker["banker"] = True

    payload = {
        "date": datetime.date.today().strftime("%-d/%m/%Y"),
        "league": "UEFA Champions League",
        "output": OUTPUT,
        "picks": picks,
    }

    font_reg = base64.b64encode(open(FONT_REG,"rb").read()).decode()
    font_bold = base64.b64encode(open(FONT_BOLD,"rb").read()).decode()

    script = "/tmp/gen_card5.js"
    result = subprocess.run(
        ["node", script, font_reg, font_bold, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"done:{OUTPUT}")
    else:
        print("error:", result.stderr[:200])

if __name__ == "__main__":
    main()


def thai_analyst_tip(home, away, home_stats, away_stats, pick_type, pick_val):
    """สร้างคำวิเคราะห์แบบนักวิเคราะห์บอลไทย"""
    h = home_stats or {}
    a = away_stats or {}
    hp = h.get("played", 1) or 1
    ap = a.get("played", 1) or 1
    h_avg = h.get("gf", 0) / hp
    a_avg = a.get("gf", 0) / ap
    h_pos = h.get("pos", 10)
    a_pos = a.get("pos", 10)

    if pick_type == "handicap":
        # ต่อ
        stronger = pick_val.split(" ต่อ")[0]
        is_high = "1 ลูก" in pick_val
        if stronger == home:
            desc = f"{home}เจ้าบ้านฟอร์มดี อันดับ {h_pos} ต่าง {away} อันดับ {a_pos}"
            if is_high:
                return f"{desc} — ต่อ 1 ลูกผ่านได้สบาย"
            else:
                return f"{desc} — ต่อครึ่งน่าเล่น"
        else:
            desc = f"{away}ฟอร์มร้อนแกร่ง อันดับ {a_pos} บุกได้"
            if is_high:
                return f"{desc} — ต่อ 1 ลูกก็ยังเชื่อ"
            else:
                return f"{desc} — ต่อครึ่งผ่านได้"
    else:
        # สูง/ต่ำ
        total = h_avg + a_avg
        if "สูง" in pick_val:
            return f"ทั้งสองทีมบุกได้ ยิงรวมเฉลี่ย {total:.1f} ลูก/นัด — เลือกสูงปลอดภัย"
        else:
            return f"ทั้งสองทีมแน่นรับ ยิงรวมน้อย — เลือกต่ำเซฟกว่า"
