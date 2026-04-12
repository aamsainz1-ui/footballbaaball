#!/usr/bin/env python3
"""
card_football_master.py — ทีเด็ดบอลวันนี้ จาก football-data.org
ดึงแมตช์ + H2H + standings → วิเคราะห์ → gen card HTML → screenshot → ส่งกลุ่ม
"""
import json, os, sys, datetime, urllib.request, urllib.error, base64, tempfile, asyncio

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

FOOTBALL_API_KEY = "0b5856b21f964b398ecc12918f22c7a2"
BAABALL_TOKEN = "8735951403:AAGZw2vM4FCKZMRiMcIVjp5PH64OHaz8B2Y"
GROUP_ID = "-1003869825051"
CDP_URL = "ws://127.0.0.1:18802"
OUTPUT = "/root/.openclaw/workspace/card_tded.png"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"

# Top leagues to check
LEAGUES = ["PL", "PD", "BL1", "SA", "FL1", "CL", "EL"]

TEAM_TH = {
    "Arsenal FC": "อาร์เซนอล", "Chelsea FC": "เชลซี", "Liverpool FC": "ลิเวอร์พูล",
    "Manchester City FC": "แมนซิตี้", "Manchester United FC": "แมนยู",
    "Tottenham Hotspur FC": "สเปอร์ส", "Newcastle United FC": "นิวคาสเซิล",
    "Aston Villa FC": "แอสตัน วิลล่า", "Brighton & Hove Albion FC": "ไบรท์ตัน",
    "West Ham United FC": "เวสต์แฮม", "Crystal Palace FC": "คริสตัล พาเลซ",
    "Fulham FC": "ฟูแล่ม", "Brentford FC": "เบรนท์ฟอร์ด",
    "Wolverhampton Wanderers FC": "วูล์ฟแฮมป์ตัน", "AFC Bournemouth": "บอร์นมัธ",
    "Everton FC": "เอฟเวอร์ตัน", "Nottingham Forest FC": "น็อตติ้งแฮม",
    "Ipswich Town FC": "อิปสวิช", "Leicester City FC": "เลสเตอร์",
    "Southampton FC": "เซาธ์แฮมป์ตัน",
    "Real Madrid CF": "เรอัล มาดริด", "FC Barcelona": "บาร์เซโลน่า",
    "Atlético de Madrid": "แอตเลติโก มาดริด",
    "FC Bayern München": "บาเยิร์น", "Borussia Dortmund": "ดอร์ทมุนด์",
    "Bayer 04 Leverkusen": "เลเวอร์คูเซ่น",
    "SSC Napoli": "นาโปลี", "FC Internazionale Milano": "อินเตอร์",
    "AC Milan": "มิลาน", "Juventus FC": "ยูเวนตุส",
    "Paris Saint-Germain FC": "เปแอสเช", "AS Monaco FC": "โมนาโก",
    "Olympique de Marseille": "มาร์กเซย",
}

def thai(name):
    return TEAM_TH.get(name, name)

