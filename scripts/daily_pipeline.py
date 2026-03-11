#!/usr/bin/env python3
"""Daily Football Tips Pipeline — gen 2 cards + ส่งกลุ่ม + stats tracking"""
import subprocess, json, os, base64, datetime, urllib.request, sys

# Import stats tracker
sys.path.insert(0, os.path.dirname(__file__))
import stats_tracker

API_KEY = "0b5856b21f964b398ecc12918f22c7a2"
FONT_REG = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf","rb").read()).decode()
FONT_BOLD = base64.b64encode(open("/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf","rb").read()).decode()
CARD_SINGLE = "/root/.openclaw/workspace/card_banker_today.png"
CARD_STEP   = "/root/.openclaw/workspace/card_step_today.png"
CARD_STATS  = "/root/.openclaw/workspace/card_stats_today.png"
GROUP_ID    = "-1003869825051"

TZ_OFFSET = 7  # Bangkok

TEAM_TH = {
    "Arsenal FC":"อาร์เซนอล","Bayer 04 Leverkusen":"เลเวอร์คูเซ่น",
    "Paris Saint-Germain FC":"เปแอสเช","Chelsea FC":"เชลซี",
    "Real Madrid CF":"เรอัล มาดริด","Manchester City FC":"แมนเชสเตอร์ ซิตี้",
    "FK Bodø/Glimt":"โบดอ/กลิมต์","Sporting Clube de Portugal":"สปอร์ติ้ง",
    "Liverpool FC":"ลิเวอร์พูล","FC Barcelona":"บาร์เซโลน่า",
    "Atletico Madrid":"แอตเลติโก มาดริด","Inter Milan":"อินเตอร์ มิลาน",
    "AC Milan":"เอซี มิลาน","Juventus FC":"ยูเวนตุส",
    "Borussia Dortmund":"โบรุสเซีย ดอร์ทมุนด์","FC Bayern München":"บาเยิร์น มิวนิค",
    "Manchester United FC":"แมนเชสเตอร์ ยูไนเต็ด","Tottenham Hotspur FC":"สเปอร์ส",
}

def th(name): return TEAM_TH.get(name, name)

def fetch(url):
    req = urllib.request.Request(url)
    req.add_header("X-Auth-Token", API_KEY)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

def get_matches():
    today = datetime.date.today().strftime("%Y-%m-%d")
    d = fetch(f"https://api.football-data.org/v4/matches?date={today}")
    return d.get("matches", [])

def get_standings(comp):
    try:
        d = fetch(f"https://api.football-data.org/v4/competitions/{comp}/standings")
        s = {}
        for g in d.get("standings", []):
            for t in g.get("table", []):
                s[t["team"]["id"]] = t
        return s
    except: return {}

def local_time(utc_str):
    h, m = int(utc_str[11:13]), int(utc_str[14:16])
    h = (h + TZ_OFFSET) % 24
    return f"{h:02d}:{m:02d}"

def analyze(m, standings):
    hid = m["homeTeam"]["id"]
    aid = m["awayTeam"]["id"]
    hs = standings.get(hid, {})
    as_ = standings.get(aid, {})
    hp = hs.get("playedGames", 1) or 1
    ap = as_.get("playedGames", 1) or 1
    h_avg = hs.get("goalsFor", 0) / hp
    a_avg = as_.get("goalsFor", 0) / ap
    h_pos = hs.get("position", 10)
    a_pos = as_.get("position", 10)
    diff = abs(h_pos - a_pos)
    total_goals = h_avg + a_avg

    if diff >= 5:
        if a_pos < h_pos:
            s = th(m["awayTeam"]["name"])
            pick = f"{s} ต่อ 1 ลูก" if diff >= 8 else f"{s} ต่อครึ่ง"
        else:
            s = th(m["homeTeam"]["name"])
            pick = f"{s} ต่อ 1 ลูก" if diff >= 8 else f"{s} ต่อครึ่ง"
        conf = min(88, 62 + diff * 2)
        return pick, conf
    else:
        line = 2.5 if total_goals >= 2.5 else 2.0
        d = "สูง" if total_goals >= line else "ต่ำ"
        pick = f"{d} {line}"
        conf = min(80, 60 + int(abs(total_goals - line) * 10))
        return pick, conf