def api_get(url):
    req = urllib.request.Request(url)
    req.add_header("X-Auth-Token", FOOTBALL_API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  API error: {url} → {e}")
        return None

def get_today_matches():
    """ดึงแมตช์วันนี้จาก ESPN API (ฟรี) แล้วแปลงเป็น format เดิม"""
    import requests
    today = datetime.date.today().strftime("%Y-%m-%d")
    espn_date = today.replace("-", "")
    
    # ESPN league slugs → football-data competition codes
    ESPN_LEAGUES = {
        "eng.1": "PL", "esp.1": "PD", "ger.1": "BL1", "ita.1": "SA", "fra.1": "FL1",
        "uefa.champions": "CL", "uefa.europa": "EL"
    }
    
    matches = []
    for espn_slug, comp_code in ESPN_LEAGUES.items():
        try:
            r = requests.get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_slug}/scoreboard?dates={espn_date}",
                timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            for event in data.get("events", []):
                comp = event.get("competitions", [{}])[0]
                status_name = comp.get("status", {}).get("type", {}).get("name", "")
                # เอาเฉพาะแมตช์ที่ยังไม่เตะ
                if status_name not in ("STATUS_SCHEDULED", "STATUS_TIMED"):
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) != 2:
                    continue
                c0, c1 = competitors[0], competitors[1]
                if c0.get("homeAway") == "home":
                    home_c, away_c = c0, c1
                else:
                    home_c, away_c = c1, c0
                    
                home_name = home_c["team"]["displayName"]
                away_name = away_c["team"]["displayName"]
                kick_time = event.get("date", "")
                
                # แปลงเป็น format ที่ analyze_match ใช้ได้
                matches.append({
                    "id": event.get("id"),
                    "homeTeam": {"id": home_c["team"].get("id", ""), "name": home_name},
                    "awayTeam": {"id": away_c["team"].get("id", ""), "name": away_name},
                    "competition": {"code": comp_code},
                    "utcDate": kick_time,
                    "status": "TIMED",
                    "_espn": True
                })
        except Exception as e:
            print(f"  ESPN {espn_slug} error: {e}")
    
    print(f"  พบ {len(matches)} แมตช์")
    return matches

def get_standings(comp_code):
    data = api_get(f"https://api.football-data.org/v4/competitions/{comp_code}/standings")
    if not data:
        return {}
    standings = {}
    for group in data.get("standings", []):
        for t in group.get("table", []):
            tid = t["team"]["id"]
            played = t.get("playedGames", 1) or 1
            standings[tid] = {
                "pos": t["position"], "pts": t["points"],
                "gf": t["goalsFor"], "ga": t["goalsAgainst"],
                "played": played, "won": t["won"], "draw": t.get("draw", 0), "lost": t.get("lost", 0),
                "gf_avg": round(t["goalsFor"] / played, 2),
                "ga_avg": round(t["goalsAgainst"] / played, 2),
            }
    return standings

def get_h2h(match_id):
    import time
    time.sleep(1.5)  # Rate limit: football-data.org free tier = 10 req/min
    data = api_get(f"https://api.football-data.org/v4/matches/{match_id}/head2head?limit=5")
    if not data:
        return None
    agg = data.get("aggregates", {})
    matches = data.get("resultSet", {})
    return {
        "total": matches.get("count", 0),
        "home_wins": agg.get("homeTeam", {}).get("wins", 0),
        "away_wins": agg.get("awayTeam", {}).get("wins", 0),
        "draws": agg.get("homeTeam", {}).get("draws", 0),
        "recent": data.get("matches", [])[:5],
    }

def analyze_match(match, standings_cache):
    """วิเคราะห์แมตช์ด้วยสถิติจริง → เลือก pick"""
    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    comp_code = match["competition"]["code"]

    # Get standings
    if comp_code not in standings_cache:
        standings_cache[comp_code] = get_standings(comp_code)
    standings = standings_cache[comp_code]

    hs = standings.get(home_id, {})
    as_ = standings.get(away_id, {})

    # Get H2H
    h2h = get_h2h(match["id"])

    # Time (UTC+7)
    utc_str = match["utcDate"][11:16]
    h, mn = int(utc_str[:2]), int(utc_str[3:])
    h_local = (h + 7) % 24
    local_time = f"{h_local:02d}:{mn:02d}"

    # Analysis
    h_pos = hs.get("pos", 10)
    a_pos = as_.get("pos", 10)
    pos_diff = h_pos - a_pos  # negative = home is higher ranked
    h_gf_avg = hs.get("gf_avg", 1.2)
    a_gf_avg = as_.get("gf_avg", 1.2)
    h_ga_avg = hs.get("ga_avg", 1.0)
    a_ga_avg = as_.get("ga_avg", 1.0)
    total_goal_avg = round(h_gf_avg + a_gf_avg, 2)

    # H2H analysis
    h2h_text = ""
    h2h_trend = "neutral"
    if h2h and h2h["total"] > 0:
        hw = h2h["home_wins"]
        aw = h2h["away_wins"]
        dr = h2h["draws"]
        h2h_text = f"H2H: {hw}W-{dr}D-{aw}L"
        if hw > aw + 1:
            h2h_trend = "home"
        elif aw > hw + 1:
            h2h_trend = "away"

    # Recent H2H goals
    h2h_goals = []
    if h2h and h2h.get("recent"):
        for rm in h2h["recent"]:
            score = rm.get("score", {})
            ft = score.get("fullTime", {})
            if ft.get("home") is not None:
                h2h_goals.append(ft["home"] + ft["away"])

    h2h_avg_goals = sum(h2h_goals) / len(h2h_goals) if h2h_goals else 2.5

    # Form calculation
    h_form = hs.get("won", 0) / max(hs.get("played", 1), 1)
    a_form = as_.get("won", 0) / max(as_.get("played", 1), 1)

    # ===== PICK DECISION =====
    confidence = 65
    pick_type = ""
    pick_label = ""
    reason = ""

    # Strong position difference → Handicap
    if abs(pos_diff) >= 6:
        if pos_diff < 0:
            # Home ranked higher
            stronger = thai(home)
            if abs(pos_diff) >= 10 and h_form >= 0.5:
                pick_label = f"{stronger} ต่อ 1 ลูก"
                confidence = min(88, 70 + abs(pos_diff))
                reason = f"{stronger} อันดับ {h_pos} ฟอร์มแกร่ง เหนือกว่า {thai(away)} อันดับ {a_pos}"
            else:
                pick_label = f"{stronger} ต่อครึ่ง"
                confidence = min(82, 65 + abs(pos_diff))
                reason = f"{stronger} อันดับ {h_pos} เหนือ {thai(away)} อันดับ {a_pos} เจ้าบ้านได้เปรียบ"
        else:
            # Away ranked higher
            stronger = thai(away)
            if abs(pos_diff) >= 10 and a_form >= 0.5:
                pick_label = f"{stronger} ต่อ 1 ลูก"
                confidence = min(85, 68 + abs(pos_diff))
                reason = f"{stronger} อันดับ {a_pos} บุกแกร่ง {thai(home)} อันดับ {h_pos} เสียท่า"
            else:
                pick_label = f"{stronger} ต่อครึ่ง"
                confidence = min(80, 63 + abs(pos_diff))
                reason = f"{stronger} อันดับ {a_pos} ฟอร์มดีกว่า {thai(home)} อันดับ {h_pos}"
        pick_type = "handicap"

    # Moderate difference + strong home → Home win
    elif abs(pos_diff) >= 3 and pos_diff < 0 and h_form >= 0.5:
        pick_label = f"{thai(home)} ชนะ"
        pick_type = "handicap"
        confidence = min(78, 65 + abs(pos_diff) * 2)
        reason = f"{thai(home)} เจ้าบ้านฟอร์มดี อันดับ {h_pos} vs {a_pos}"

    # Close match → Over/Under based on goals
    else:
        # Combine league avg, team avg, H2H avg for line decision
        combined_avg = (total_goal_avg * 0.5 + h2h_avg_goals * 0.3 + (h_ga_avg + a_ga_avg) * 0.2)

        if combined_avg >= 3.0:
            pick_label = "สูง 2.5"
            pick_type = "over_under"
            confidence = min(82, 65 + int((combined_avg - 2.5) * 15))
            reason = f"ทั้งคู่บุกได้ ยิงเฉลี่ย {total_goal_avg:.1f} H2H เฉลี่ย {h2h_avg_goals:.1f} ลูก"
        elif combined_avg >= 2.3:
            pick_label = "สูง 2.0"
            pick_type = "over_under"
            confidence = min(78, 62 + int((combined_avg - 2.0) * 12))
            reason = f"เปิดเกมรุก ยิงเฉลี่ย {total_goal_avg:.1f} น่าเปิดสูง 2"
        elif combined_avg <= 1.8:
            pick_label = "ต่ำ 2.5"
            pick_type = "over_under"
            confidence = min(80, 65 + int((2.5 - combined_avg) * 15))
            reason = f"ทั้งคู่แน่นรับ ยิงเฉลี่ยน้อย {total_goal_avg:.1f} — ต่ำปลอดภัย"
        else:
            # Medium goals → check if home or away has edge
            if h_form > a_form + 0.15:
                pick_label = f"{thai(home)} ชนะ"
                pick_type = "handicap"
                confidence = 68
                reason = f"{thai(home)} เจ้าบ้านฟอร์มดีกว่า เปอร์เซ็นต์ชนะ {h_form:.0%} vs {a_form:.0%}"
            elif a_form > h_form + 0.15:
                pick_label = f"{thai(away)} ชนะ"
                pick_type = "handicap"
                confidence = 66
                reason = f"{thai(away)} ฟอร์มเหนือกว่า เปอร์เซ็นต์ชนะ {a_form:.0%} vs {h_form:.0%}"
            else:
                pick_label = "สูง 2.0"
                pick_type = "over_under"
                confidence = 65
                reason = f"สูสีทั้งคู่ เปิดเกมได้ ยิงเฉลี่ย {total_goal_avg:.1f}"

    # H2H bonus
    if h2h_trend == "home" and "home" in pick_label.lower():
        confidence = min(confidence + 5, 92)
    elif h2h_trend == "away" and "away" in pick_label.lower():
        confidence = min(confidence + 5, 92)

    return {
        "home": thai(home), "away": thai(away),
        "home_en": home, "away_en": away,
        "league": match.get("competition", {}).get("name", match.get("competition", {}).get("code", "")),
        "league_code": comp_code,
        "time": local_time,
        "pick": pick_label,
        "pick_type": pick_type,
        "confidence": confidence,
        "reason": reason,
        "h2h": h2h_text,
        "h_pos": h_pos, "a_pos": a_pos,
        "total_goal_avg": total_goal_avg,
    }