def gen_card(script, picks, output):
    payload = {
        "date": datetime.date.today().strftime("%-d/%m/%Y"),
        "league": "UEFA Champions League",
        "output": output,
        "picks": picks,
    }
    r = subprocess.run(
        ["node", script, FONT_REG, FONT_BOLD, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True
    )
    return r.returncode == 0

def check_results():
    """Check finished matches today and update stats"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    try:
        d = fetch(f"https://api.football-data.org/v4/matches?date={today}&status=FINISHED")
        finished = d.get("matches", [])
    except Exception as e:
        print(f"check_results error: {e}")
        return

    today_entry = stats_tracker.get_today_picks()
    if not today_entry:
        return

    for m in finished:
        home = th(m["homeTeam"]["name"])
        away = th(m["awayTeam"]["name"])
        match_name = f"{home} vs {away}"
        score_h = m.get("score", {}).get("fullTime", {}).get("home")
        score_a = m.get("score", {}).get("fullTime", {}).get("away")
        if score_h is None or score_a is None:
            continue

        for p in today_entry["picks"]:
            if p["match"] == match_name and p["result"] is None:
                # Simple heuristic: check if pick matches result
                result = evaluate_pick(p["pick"], home, away, score_h, score_a)
                if result:
                    stats_tracker.update_result(today, match_name, result)
                    print(f"Updated: {match_name} -> {result}")

def evaluate_pick(pick, home, away, sh, sa):
    """Evaluate if a pick was correct based on final score"""
    diff = sh - sa  # positive = home wins
    total = sh + sa

    # Over/Under picks
    if "สูง" in pick:
        line = 2.5
        try:
            parts = pick.split()
            for part in parts:
                try: line = float(part); break
                except: pass
        except: pass
        return "win" if total > line else "loss"
    if "ต่ำ" in pick:
        line = 2.5
        try:
            parts = pick.split()
            for part in parts:
                try: line = float(part); break
                except: pass
        except: pass
        return "win" if total < line else "loss"

    # Handicap picks (team ต่อ X ลูก / ครึ่ง)
    if "ต่อ" in pick:
        # Find which team is favored
        team_name = pick.split(" ต่อ")[0].strip()
        is_home = (team_name == home)
        goal_diff = diff if is_home else -diff  # positive = favored team winning

        if "1 ลูก" in pick:
            return "win" if goal_diff >= 2 else ("loss" if goal_diff <= 0 else None)
        elif "ครึ่ง" in pick:
            return "win" if goal_diff >= 1 else "loss"

    return None

def gen_stats_card():
    """Generate stats card image"""
    today_entry = stats_tracker.get_today_picks()
    stats_7d = stats_tracker.get_stats(7)
    stats_30d = stats_tracker.get_stats(30)

    today_picks = []
    if today_entry:
        today_picks = [{"match": p["match"], "pick": p["pick"], "result": p["result"]}
                       for p in today_entry["picks"]]

    payload = {
        "date": datetime.date.today().strftime("%-d/%m/%Y"),
        "today_picks": today_picks,
        "stats_7d": {"correct": stats_7d["correct"], "total": stats_7d["decided"], "pct": stats_7d["pct"]},
        "stats_30d": {"correct": stats_30d["correct"], "total": stats_30d["decided"], "pct": stats_30d["pct"]},
        "output": CARD_STATS,
    }
    r = subprocess.run(
        ["node", "/tmp/gen_stats_card.js", FONT_REG, FONT_BOLD, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print(f"stats_card:{CARD_STATS}")
        return True
    else:
        print(f"gen_stats_card error: {r.stderr}")
        return False

def send_to_group(path, caption):
    """ส่งผ่าน openclaw telegram tool"""
    # ใช้ openclaw message tool แทน bot token โดยตรง
    print(f"SEND:{path}:{caption}")

def main():
    matches = get_matches()
    ucl = [m for m in matches if m["competition"]["code"] == "CL"]
    if not ucl:
        ucl = matches[:6]
    
    standings = get_standings("CL")
    
    # วิเคราะห์ทุกคู่
    analyzed = []
    for m in ucl[:6]:
        pick, conf = analyze(m, standings)
        crest_h = m["homeTeam"].get("crest", "")
        crest_a = m["awayTeam"].get("crest", "")
        comp = m["competition"]["name"].replace("UEFA Champions League","UCL")
        analyzed.append({
            "home": th(m["homeTeam"]["name"]),
            "away": th(m["awayTeam"]["name"]),
            "league": comp,
            "time": local_time(m["utcDate"]),
            "tip": pick,
            "confidence": conf,
            "home_crest": crest_h,
            "away_crest": crest_a,
        })
    
    if not analyzed:
        print("no matches"); return
    
    # เรียงตาม confidence
    analyzed.sort(key=lambda x: -x["confidence"])
    
    # ตัวเต็ง = อันดับ 1
    banker = dict(analyzed[0])
    banker["tier"] = "banker"
    banker["handicap"] = banker["tip"]
    
    # สเต็ป 2-5 คู่
    step_picks = []
    tiers = ["banker","second","second","dark","dark"]
    for i, p in enumerate(analyzed[:5]):
        pp = dict(p)
        pp["tier"] = tiers[i]
        pp["handicap"] = pp["tip"]
        step_picks.append(pp)
    
    # Gen card ตัวเต็ง
    ok1 = gen_card("/tmp/gen_card7.js", [banker], CARD_SINGLE)
    # Gen card สเต็ป
    ok2 = gen_card("/tmp/gen_card7.js", step_picks, CARD_STEP)
    
    if ok1: print(f"banker_card:{CARD_SINGLE}")
    if ok2: print(f"step_card:{CARD_STEP}")

    # Save picks to stats tracker
    picks_for_stats = []
    for p in analyzed[:5]:
        picks_for_stats.append({
            "match": f"{p['home']} vs {p['away']}",
            "pick": p["tip"]
        })
    if picks_for_stats:
        stats_tracker.save_picks(picks_for_stats)
        print(f"saved {len(picks_for_stats)} picks to stats")

    # Check finished matches and update results
    check_results()

    # Generate stats card
    gen_stats_card()

if __name__ == "__main__":
    main()