def gen_card_html(picks, date_str):
    """Generate dark-themed HTML card"""
    rows_html = ""
    for i, p in enumerate(picks):
        # Confidence badge
        if p["confidence"] >= 80:
            badge = '<span style="background:#22c55e;color:#000;padding:2px 10px;border-radius:12px;font-weight:bold;">🔥 เต็ง</span>'
        elif p["confidence"] >= 70:
            badge = '<span style="background:#eab308;color:#000;padding:2px 10px;border-radius:12px;font-weight:bold;">✅ แนะนำ</span>'
        else:
            badge = '<span style="background:#64748b;color:#fff;padding:2px 10px;border-radius:12px;">📊 วิเคราะห์</span>'

        # Pick icon
        if "สูง" in p["pick"]:
            pick_icon = "⬆️"
        elif "ต่ำ" in p["pick"]:
            pick_icon = "⬇️"
        elif "ต่อ" in p["pick"]:
            pick_icon = "⚡"
        else:
            pick_icon = "🎯"

        league_short = p["league"].replace("Primera Division", "ลาลีกา").replace("Serie A", "เซเรีย อา").replace("Bundesliga", "บุนเดสลีกา").replace("Ligue 1", "ลีกเอิง").replace("Premier League", "พรีเมียร์ลีก").replace("UEFA Champions League", "UCL").replace("UEFA Europa League", "UEL")

        rows_html += f"""
        <div style="background:linear-gradient(135deg, #1a2332, #0f1923);border:1px solid #2d4a3e;border-radius:16px;padding:20px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="color:#4ade80;font-size:14px;">{league_short}</span>
                <span style="color:#94a3b8;font-size:14px;">⏰ {p['time']} น.</span>
            </div>
            <div style="text-align:center;margin:12px 0;">
                <span style="color:#fff;font-size:22px;font-weight:bold;">{p['home']}</span>
                <span style="color:#4ade80;font-size:18px;margin:0 12px;">VS</span>
                <span style="color:#fff;font-size:22px;font-weight:bold;">{p['away']}</span>
            </div>
            <div style="display:flex;justify-content:center;gap:8px;margin:8px 0;">
                <span style="color:#94a3b8;font-size:13px;">อันดับ {p['h_pos']}</span>
                <span style="color:#4ade80;">|</span>
                <span style="color:#94a3b8;font-size:13px;">อันดับ {p['a_pos']}</span>
                {"<span style='color:#4ade80;'>|</span><span style='color:#94a3b8;font-size:13px;'>" + p['h2h'] + "</span>" if p['h2h'] else ""}
            </div>
            <div style="background:#0d2818;border:1px solid #22c55e44;border-radius:12px;padding:12px;text-align:center;margin-top:10px;">
                <div style="font-size:20px;font-weight:bold;color:#4ade80;">{pick_icon} {p['pick']}</div>
                <div style="color:#94a3b8;font-size:13px;margin-top:6px;">{p['reason']}</div>
            </div>
            <div style="text-align:right;margin-top:8px;">{badge}</div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'NotoThai'; src:url('file://{FONT_REG}'); font-weight:400; }}
@font-face {{ font-family:'NotoThai'; src:url('file://{FONT_BOLD}'); font-weight:700; }}
* {{ margin:0; padding:0; box-sizing:border-box; font-family:'NotoThai','Noto Sans Thai',sans-serif; }}
</style></head>
<body style="background:#0a0f14;padding:0;margin:0;">
<div style="width:720px;padding:30px;background:linear-gradient(180deg,#0a1a0f,#0a0f14);">
    <!-- Header -->
    <div style="text-align:center;padding:20px;background:linear-gradient(135deg,#0d2818,#1a2332);border-radius:16px;border:1px solid #22c55e55;margin-bottom:20px;">
        <div style="font-size:28px;font-weight:bold;color:#4ade80;">⚽ ทีเด็ดบอลวันนี้</div>
        <div style="color:#94a3b8;font-size:16px;margin-top:6px;">📅 {date_str}</div>
    </div>

    {rows_html}

    <!-- Footer -->
    <div style="text-align:center;padding:16px;color:#475569;font-size:13px;margin-top:10px;">
        ⚠️ วิเคราะห์ประกอบการตัดสินใจ | 🤖 Powered by Stats Analysis
    </div>
</div>
</body></html>"""
    return html

def get_cdp_ws_url():
    """Get actual WebSocket debugger URL from CDP"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:18802/json/version", timeout=5) as r:
            data = json.loads(r.read())
            return data.get("webSocketDebuggerUrl", CDP_URL)
    except:
        return CDP_URL

async def screenshot_html(html_content, output_path):
    """Take screenshot via Playwright CDP"""
    from playwright.async_api import async_playwright
    ws_url = get_cdp_ws_url()
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()
        await page.set_viewport_size({"width": 720, "height": 1200})
        await page.set_content(html_content, wait_until="networkidle")
        # Get actual content height
        height = await page.evaluate("document.body.scrollHeight")
        await page.set_viewport_size({"width": 720, "height": height + 20})
        await page.screenshot(path=output_path, full_page=True)
        await page.close()
    print(f"✅ Screenshot: {output_path}")

def send_photo(photo_path, caption=""):
    """Send photo to Telegram group"""
    import urllib.parse
    url = f"https://api.telegram.org/bot{BAABALL_TOKEN}/sendPhoto"
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    
    with open(photo_path, "rb") as f:
        photo_data = f.read()
    
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{GROUP_ID}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="card.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + photo_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            print(f"✅ Sent to Telegram: {result.get('ok')}")
            return result.get("ok")
    except Exception as e:
        print(f"❌ Telegram send error: {e}")
        return False

def main(dry_run=False, limit=5):
    today = datetime.date.today()
    day_names = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]
    date_str = f"วัน{day_names[today.weekday()]}ที่ {today.strftime('%d/%m/%Y')}"

    print("🔍 ดึงแมตช์วันนี้...")
    matches = get_today_matches()
    print(f"  พบ {len(matches)} แมตช์")

    if not matches:
        print("❌ ไม่มีแมตช์วันนี้ใน Top leagues")
        return

    # Analyze all matches
    standings_cache = {}
    analyzed = []
    for m in matches:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        print(f"  📊 วิเคราะห์: {home} vs {away}")
        result = analyze_match(m, standings_cache)
        analyzed.append(result)

    # Self-improve: ปรับ confidence ตาม weight จากประวัติ win/loss
    try:
        from self_improve_football import get_pick_score
        for p in analyzed:
            p["confidence"] = get_pick_score(p["pick"], p.get("confidence"), "tded")
    except Exception as e:
        print(f"  ⚠️ self_improve weight skip: {e}")

    # Sort by confidence, pick top 3-5
    analyzed.sort(key=lambda x: x["confidence"], reverse=True)
    limit = max(1, min(int(limit), 10))
    picks = analyzed[:limit]

    print(f"\n🎯 เลือก {len(picks)} คู่เด่น:")
    for p in picks:
        print(f"  {p['home']} vs {p['away']} → {p['pick']} ({p['confidence']}%)")

    # Generate card
    html = gen_card_html(picks, date_str)
    html_path = os.path.join(tempfile.gettempdir(), "card_football_master.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    asyncio.run(screenshot_html(html, OUTPUT))

    # Save picks to stats_tracker (backward compatible)
    try:
        import stats_tracker
        tracker_picks = [{"match": f"{p['home']} vs {p['away']}", "pick": p["pick"]} for p in picks]
        stats_tracker.save_picks(tracker_picks)
        print(f"✅ บันทึก {len(tracker_picks)} picks ลง stats_tracker")
    except Exception as e:
        print(f"⚠️ stats_tracker error: {e}")

    # Save picks to canonical picks_log (new system)
    try:
        import picks_log
        log_picks = []
        for p in picks:
            log_picks.append({
                "home": p["home"],
                "away": p["away"],
                "home_en": p.get("home_en", ""),
                "away_en": p.get("away_en", ""),
                "pick": p["pick"],
                "league": p.get("league", ""),
                "league_code": p.get("league_code", ""),
                "kick_time": p.get("time", ""),
                "confidence": p.get("confidence"),
                "reason": p.get("reason", ""),
            })
        picks_log.save_picks(log_picks, pick_type="tded")
        print(f"✅ บันทึก {len(log_picks)} picks ลง picks_log (tded)")
    except Exception as e:
        print(f"⚠️ picks_log error: {e}")

    # Send to group
    if not dry_run:
        caption = f"⚽ ทีเด็ดบอลวันนี้ {date_str}\n"
        for p in picks:
            emoji = "🔥" if p["confidence"] >= 80 else "✅" if p["confidence"] >= 70 else "📊"
            caption += f"\n{emoji} {p['home']} vs {p['away']}\n   👉 {p['pick']}"
        caption += "\n\n⚠️ วิเคราะห์ประกอบการตัดสินใจ"
        send_photo(OUTPUT, caption)
    else:
        print(f"🔇 DRY RUN — ไม่ส่งกลุ่ม")

    print(f"\n✅ เสร็จสิ้น! Output: {OUTPUT}")
    return picks

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "dry_run" in sys.argv
    limit = 5
    if "--limit" in sys.argv:
        try:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])
        except Exception:
            limit = 5
    main(dry_run=dry_run, limit=limit)
