"""
 Thai Football Analysis v5
- ใช้ชื่อทีม/ลีกเป็นไทย
- เขียนวิเคราะห์เป็นย่อหน้าแบบนักวิเคราะห์บอลไทย
- ศัพท์ฟุตบอลไทยทั้งหมด
- CLI: --schedule, --standings, --results, --scorers, --count, --rated, --parlay, --summary
"""

import json, os, sys, io, argparse
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Fix Windows console encoding for emoji/Thai
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

TZ = timezone(timedelta(hours=7))
NOW = datetime.now(TZ)
TODAY = NOW.strftime("%Y-%m-%d")
DATE_TH = NOW.strftime("%d/%m/%Y")
DAY_NAMES = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]
DAY_TH = DAY_NAMES[NOW.weekday()]

API_KEY = os.environ.get("FOOTBALLDATA_KEY", "0b5856b21f964b398ecc12918f22c7a2")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_LOG = os.path.join(SCRIPT_DIR, "results_log.json")

PREDICTIONS_LOG = os.path.join(SCRIPT_DIR, "predictions.json")

def local_match_date(match):
    dt = parse_utc_date(match.get("utcDate", ""))
    if not dt:
        return TODAY
    return dt.astimezone(TZ).strftime("%Y-%m-%d")

def infer_pick(home_info, away_info, h2h_matches=None, home_name="", away_name=""):
    """Infer one best betting angle only."""
    if home_info and away_info:
        diff = (home_info.get("points", 0) - away_info.get("points", 0))
        goal_total = (home_info.get("goalsFor", 0) + away_info.get("goalsFor", 0))
        conceded_total = (home_info.get("goalsAgainst", 0) + away_info.get("goalsAgainst", 0))
        if diff >= 20:
            return {"pick_type": "HANDICAP", "pick_value": "HOME_-0.5/1", "label": f"{home_name} -0.5/1"}
        if diff >= 8:
            return {"pick_type": "HANDICAP", "pick_value": "HOME_-0.5", "label": f"{home_name} -0.5"}
        if diff <= -20:
            return {"pick_type": "HANDICAP", "pick_value": "AWAY_-0.5/1", "label": f"{away_name} -0.5/1"}
        if diff <= -8:
            return {"pick_type": "HANDICAP", "pick_value": "AWAY_-0.5", "label": f"{away_name} -0.5"}
        if goal_total >= 70 or conceded_total >= 65:
            return {"pick_type": "TOTAL", "pick_value": "OVER_2.5", "label": "สูง 2.5"}
    return {"pick_type": "TOTAL", "pick_value": "UNDER_2.5", "label": "ต่ำ 2.5"}

def load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("predictions"), list):
            return data["predictions"]
        return data if isinstance(data, list) else []
    except:
        return []

def save_prediction_records(records):
    existing = load_json_list(RESULTS_LOG)
    seen = {(x.get("date"), x.get("home"), x.get("away"), x.get("pick_type"), x.get("pick_value")) for x in existing}
    for rec in records:
        key = (rec.get("date"), rec.get("home"), rec.get("away"), rec.get("pick_type"), rec.get("pick_value"))
        if key not in seen:
            existing.append(rec)
            seen.add(key)
    with open(RESULTS_LOG, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def update_prediction_results(date_from=None, date_to=None):
    logs = load_json_list(RESULTS_LOG)
    # de-duplicate old rows
    deduped = []
    seen = set()
    for rec in logs:
        key = (rec.get("date"), rec.get("home"), rec.get("away"), rec.get("pick_type"), rec.get("pick_value"), rec.get("prediction"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rec)
    logs = deduped
    pending_dates = sorted({x.get("date") for x in logs if x.get("date") and x.get("correct") is None})
    if date_from and date_to:
        pending_dates = [d for d in pending_dates if date_from <= d <= date_to]
    if not pending_dates:
        return logs
    score_map = {}
    for d in pending_dates:
        try:
            data = api_get(f"/matches?date={d}")
            matches = data.get("matches", [])
        except:
            continue
        for m in matches:
            home = th_name(m.get("homeTeam", {}).get("shortName", m.get("homeTeam", {}).get("name", "?")))
            away = th_name(m.get("awayTeam", {}).get("shortName", m.get("awayTeam", {}).get("name", "?")))
            mdate = local_match_date(m)
            ft = m.get("score", {}).get("fullTime", {})
            hs = ft.get("home")
            as_ = ft.get("away")
            if hs is None or as_ is None:
                continue
            score_map[(mdate, home, away)] = (hs, as_)
    for rec in logs:
        if rec.get("correct") is not None:
            continue
        result = score_map.get((rec.get("date"), rec.get("home"), rec.get("away")))
        if not result:
            continue
        hs, as_ = result
        rec["actual"] = f"{rec.get('home')} {hs}-{as_} {rec.get('away')}"
        pick = rec.get("pick_value")
        if pick == "HOME":
            rec["correct"] = hs > as_
        elif pick == "AWAY":
            rec["correct"] = as_ > hs
        elif pick == "DRAW_NO_BET_HOME":
            rec["correct"] = hs >= as_
        else:
            rec["correct"] = None
    with open(RESULTS_LOG, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    total = len(logs)
    correct = sum(1 for x in logs if x.get("correct") is True)
    wrong = sum(1 for x in logs if x.get("correct") is False)
    pending = sum(1 for x in logs if x.get("correct") is None)
    with open(PREDICTIONS_LOG, "w", encoding="utf-8") as f:
        json.dump({"predictions": logs, "stats": {"total": total, "correct": correct, "wrong": wrong, "pending": pending}}, f, ensure_ascii=False, indent=2)
    return logs

# Major league priority order for match selection
LEAGUE_PRIORITY = ["PL", "PD", "SA", "BL1", "FL1", "CL", "ELC", "EL", "DED", "PPL"]

# ===== ชื่อทีมไทย (ครบทุกลีกหลัก) =====
TEAM_TH = {
    # === Premier League (PL) ===
    "Arsenal FC": "อาร์เซนอล", "Arsenal": "อาร์เซนอล",
    "Aston Villa FC": "แอสตัน วิลล่า", "Aston Villa": "แอสตัน วิลล่า",
    "AFC Bournemouth": "บอร์นมัธ", "Bournemouth": "บอร์นมัธ",
    "Brentford FC": "เบรนท์ฟอร์ด", "Brentford": "เบรนท์ฟอร์ด",
    "Brighton & Hove Albion FC": "ไบรท์ตัน", "Brighton": "ไบรท์ตัน",
    "Chelsea FC": "เชลซี", "Chelsea": "เชลซี",
    "Crystal Palace FC": "คริสตัล พาเลซ", "Crystal Palace": "คริสตัล พาเลซ",
    "Everton FC": "เอฟเวอร์ตัน", "Everton": "เอฟเวอร์ตัน",
    "Fulham FC": "ฟูแล่ม", "Fulham": "ฟูแล่ม",
    "Ipswich Town FC": "อิปสวิช ทาวน์", "Ipswich Town": "อิปสวิช ทาวน์", "Ipswich": "อิปสวิช ทาวน์",
    "Leicester City FC": "เลสเตอร์", "Leicester City": "เลสเตอร์", "Leicester": "เลสเตอร์",
    "Liverpool FC": "ลิเวอร์พูล", "Liverpool": "ลิเวอร์พูล",
    "Manchester City FC": "แมนซิตี้", "Man City": "แมนซิตี้", "Manchester City": "แมนซิตี้",
    "Manchester United FC": "แมนยู", "Man United": "แมนยู", "Manchester United": "แมนยู",
    "Newcastle United FC": "นิวคาสเซิล", "Newcastle": "นิวคาสเซิล", "Newcastle United": "นิวคาสเซิล",
    "Nottingham Forest FC": "น็อตติ้งแฮม ฟอเรสต์", "Nottingham Forest": "น็อตติ้งแฮม ฟอเรสต์", "Nott'm Forest": "น็อตติ้งแฮม ฟอเรสต์",
    "Southampton FC": "เซาท์แฮมป์ตัน", "Southampton": "เซาท์แฮมป์ตัน",
    "Tottenham Hotspur FC": "สเปอร์ส", "Spurs": "สเปอร์ส", "Tottenham": "สเปอร์ส",
    "West Ham United FC": "เวสต์แฮม", "West Ham": "เวสต์แฮม", "West Ham United": "เวสต์แฮม",
    "Wolverhampton Wanderers FC": "วูล์ฟส์", "Wolves": "วูล์ฟส์", "Wolverhampton": "วูล์ฟส์",
    "Burnley FC": "เบิร์นลีย์", "Burnley": "เบิร์นลีย์",
    "Luton Town FC": "ลูตัน ทาวน์", "Luton Town": "ลูตัน ทาวน์", "Luton": "ลูตัน ทาวน์",
    "Sheffield United FC": "เชฟฟิลด์ ยูไนเต็ด", "Sheffield United": "เชฟฟิลด์ ยูไนเต็ด", "Sheffield Utd": "เชฟฟิลด์ ยูไนเต็ด",

    # === La Liga (PD) ===
    "FC Barcelona": "บาร์ซ่า", "Barcelona": "บาร์ซ่า", "Barça": "บาร์ซ่า",
    "Real Madrid CF": "เรอัลมาดริด", "Real Madrid": "เรอัลมาดริด",
    "Atlético de Madrid": "แอตเลติโก้", "Atlético Madrid": "แอตเลติโก้", "Atletico Madrid": "แอตเลติโก้",
    "Girona FC": "กิโรน่า", "Girona": "กิโรน่า",
    "Athletic Club": "แอธเลติก บิลเบา", "Athletic Bilbao": "แอธเลติก บิลเบา",
    "Real Sociedad de Fútbol": "เรอัล โซเซียดาด", "Real Sociedad": "เรอัล โซเซียดาด",
    "Real Betis Balompié": "เรอัล เบติส", "Real Betis": "เรอัล เบติส", "Betis": "เรอัล เบติส",
    "Villarreal CF": "บีญาร์เรอัล", "Villarreal": "บีญาร์เรอัล",
    "Valencia CF": "บาเลนเซีย", "Valencia": "บาเลนเซีย",
    "Getafe CF": "เกตาเฟ่", "Getafe": "เกตาเฟ่",
    "CA Osasuna": "โอซาซูน่า", "Osasuna": "โอซาซูน่า",
    "Sevilla FC": "เซบีย่า", "Sevilla": "เซบีย่า",
    "RC Celta de Vigo": "เซลต้า บีโก้", "Celta Vigo": "เซลต้า บีโก้", "Celta": "เซลต้า บีโก้",
    "RCD Mallorca": "มายอร์ก้า", "Mallorca": "มายอร์ก้า",
    "UD Las Palmas": "ลาส พัลมาส", "Las Palmas": "ลาส พัลมาส",
    "Deportivo Alavés": "อลาเบส", "Alavés": "อลาเบส", "Alaves": "อลาเบส",
    "Rayo Vallecano de Madrid": "ราโย บาเยกาโน่", "Rayo Vallecano": "ราโย บาเยกาโน่",
    "Cádiz CF": "กาดิซ", "Cádiz": "กาดิซ", "Cadiz": "กาดิซ",
    "Granada CF": "กรานาด้า", "Granada": "กรานาด้า",
    "UD Almería": "อัลเมเรีย", "Almería": "อัลเมเรีย", "Almeria": "อัลเมเรีย",
    "RCD Espanyol de Barcelona": "เอสปันญ่อล", "Espanyol": "เอสปันญ่อล",
    "CD Leganés": "เลกาเนส", "Leganés": "เลกาเนส", "Leganes": "เลกาเนส",
    "Real Valladolid CF": "บายาโดลิด", "Real Valladolid": "บายาโดลิด", "Valladolid": "บายาโดลิด",
    "Racing Club de Ferrol": "ราซิ่ง เฟร์โรล", "Racing Ferrol": "ราซิ่ง เฟร์โรล",

    # === Serie A (SA) ===
    "FC Internazionale Milano": "อินเตอร์", "Inter": "อินเตอร์", "Inter Milan": "อินเตอร์",
    "AC Milan": "เอซีมิลาน", "Milan": "เอซีมิลาน",
    "SSC Napoli": "นาโปลี", "Napoli": "นาโปลี",
    "Juventus FC": "ยูเว่", "Juventus": "ยูเว่",
    "Atalanta BC": "อตาลันต้า", "Atalanta": "อตาลันต้า",
    "AS Roma": "โรม่า", "Roma": "โรม่า",
    "SS Lazio": "ลาซิโอ", "Lazio": "ลาซิโอ",
    "ACF Fiorentina": "ฟิออเรนติน่า", "Fiorentina": "ฟิออเรนติน่า",
    "Bologna FC 1909": "โบโลญญ่า", "Bologna": "โบโลญญ่า",
    "Torino FC": "โตริโน่", "Torino": "โตริโน่",
    "AC Monza": "มอนซ่า", "Monza": "มอนซ่า",
    "Udinese Calcio": "อูดิเนเซ่", "Udinese": "อูดิเนเซ่",
    "US Sassuolo Calcio": "ซาสซูโอโล่", "Sassuolo": "ซาสซูโอโล่",
    "Empoli FC": "เอ็มโปลี", "Empoli": "เอ็มโปลี",
    "Cagliari Calcio": "กายารี่", "Cagliari": "กายารี่",
    "Hellas Verona FC": "เวโรน่า", "Verona": "เวโรน่า", "Hellas Verona": "เวโรน่า",
    "US Lecce": "เลชเช่", "Lecce": "เลชเช่",
    "Frosinone Calcio": "โฟรซิโนเน่", "Frosinone": "โฟรซิโนเน่",
    "US Salernitana 1919": "ซาแลร์นิตาน่า", "Salernitana": "ซาแลร์นิตาน่า",
    "Genoa CFC": "เจนัว", "Genoa": "เจนัว",
    "Parma Calcio 1913": "ปาร์ม่า", "Parma": "ปาร์ม่า",
    "Venezia FC": "เวเนเซีย", "Venezia": "เวเนเซีย",
    "Como 1907": "โคโม่", "Como": "โคโม่",
    "US Cremonese": "เครโมเนเซ่", "Cremonese": "เครโมเนเซ่",
    "Spezia Calcio": "สเปเซีย", "Spezia": "สเปเซีย",
    "Sampdoria": "ซามพ์โดเรีย",

    # === Bundesliga (BL1) ===
    "FC Bayern München": "บาเยิร์น", "Bayern": "บาเยิร์น", "Bayern Munich": "บาเยิร์น",
    "Borussia Dortmund": "ดอร์ทมุนด์", "Dortmund": "ดอร์ทมุนด์",
    "Bayer 04 Leverkusen": "เลเวอร์คูเซ่น", "Leverkusen": "เลเวอร์คูเซ่น",
    "RB Leipzig": "ไลป์ซิก", "Leipzig": "ไลป์ซิก",
    "VfB Stuttgart": "ชตุ๊ตการ์ท", "Stuttgart": "ชตุ๊ตการ์ท",
    "Eintracht Frankfurt": "แฟรงค์เฟิร์ต", "Frankfurt": "แฟรงค์เฟิร์ต",
    "VfL Wolfsburg": "โวล์ฟสบวร์ก", "Wolfsburg": "โวล์ฟสบวร์ก",
    "SC Freiburg": "ไฟรบวร์ก", "Freiburg": "ไฟรบวร์ก",
    "TSG 1899 Hoffenheim": "ฮอฟเฟ่นไฮม์", "Hoffenheim": "ฮอฟเฟ่นไฮม์",
    "1. FC Union Berlin": "อูนิโอน เบอร์ลิน", "Union Berlin": "อูนิโอน เบอร์ลิน",
    "Borussia Mönchengladbach": "มึนเช่นกลัดบัค", "Mönchengladbach": "มึนเช่นกลัดบัค", "Gladbach": "มึนเช่นกลัดบัค",
    "SV Werder Bremen": "แวร์เดอร์ เบรเมน", "Werder Bremen": "แวร์เดอร์ เบรเมน",
    "1. FSV Mainz 05": "ไมนซ์", "Mainz": "ไมนซ์", "Mainz 05": "ไมนซ์",
    "FC Augsburg": "เอาก์สบวร์ก", "Augsburg": "เอาก์สบวร์ก",
    "1. FC Heidenheim 1846": "ไฮเดนไฮม์", "Heidenheim": "ไฮเดนไฮม์",
    "SV Darmstadt 98": "ดาร์มชตัดท์", "Darmstadt": "ดาร์มชตัดท์", "Darmstadt 98": "ดาร์มชตัดท์",
    "1. FC Köln": "โคโลญจน์", "Köln": "โคโลญจน์", "Cologne": "โคโลญจน์",
    "FC St. Pauli 1910": "เซนต์ เพาลี", "St. Pauli": "เซนต์ เพาลี",
    "Holstein Kiel": "ฮ็อลชไตน์ คีล", "Kiel": "ฮ็อลชไตน์ คีล",

    # === Ligue 1 (FL1) ===
    "Paris Saint-Germain FC": "เปแอสเช", "PSG": "เปแอสเช", "Paris Saint-Germain": "เปแอสเช",
    "AS Monaco FC": "โมนาโก", "Monaco": "โมนาโก",
    "Olympique de Marseille": "มาร์กเซย", "Marseille": "มาร์กเซย",
    "Olympique Lyonnais": "ลียง", "Lyon": "ลียง",
    "LOSC Lille": "ลีลล์", "Lille": "ลีลล์",
    "OGC Nice": "นีซ", "Nice": "นีซ",
    "Stade Rennais FC 1901": "แรนส์", "Rennes": "แรนส์",
    "RC Lens": "ล็องส์", "Lens": "ล็องส์",
    "RC Strasbourg Alsace": "สตราส์บูร์ก", "Strasbourg": "สตราส์บูร์ก",
    "Montpellier HSC": "มงต์เปลลิเย่ร์", "Montpellier": "มงต์เปลลิเย่ร์",
    "Stade de Reims": "แร็งส์", "Reims": "แร็งส์",
    "Toulouse FC": "ตูลูส", "Toulouse": "ตูลูส",
    "FC Nantes": "น็องต์", "Nantes": "น็องต์",
    "Stade Brestois 29": "เบรสต์", "Brest": "เบรสต์",
    "FC Lorient": "ลอเรียงต์", "Lorient": "ลอเรียงต์",
    "Le Havre AC": "เลออาฟวร์", "Le Havre": "เลออาฟวร์",
    "Clermont Foot 63": "แกลร์มงต์", "Clermont": "แกลร์มงต์",
    "FC Metz": "เมตซ์", "Metz": "เมตซ์",
    "AJ Auxerre": "โอแซร์", "Auxerre": "โอแซร์",
    "AS Saint-Étienne": "แซงต์ เอเตียน", "Saint-Étienne": "แซงต์ เอเตียน", "St Etienne": "แซงต์ เอเตียน",
    "Angers SCO": "อองเฌ่ร์", "Angers": "อองเฌ่ร์",

    # === Championship (ELC) ===
    "Coventry City FC": "โคเวนทรี่", "Coventry City": "โคเวนทรี่", "Coventry": "โคเวนทรี่",
    "Middlesbrough FC": "มิดเดิลสโบรห์", "Middlesbrough": "มิดเดิลสโบรห์", "Boro": "มิดเดิลสโบรห์",
    "Leeds United FC": "ลีดส์", "Leeds United": "ลีดส์", "Leeds": "ลีดส์",
    "Sunderland AFC": "ซันเดอร์แลนด์", "Sunderland": "ซันเดอร์แลนด์",
    "Norwich City FC": "นอริช", "Norwich City": "นอริช", "Norwich": "นอริช",
    "West Bromwich Albion FC": "เวสต์บรอม", "West Brom": "เวสต์บรอม", "West Bromwich": "เวสต์บรอม",
    "Watford FC": "วัตฟอร์ด", "Watford": "วัตฟอร์ด",
    "Bristol City FC": "บริสตอล ซิตี้", "Bristol City": "บริสตอล ซิตี้",
    "Swansea City AFC": "สวอนซี", "Swansea City": "สวอนซี", "Swansea": "สวอนซี",
    "Hull City FC": "ฮัลล์ ซิตี้", "Hull City": "ฮัลล์ ซิตี้", "Hull": "ฮัลล์ ซิตี้",
    "Stoke City FC": "สโต๊ค ซิตี้", "Stoke City": "สโต๊ค ซิตี้", "Stoke": "สโต๊ค ซิตี้",
    "Millwall FC": "มิลล์วอลล์", "Millwall": "มิลล์วอลล์",
    "Cardiff City FC": "คาร์ดิฟฟ์", "Cardiff City": "คาร์ดิฟฟ์", "Cardiff": "คาร์ดิฟฟ์",
    "Queens Park Rangers FC": "คิวพีอาร์", "QPR": "คิวพีอาร์",
    "Plymouth Argyle FC": "พลีมัธ", "Plymouth Argyle": "พลีมัธ", "Plymouth": "พลีมัธ",
    "Rotherham United FC": "ร็อธเธอร์แฮม", "Rotherham United": "ร็อธเธอร์แฮม", "Rotherham": "ร็อธเธอร์แฮม",
    "Huddersfield Town AFC": "ฮัดเดอร์สฟิลด์", "Huddersfield": "ฮัดเดอร์สฟิลด์",
    "Birmingham City FC": "เบอร์มิ่งแฮม", "Birmingham City": "เบอร์มิ่งแฮม", "Birmingham": "เบอร์มิ่งแฮม",
    "Preston North End FC": "เพรสตัน", "Preston North End": "เพรสตัน", "Preston": "เพรสตัน",
    "Blackburn Rovers FC": "แบล็คเบิร์น", "Blackburn": "แบล็คเบิร์น",
    "Sheffield Wednesday FC": "เชฟฟิลด์ เว้นส์เดย์", "Sheffield Wednesday": "เชฟฟิลด์ เว้นส์เดย์",
    "Derby County FC": "ดาร์บี้ เคาน์ตี้", "Derby County": "ดาร์บี้ เคาน์ตี้", "Derby": "ดาร์บี้ เคาน์ตี้",
    "Portsmouth FC": "พอร์ทสมัธ", "Portsmouth": "พอร์ทสมัธ",
    "Oxford United FC": "อ็อกซ์ฟอร์ด", "Oxford United": "อ็อกซ์ฟอร์ด", "Oxford": "อ็อกซ์ฟอร์ด",

    # === Others / European ===
    "Rio Ave FC": "ริโอ อาเว", "Rio Ave": "ริโอ อาเว",
    "Moreirense FC": "โมเรเรนเซ่", "Moreirense": "โมเรเรนเซ่",
}

LEAGUE_TH = {
    "Premier League": "พรีเมียร์ลีก 🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Primera Division": "ลาลีกา 🇪🇸",
    "La Liga": "ลาลีกา 🇪🇸",
    "Serie A": "เซเรียอา 🇮🇹",
    "Bundesliga": "บุนเดสลีกา 🇩🇪",
    "Ligue 1": "ลีกเอิง 🇫🇷",
    "Championship": "แชมเปี้ยนชิพ อังกฤษ 🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Champions League": "แชมเปี้ยนส์ลีก 🏆",
    "UEFA Champions League": "แชมเปี้ยนส์ลีก 🏆",
    "Europa League": "ยูโรปาลีก 🏆",
    "UEFA Europa League": "ยูโรปาลีก 🏆",
    "Eredivisie": "เอเรดิวิซี่ 🇳🇱",
    "Primeira Liga": "ลีกโปรตุเกส 🇵🇹",
}

LEAGUE_EMOJI = {
    "PL": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "PD": "🇪🇸",
    "SA": "🇮🇹",
    "BL1": "🇩🇪",
    "FL1": "🇫🇷",
    "ELC": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "CL": "🏆",
    "EL": "🏆",
    "DED": "🇳🇱",
    "PPL": "🇵🇹",
}

LEAGUE_CODE_TH = {
    "PL": "พรีเมียร์ลีก",
    "PD": "ลาลีกา",
    "SA": "เซเรียอา",
    "BL1": "บุนเดสลีกา",
    "FL1": "ลีกเอิง",
    "ELC": "แชมเปี้ยนชิพ",
    "CL": "แชมเปี้ยนส์ลีก",
    "EL": "ยูโรปาลีก",
}


def th_name(name):
    """แปลงชื่อทีมเป็นไทย"""
    if name in TEAM_TH:
        return TEAM_TH[name]
    for k, v in TEAM_TH.items():
        if k.lower() in name.lower() or name.lower() in k.lower():
            return v
    return name


def th_league(name):
    """แปลงชื่อลีกเป็นไทย"""
    for k, v in LEAGUE_TH.items():
        if k.lower() in name.lower():
            return v
    return name + " ⚽"


# ===== API cache + rate limit handling =====
API_CACHE_PATH = os.path.join(SCRIPT_DIR, "api_cache.json")
_api_cache_mem = {}
_api_last_call_ts = 0.0


def _cache_load():
    global _api_cache_mem
    if _api_cache_mem:
        return
    try:
        with open(API_CACHE_PATH, "r", encoding="utf-8") as f:
            _api_cache_mem = json.load(f) or {}
    except Exception:
        _api_cache_mem = {}


def _cache_get(path, ttl_seconds=6*60*60):
    _cache_load()
    item = _api_cache_mem.get(path)
    if not item:
        return None
    ts = item.get("ts")
    if not ts:
        return None
    if (datetime.now(timezone.utc).timestamp() - ts) > ttl_seconds:
        return None
    return item.get("data")


def _cache_set(path, data):
    _cache_load()
    _api_cache_mem[path] = {"ts": datetime.now(timezone.utc).timestamp(), "data": data}
    try:
        with open(API_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_api_cache_mem, f, ensure_ascii=False)
    except Exception:
        pass


def api_get(path, *, retries=3, min_interval_s=0.35):
    """Call football-data.org with small rate limiting + retry/backoff.

    - Caches responses to reduce repeat calls (helps 429)
    - Retries 429 with exponential backoff
    """
    cached = _cache_get(path)
    if cached is not None:
        return cached

    import time
    global _api_last_call_ts

    url = f"https://api.football-data.org/v4{path}"
    req = Request(url)
    req.add_header("X-Auth-Token", API_KEY)

    attempt = 0
    while True:
        attempt += 1

        # gentle throttle
        now_ts = time.time()
        wait_s = (_api_last_call_ts + min_interval_s) - now_ts
        if wait_s > 0:
            time.sleep(wait_s)

        try:
            with urlopen(req, timeout=20) as resp:
                _api_last_call_ts = time.time()
                data = json.loads(resp.read().decode())
                _cache_set(path, data)
                return data
        except HTTPError as e:
            _api_last_call_ts = time.time()
            print(f"⚠️ API Error {e.code}: {path}", file=sys.stderr)
            if e.code == 429 and attempt <= retries:
                backoff = min(6.0, 0.8 * (2 ** (attempt - 1)))
                print(f"   Rate limited — รอ {backoff:.1f}s แล้วลองใหม่ (attempt {attempt}/{retries})", file=sys.stderr)
                time.sleep(backoff)
                continue
            return {}
        except URLError as e:
            _api_last_call_ts = time.time()
            print(f"⚠️ Connection Error: {e.reason}", file=sys.stderr)
            return {}


def form_emoji(form_str):
    if not form_str:
        return ""
    return "".join({"W": "🟢", "D": "🟡", "L": "🔴"}.get(c, c) for c in form_str.replace(",", ""))


def form_desc(form_str, team_name):
    """สร้างคำอธิบายฟอร์มแบบไทย"""
    if not form_str:
        return ""
    f = form_str.replace(",", "")
    w = f.count("W")
    d = f.count("D")
    l = f.count("L")

    if w >= 4:
        return f"{team_name} ฟอร์มมาแรง ชนะรวด {w} จาก 5 นัดล่าสุด"
    elif w >= 3:
        return f"{team_name} ฟอร์มดี ชนะ {w} จาก 5 นัด"
    elif l >= 3:
        return f"{team_name} ฟอร์มร่วง แพ้ติด {l} จาก 5 นัด"
    elif l >= 2 and w <= 1:
        return f"{team_name} ฟอร์มไม่ค่อยดี ชนะแค่ {w} แพ้ {l}"
    elif w == 2 and d >= 2:
        return f"{team_name} ฟอร์มปานกลาง ชนะ {w} เสมอ {d}"
    else:
        return f"{team_name} ฟอร์มผสม ชนะ {w} เสมอ {d} แพ้ {l}"


def compute_confidence(home_info, away_info, h2h_matches=None, home_name="", away_name=""):
    """คำนวณความมั่นใจ: 3=เต็งจ๋า, 2=น่าสนใจ, 1=สูสี"""
    score = 0
    if home_info and away_info:
        diff = abs(home_info.get("points", 0) - away_info.get("points", 0))
        pos_diff = abs(home_info.get("position", 10) - away_info.get("position", 10))
        if diff > 25:
            score += 3
        elif diff > 15:
            score += 2
        elif diff > 8:
            score += 1

        # form check
        for info in [home_info, away_info]:
            f = (info.get("form") or "").replace(",", "")
            if f.count("W") >= 4:
                score += 1
            if f.count("L") >= 3:
                score += 1  # clear underdog

        if pos_diff >= 10:
            score += 1

    if score >= 5:
        return 3, "★★★"
    elif score >= 3:
        return 2, "★★"
    else:
        return 1, "★"


def get_confidence_label(level):
    labels = {3: "เต็งจ๋า", 2: "น่าสนใจ", 1: "สูสี/เสี่ยง"}
    return labels.get(level, "")


def parse_utc_date(utc_str):
    """Parse ISO date string to datetime."""
    try:
        return datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    except:
        return None


def format_kick_time(utc_str):
    dt = parse_utc_date(utc_str)
    if dt:
        return dt.astimezone(TZ).strftime("%H:%M")
    return "TBD"


# ===================================================================
# FEATURE 1: Weekly Schedule (--schedule)
# ===================================================================
def weekly_schedule():
    """แสดงโปรแกรมแมตช์ 7 วันข้างหน้า แบ่งตามลีก"""
    date_from = NOW.strftime("%Y-%m-%d")
    date_to = (NOW + timedelta(days=7)).strftime("%Y-%m-%d")

    print("กำลังดึงโปรแกรม 7 วัน...", file=sys.stderr)
    data = api_get(f"/matches?dateFrom={date_from}&dateTo={date_to}")
    matches = data.get("matches", [])

    if not matches:
        return "❌ ไม่พบแมตช์ในช่วง 7 วันข้างหน้า"

    # Group by league
    by_league = {}
    for m in matches:
        comp = m.get("competition", {})
        league_name = comp.get("name", "อื่นๆ")
        league_code = comp.get("code", "")
        key = league_code or league_name
        if key not in by_league:
            by_league[key] = {"name": league_name, "matches": []}
        by_league[key]["matches"].append(m)

    lines = []
    lines.append(f"📅 โปรแกรมแมตช์ 7 วันข้างหน้า")
    lines.append(f"📆 {date_from} ถึง {date_to}")
    lines.append("━" * 30)

    # Sort by league priority
    sorted_leagues = sorted(by_league.keys(),
                            key=lambda x: LEAGUE_PRIORITY.index(x) if x in LEAGUE_PRIORITY else 99)

    for lkey in sorted_leagues:
        info = by_league[lkey]
        league_th = th_league(info["name"])
        emoji = LEAGUE_EMOJI.get(lkey, "⚽")
        lines.append(f"\n{emoji} {league_th}")
        lines.append("─" * 25)

        # Sort matches by date
        sorted_matches = sorted(info["matches"], key=lambda x: x.get("utcDate", ""))

        for m in sorted_matches:
            home_th = th_name(m.get("homeTeam", {}).get("shortName", m.get("homeTeam", {}).get("name", "?")))
            away_th = th_name(m.get("awayTeam", {}).get("shortName", m.get("awayTeam", {}).get("name", "?")))
            utc = m.get("utcDate", "")
            dt = parse_utc_date(utc)
            if dt:
                dt_local = dt.astimezone(TZ)
                day_idx = dt_local.weekday()
                day_name = DAY_NAMES[day_idx]
                date_str = dt_local.strftime(f"%d/%m ({day_name})")
                time_str = dt_local.strftime("%H:%M")
            else:
                date_str = "TBD"
                time_str = "TBD"

            lines.append(f"  📌 {date_str} {time_str} น. — {home_th} vs {away_th}")

    lines.append("")
    lines.append("━" * 30)
    lines.append(_footer())
    return "\n".join(lines)


# ===================================================================
# FEATURE 2: League Standings (--standings LEAGUE_CODE)
# ===================================================================
def league_standings(league_code):
    """ตารางคะแนนแบบเต็ม"""
    code = league_code.upper()
    league_label = LEAGUE_CODE_TH.get(code, code)
    emoji = LEAGUE_EMOJI.get(code, "⚽")

    print(f"กำลังดึงตาราง {league_label}...", file=sys.stderr)
    data = api_get(f"/competitions/{code}/standings")

    if not data or "standings" not in data:
        return f"❌ ไม่สามารถดึงตาราง {league_label} ได้ (รหัส: {code})"

    standings = data.get("standings", [{}])
    # Get total standings (type: TOTAL)
    table = []
    for s in standings:
        if s.get("type") == "TOTAL":
            table = s.get("table", [])
            break
    if not table and standings:
        table = standings[0].get("table", [])

    lines = []
    lines.append(f"{emoji} ตารางคะแนน {league_label}")
    season = data.get("season", {})
    if season:
        lines.append(f"📅 ฤดูกาล {season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]}")
    lines.append("━" * 50)
    lines.append(f"{'#':>2} {'ทีม':<20} {'เล่น':>3} {'ชนะ':>3} {'เสมอ':>3} {'แพ้':>3} {'ได้':>3} {'เสีย':>3} {'+/-':>4} {'คะแนน':>5}")
    lines.append("─" * 50)

    for entry in table:
        pos = entry.get("position", 0)
        team = entry.get("team", {})
        name = th_name(team.get("shortName", team.get("name", "?")))
        played = entry.get("playedGames", 0)
        w = entry.get("won", 0)
        d = entry.get("draw", 0)
        l = entry.get("lost", 0)
        gf = entry.get("goalsFor", 0)
        ga = entry.get("goalsAgainst", 0)
        gd = entry.get("goalDifference", 0)
        pts = entry.get("points", 0)
        form = entry.get("form", "")

        gd_str = f"+{gd}" if gd > 0 else str(gd)
        form_str = f" {form_emoji(form)}" if form else ""

        # Truncate team name for alignment
        if len(name) > 18:
            name = name[:18]

        lines.append(f"{pos:>2} {name:<20} {played:>3} {w:>3} {d:>3} {l:>3} {gf:>3} {ga:>3} {gd_str:>4} {pts:>5}{form_str}")

    lines.append("━" * 50)
    lines.append(_footer())
    return "\n".join(lines)


# ===================================================================
# FEATURE 3: Yesterday's Results (--results)
# ===================================================================
def yesterday_results():
    """ผลบอลเมื่อวาน แบ่งตามลีก"""
    yesterday = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"กำลังดึงผลบอลวันที่ {yesterday}...", file=sys.stderr)
    data = api_get(f"/matches?date={yesterday}")
    matches = data.get("matches", [])

    if not matches:
        return f"❌ ไม่พบผลแมตช์วันที่ {yesterday}"

    # Group by league
    by_league = {}
    for m in matches:
        status = m.get("status", "")
        if status not in ("FINISHED", "AWARDED"):
            continue
        comp = m.get("competition", {})
        league_name = comp.get("name", "อื่นๆ")
        league_code = comp.get("code", "")
        key = league_code or league_name
        if key not in by_league:
            by_league[key] = {"name": league_name, "matches": []}
        by_league[key]["matches"].append(m)

    if not by_league:
        return f"❌ ไม่พบผลแมตช์ที่จบแล้ววันที่ {yesterday}"

    lines = []
    yesterday_dt = NOW - timedelta(days=1)
    day_name = DAY_NAMES[yesterday_dt.weekday()]
    lines.append(f"📊 ผลบอลเมื่อวาน ({day_name}ที่ {yesterday})")
    lines.append("━" * 30)

    sorted_leagues = sorted(by_league.keys(),
                            key=lambda x: LEAGUE_PRIORITY.index(x) if x in LEAGUE_PRIORITY else 99)

    for lkey in sorted_leagues:
        info = by_league[lkey]
        league_th = th_league(info["name"])
        emoji = LEAGUE_EMOJI.get(lkey, "⚽")
        lines.append(f"\n{emoji} {league_th}")
        lines.append("─" * 25)

        for m in info["matches"]:
            home_th = th_name(m.get("homeTeam", {}).get("shortName", m.get("homeTeam", {}).get("name", "?")))
            away_th = th_name(m.get("awayTeam", {}).get("shortName", m.get("awayTeam", {}).get("name", "?")))
            ft = m.get("score", {}).get("fullTime", {})
            hg = ft.get("home", 0) if ft.get("home") is not None else 0
            ag = ft.get("away", 0) if ft.get("away") is not None else 0

            ht = m.get("score", {}).get("halfTime", {})
            ht_str = ""
            if ht and ht.get("home") is not None:
                ht_str = f" (ครึ่งแรก {ht.get('home', 0)}-{ht.get('away', 0)})"

            lines.append(f"  ⚽ {home_th} {hg} - {ag} {away_th}{ht_str}")

    lines.append("")
    lines.append("━" * 30)
    lines.append(_footer())
    return "\n".join(lines)


# ===================================================================
# FEATURE 4: Top Scorers (--scorers LEAGUE_CODE)
# ===================================================================
def top_scorers(league_code):
    """ดาวซัลโว 10 อันดับแรก"""
    code = league_code.upper()
    league_label = LEAGUE_CODE_TH.get(code, code)
    emoji = LEAGUE_EMOJI.get(code, "⚽")

    print(f"กำลังดึงดาวซัลโว {league_label}...", file=sys.stderr)
    data = api_get(f"/competitions/{code}/scorers?limit=10")

    if not data or "scorers" not in data:
        return f"❌ ไม่สามารถดึงข้อมูลดาวซัลโว {league_label} ได้"

    scorers = data.get("scorers", [])

    lines = []
    lines.append(f"{emoji} ดาวซัลโว {league_label} — Top 10")
    season = data.get("season", {})
    if season:
        lines.append(f"📅 ฤดูกาล {season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]}")
    lines.append("━" * 40)
    lines.append(f"{'#':>2} {'ผู้เล่น':<22} {'ทีม':<15} {'ประตู':>4} {'แอสซิสต์':>7}")
    lines.append("─" * 40)

    for i, s in enumerate(scorers, 1):
        player = s.get("player", {})
        player_name = player.get("name", "?")
        team = s.get("team", {})
        team_name = th_name(team.get("shortName", team.get("name", "?")))
        goals = s.get("goals", 0) or 0
        assists = s.get("assists", 0) or 0

        # Medal emoji for top 3
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i:>2}")

        lines.append(f"{rank_emoji} {player_name:<22} {team_name:<15} {goals:>4} {assists:>7}")

    lines.append("━" * 40)
    lines.append(_footer())
    return "\n".join(lines)


# ===================================================================
# FEATURE 7: Parlay Tips (--parlay)
# ===================================================================
def parlay_tips():
    """แนะนำบิลรวม 3-5 คู่จากแมตช์วันนี้"""
    print("กำลังวิเคราะห์บิลรวม...", file=sys.stderr)
    data = api_get("/matches")
    matches = data.get("matches", [])

    if not matches:
        return "❌ ไม่พบแมตช์วันนี้สำหรับบิลรวม"

    # Collect match data with confidence
    candidates = []
    for m in matches:
        comp = m.get("competition", {})
        comp_code = comp.get("code", "")
        home = m.get("homeTeam", {})
        away = m.get("awayTeam", {})
        home_full = home.get("name", "?")
        away_full = away.get("name", "?")
        home_th = th_name(home.get("shortName", home_full))
        away_th = th_name(away.get("shortName", away_full))

        # Get standings for confidence calc
        home_info = None
        away_info = None
        if comp_code:
            try:
                sd = api_get(f"/competitions/{comp_code}/standings")
                table = sd.get("standings", [{}])[0].get("table", [])
                for entry in table:
                    t = entry.get("team", {}).get("name", "")
                    if t.lower() == home_full.lower():
                        home_info = entry
                    if t.lower() == away_full.lower():
                        away_info = entry
            except:
                pass

        level, stars = compute_confidence(home_info, away_info)

        if home_info and away_info:
            h_pts = home_info.get("points", 0)
            a_pts = away_info.get("points", 0)
            h_pos = home_info.get("position", 99)
            a_pos = away_info.get("position", 99)

            if h_pts > a_pts:
                fav = home_th
                fav_pos = h_pos
                und = away_th
                tip = f"{home_th} ชนะ (เหย้า + อันดับดีกว่า)"
            elif a_pts > h_pts:
                fav = away_th
                fav_pos = a_pos
                und = home_th
                tip = f"{away_th} ชนะ (อันดับดีกว่า แม้เล่นเยือน)"
            else:
                fav = home_th
                fav_pos = h_pos
                tip = f"{home_th} ชนะ (ได้เปรียบเหย้า)"
        else:
            fav = home_th
            fav_pos = 99
            tip = f"{home_th} ชนะ (เหย้า)"

        candidates.append({
            "home_th": home_th,
            "away_th": away_th,
            "league": th_league(comp.get("name", "")),
            "level": level,
            "stars": stars,
            "tip": tip,
            "fav": fav,
            "kick": format_kick_time(m.get("utcDate", "")),
        })

    # Sort by confidence (highest first), pick top 3-5
    candidates.sort(key=lambda x: x["level"], reverse=True)
    picks = candidates[:min(5, max(3, len(candidates)))]

    if len(picks) < 3:
        picks = candidates[:len(candidates)]

    lines = []
    lines.append("🎯 บิลรวมแนะนำวันนี้ (Parlay Tips)")
    lines.append(f"📅 วัน{DAY_TH}ที่ {DATE_TH}")
    lines.append("━" * 30)

    for i, p in enumerate(picks, 1):
        lines.append(f"\n{i}. {p['stars']} {p['home_th']} vs {p['away_th']}")
        lines.append(f"   🏆 {p['league']} | ⏰ {p['kick']} น.")
        lines.append(f"   💡 ทิป: {p['tip']}")

    lines.append(f"\n{'━' * 30}")
    lines.append(f"📊 จำนวนคู่: {len(picks)} คู่")
    high_conf = sum(1 for p in picks if p["level"] >= 2)
    lines.append(f"🔥 ความมั่นใจสูง: {high_conf}/{len(picks)} คู่")
    lines.append("")
    lines.append("⚠️ บิลรวมเสี่ยงสูง เล่นด้วยเงินที่เสียได้เท่านั้น!")
    lines.append(_footer())
    return "\n".join(lines)


# ===================================================================
# FEATURE 8: Weekly Summary (--summary)
# ===================================================================
def daily_pick_summary(target_date=None):
    """สรุปผลทีเด็ดรายวันแบบเข้า/พลาด/รอผล"""
    logs = update_prediction_results()
    target_date = target_date or TODAY
    rows = [x for x in logs if x.get("date") == target_date and x.get("pick_type")]
    if not rows:
        return f"❌ ไม่มีข้อมูลทีเด็ดวันที่ {target_date}"

    correct = sum(1 for x in rows if x.get("correct") is True)
    wrong = sum(1 for x in rows if x.get("correct") is False)
    pending = sum(1 for x in rows if x.get("correct") is None)
    decided = correct + wrong
    rate = (correct / decided * 100) if decided else 0

    lines = []
    lines.append(f"📊 สรุปทีเด็ดวันที่ {target_date}")
    lines.append("━" * 30)
    lines.append(f"✅ เข้า: {correct}")
    lines.append(f"❌ พลาด: {wrong}")
    lines.append(f"⏳ รอผล: {pending}")
    if decided:
        lines.append(f"🎯 Win rate: {rate:.0f}%")
    lines.append("")
    for row in rows:
        icon = "✅" if row.get("correct") is True else ("❌" if row.get("correct") is False else "⏳")
        conf = row.get("confidence_stars", "")
        actual = row.get("actual") or "-"
        lines.append(f"{icon} {row.get('home')} vs {row.get('away')}")
        lines.append(f"   ทีเด็ด: {row.get('prediction')} {conf}")
        lines.append(f"   ผลจริง: {actual}")
    lines.append("")
    lines.append("━" * 30)
    lines.append(_footer())
    return "\n".join(lines)

def weekly_summary():
    """เปรียบเทียบทำนาย vs ผลจริง (อ่านจาก results_log.json)"""
    update_prediction_results()
    if not os.path.exists(RESULTS_LOG):
        return "❌ ไม่พบไฟล์ results_log.json — ยังไม่มีข้อมูลทำนายก่อนหน้า"

    try:
        with open(RESULTS_LOG, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except:
        return "❌ ไม่สามารถอ่าน results_log.json ได้"

    if not logs:
        return "❌ ไม่มีข้อมูลในไฟล์ results_log.json"

    # Only look at last 7 days
    cutoff = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [l for l in logs if l.get("date", "") >= cutoff]

    if not recent:
        return "❌ ไม่มีข้อมูลทำนายใน 7 วันที่ผ่านมา"

    total = len(recent)
    correct = sum(1 for l in recent if l.get("correct") is True)
    wrong = sum(1 for l in recent if l.get("correct") is False)
    pending = sum(1 for l in recent if l.get("correct") is None)

    lines = []
    lines.append("📈 สรุปผลทำนาย 7 วันที่ผ่านมา")
    lines.append("━" * 30)
    decided = correct + wrong
    rate = (correct / decided * 100) if decided else 0
    lines.append(f"✅ ถูก: {correct}/{decided or total} ({rate:.0f}%)")
    lines.append(f"❌ พลาด: {wrong}/{decided or total}")
    lines.append(f"⏳ รอผล: {pending}")
    lines.append("")

    for l in recent:
        date = l.get("date", "?")
        home = l.get("home", "?")
        away = l.get("away", "?")
        pred = l.get("prediction", "?")
        actual = l.get("actual", "?")
        ok = "✅" if l.get("correct") is True else ("❌" if l.get("correct") is False else "⏳")
        lines.append(f"{ok} {date}: {home} vs {away}")
        lines.append(f"   ทำนาย: {pred} | ผลจริง: {actual or '-'}")

    lines.append("")
    lines.append("━" * 30)
    lines.append(_footer())
    return "\n".join(lines)


def save_predictions_to_log(matches_data):
    """บันทึกทำนายลง results_log.json"""
    save_prediction_records(matches_data)
    update_prediction_results()


# ===================================================================
# Original Analysis
# ===================================================================
def write_analysis(match, standings, h2h_matches, rated=False):
    """เขียนวิเคราะห์ 1 คู่แบบไทย"""
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    home_full = home.get("name", "?")
    away_full = away.get("name", "?")
    home_th = th_name(home.get("shortName", home_full))
    away_th = th_name(away.get("shortName", away_full))
    comp_th = th_league(match.get("competition", {}).get("name", ""))

    kick = format_kick_time(match.get("utcDate", ""))

    lines = []
    lines.append(f"⚽ {home_th} vs {away_th}")
    lines.append(f"🏆 {comp_th}")
    lines.append(f"⏰ เวลาเตะ {kick} น.")
    lines.append("")

    # หาข้อมูลตาราง
    home_info = None
    away_info = None
    for entry in standings:
        t = entry.get("team", {}).get("name", "")
        if t.lower() == home_full.lower():
            home_info = entry
        if t.lower() == away_full.lower():
            away_info = entry

    # Confidence rating
    if rated:
        level, stars = compute_confidence(home_info, away_info, h2h_matches, home_th, away_th)
        label = get_confidence_label(level)
        lines.append(f"🎯 ความมั่นใจ: {stars} ({label})")
        lines.append("")

    # สถานการณ์ทั้ง 2 ทีม
    lines.append("📊 สถานการณ์:")
    if home_info:
        pos = home_info.get("position", "?")
        pts = home_info.get("points", 0)
        w = home_info.get("won", 0)
        d = home_info.get("draw", 0)
        l = home_info.get("lost", 0)
        gf = home_info.get("goalsFor", 0)
        ga = home_info.get("goalsAgainst", 0)
        form = home_info.get("form", "")

        lines.append(f"🏠 {home_th} — อันดับ {pos} ({pts} คะแนน)")
        lines.append(f"   ชนะ {w} เสมอ {d} แพ้ {l} | ยิงได้ {gf} เสีย {ga}")
        if form:
            lines.append(f"   ฟอร์ม 5 นัด: {form_emoji(form)}")

    if away_info:
        pos = away_info.get("position", "?")
        pts = away_info.get("points", 0)
        w = away_info.get("won", 0)
        d = away_info.get("draw", 0)
        l = away_info.get("lost", 0)
        gf = away_info.get("goalsFor", 0)
        ga = away_info.get("goalsAgainst", 0)
        form = away_info.get("form", "")

        lines.append(f"✈️ {away_th} — อันดับ {pos} ({pts} คะแนน)")
        lines.append(f"   ชนะ {w} เสมอ {d} แพ้ {l} | ยิงได้ {gf} เสีย {ga}")
        if form:
            lines.append(f"   ฟอร์ม 5 นัด: {form_emoji(form)}")

    lines.append("")

    # สถิติเจอกัน
    hw, dw, aw = 0, 0, 0
    if h2h_matches:
        lines.append("🔄 เจอกัน 5 นัดหลังสุด:")
        for hm in h2h_matches[:5]:
            ht = th_name(hm.get("homeTeam", {}).get("shortName", hm.get("homeTeam", {}).get("name", "?")))
            at = th_name(hm.get("awayTeam", {}).get("shortName", hm.get("awayTeam", {}).get("name", "?")))
            ft = hm.get("score", {}).get("fullTime", {})
            hg = ft.get("home", 0) or 0
            ag = ft.get("away", 0) or 0

            if hg > ag:
                winner_name = hm.get("homeTeam", {}).get("name", "")
            elif ag > hg:
                winner_name = hm.get("awayTeam", {}).get("name", "")
            else:
                winner_name = "draw"

            if winner_name == "draw":
                dw += 1
            elif winner_name.lower() == home_full.lower():
                hw += 1
            else:
                aw += 1

            lines.append(f"   • {ht} {hg}-{ag} {at}")

        lines.append(f"   สรุป: {home_th} ชนะ {hw} เสมอ {dw} {away_th} ชนะ {aw}")
        lines.append("")

    # วิเคราะห์เป็นย่อหน้า (แบบนักวิเคราะห์บอลไทย)
    lines.append("💡 วิเคราะห์:")

    analysis_parts = []

    if home_info and away_info:
        h_pts = home_info.get("points", 0)
        a_pts = away_info.get("points", 0)
        h_pos = home_info.get("position", 99)
        a_pos = away_info.get("position", 99)
        h_gf = home_info.get("goalsFor", 0)
        a_gf = away_info.get("goalsFor", 0)
        h_ga = home_info.get("goalsAgainst", 0)
        a_ga = away_info.get("goalsAgainst", 0)
        diff = h_pts - a_pts
        h_form = (home_info.get("form") or "").replace(",", "")
        a_form = (away_info.get("form") or "").replace(",", "")
        h_games = home_info.get("won", 0) + home_info.get("draw", 0) + home_info.get("lost", 0)
        a_games = away_info.get("won", 0) + away_info.get("draw", 0) + away_info.get("lost", 0)

        # ฟอร์ม
        h_desc = form_desc(h_form, home_th)
        a_desc = form_desc(a_form, away_th)
        if h_desc:
            analysis_parts.append(h_desc)
        if a_desc:
            analysis_parts.append(a_desc)

        # ยิงประตู
        if h_games > 0:
            h_avg = h_gf / h_games
            if h_avg >= 2.0:
                analysis_parts.append(f"{home_th} เน้นบุก ยิงเฉลี่ย {h_avg:.1f} ลูกต่อนัด")
            elif h_avg <= 0.8:
                analysis_parts.append(f"{home_th} ยิงได้น้อย เฉลี่ยแค่ {h_avg:.1f} ลูกต่อนัด")
        if a_games > 0:
            a_avg = a_gf / a_games
            if a_avg >= 2.0:
                analysis_parts.append(f"{away_th} บุกหนัก ยิงเฉลี่ย {a_avg:.1f} ลูกต่อนัด")

        # แนวรับ
        if h_games > 0 and h_ga / h_games < 0.8:
            analysis_parts.append(f"{home_th} รับแน่น เสียเฉลี่ยแค่ {h_ga/h_games:.1f} ลูกต่อนัด")
        if a_games > 0 and a_ga / a_games < 0.8:
            analysis_parts.append(f"{away_th} แนวรับดี เสียเฉลี่ย {a_ga/a_games:.1f} ลูกต่อนัด")

        # H2H context
        if h2h_matches:
            if hw >= 4:
                analysis_parts.append(f"สถิติเจอกัน {home_th} ขยี้ ชนะ {hw} จาก 5 นัด")
            elif aw >= 4:
                analysis_parts.append(f"สถิติเจอกัน {away_th} ครองสถิติ ชนะ {aw} จาก 5 นัด")

        # สรุป
        if abs(diff) > 20:
            fav = home_th if diff > 0 else away_th
            if diff > 0:
                analysis_parts.append(f"สรุป: {fav} เต็งจ๋า เล่นเหย้า + คะแนนห่างกัน {abs(diff)} แต้ม น่าเก็บ 3 คะแนนได้")
            else:
                analysis_parts.append(f"สรุป: {fav} เต็งหนัก แม้เล่นเยือนแต่คะแนนห่างกัน {abs(diff)} แต้ม น่าจะคุมเกมได้")
        elif abs(diff) > 10:
            fav = home_th if diff > 0 else away_th
            if diff > 0:
                analysis_parts.append(f"สรุป: {fav} ได้เปรียบเล่นเหย้า + อันดับดีกว่า เต็งเบาๆ")
            else:
                analysis_parts.append(f"สรุป: {fav} อันดับดีกว่า แต่เล่นนอกบ้าน ระวังสะดุด")
        else:
            analysis_parts.append(f"สรุป: คู่นี้พอฟัดพอเหวี่ยง ต้องดูฟอร์มวันจริงประกอบ")

        # สูง-ต่ำ
        if h_games > 0 and a_games > 0:
            total_avg = (h_gf / h_games + a_gf / a_games)
            if total_avg > 3.5:
                analysis_parts.append(f"เกมนี้น่ามีประตูเยอะ ทั้งคู่บุกหนัก ลุ้นสูง 💥")
            elif total_avg > 2.5:
                analysis_parts.append(f"น่ามีประตู ทั้งคู่ยิงพอได้ ลุ้นสูง")
            elif total_avg < 1.5:
                analysis_parts.append(f"เกมนี้น่าจะประตูน้อย ทั้งคู่เน้นรับ ลุ้นต่ำ")

    for part in analysis_parts:
        lines.append(f"• {part}")

    return "\n".join(lines)


def select_matches(matches, count=2):
    """เลือกแมตช์ตามลำดับลีกสำคัญ"""
    prioritized = []
    other = []

    for m in matches:
        comp_code = m.get("competition", {}).get("code", "")
        if comp_code in LEAGUE_PRIORITY:
            prio = LEAGUE_PRIORITY.index(comp_code)
            prioritized.append((prio, m))
        else:
            other.append((99, m))

    prioritized.sort(key=lambda x: x[0])
    all_sorted = prioritized + other
    return [m for _, m in all_sorted[:count]]


def _footer():
    """ branding footer"""
    return (
        "\n💰 เดิมพันอย่างมีสติ ดูฟอร์ม+สถิติประกอบ\n"
        "⚠️ วิเคราะห์ประกอบการตัดสินใจเท่านั้น\n"
        "\n"
        "🔥 แทงบอลออนไลน์ ค่าน้ำดีที่สุด\n"
        "👉 .com — ฝากถอนออโต้ 24 ชม."
    )



def build_step_tips(pred_rows):
    ordered = sorted(pred_rows, key=lambda x: (-x.get("confidence", 0), x.get("home", "")))
    single = ordered[0] if ordered else None
    step = ordered[: min(3, len(ordered))]
    return single, step


def pre_match_post(count=3, rated=True):
    print("กำลังดึงข้อมูลทีเด็ดวันนี้...", file=sys.stderr)
    data = api_get("/matches")
    matches = data.get("matches", [])
    if not matches:
        return "❌ ไม่พบแมตช์วันนี้"
    target = select_matches(matches, max(count, 3))
    predictions = []
    for m in target:
        comp_code = m.get("competition", {}).get("code", "")
        mid = m.get("id")
        standings = []
        if comp_code:
            try:
                sd = api_get(f"/competitions/{comp_code}/standings")
                table_data = sd.get("standings", [])
                for st in table_data:
                    if st.get("type") == "TOTAL":
                        standings = st.get("table", [])
                        break
                if not standings and table_data:
                    standings = table_data[0].get("table", [])
            except:
                pass
        h2h = []
        if mid:
            try:
                hd = api_get(f"/matches/{mid}/head2head?limit=5")
                h2h = hd.get("matches", [])
            except:
                pass
        home_full = m.get("homeTeam", {}).get("name", "?")
        away_full = m.get("awayTeam", {}).get("name", "?")
        home_th = th_name(m.get("homeTeam", {}).get("shortName", home_full))
        away_th = th_name(m.get("awayTeam", {}).get("shortName", away_full))
        home_info = next((entry for entry in standings if entry.get("team", {}).get("name", "").lower() == home_full.lower()), None)
        away_info = next((entry for entry in standings if entry.get("team", {}).get("name", "").lower() == away_full.lower()), None)
        pick = infer_pick(home_info, away_info, h2h, home_th, away_th)
        confidence_level, confidence_stars = compute_confidence(home_info, away_info, h2h, home_th, away_th)
        predictions.append({
            "date": local_match_date(m),
            "home": home_th,
            "away": away_th,
            "prediction": pick["label"],
            "pick_type": pick["pick_type"],
            "pick_value": pick["pick_value"],
            "confidence": confidence_level,
            "confidence_stars": confidence_stars,
            "league": comp_code,
            "kick": format_kick_time(m.get("utcDate", "")),
        })
    save_predictions_to_log([{**x, "actual": "", "correct": None} for x in predictions])
    single, step = build_step_tips(predictions)
    lines = []
    lines.append("⚽ ทีเด็ดบอลวันนี้")
    lines.append(f"📅 วัน{DAY_TH}ที่ {DATE_TH}")
    lines.append("━" * 28)
    if single:
        lines.append("🔥 ตัวเต็ง")
        lines.append(f"• {single['home']} vs {single['away']}")
        lines.append(f"  ทีเด็ด: {single['prediction']} {single['confidence_stars']}")
        lines.append(f"  เวลา: {single['kick']} น.")
        lines.append("")
    if step:
        lines.append("🧾 สเต็ปแนะนำ")
        for i, row in enumerate(step, 1):
            lines.append(f"{i}. {row['home']} vs {row['away']} — {row['prediction']} {row['confidence_stars']}")
        lines.append("")
    lines.append("📌 คู่คัดทั้งหมด")
    for row in predictions[:count]:
        lines.append(f"• {row['home']} vs {row['away']} — {row['prediction']} {row['confidence_stars']}")
    lines.append("")
    lines.append(_footer())
    return "\n".join(lines)

def run_daily_analysis(count=2, rated=False):
    """วิเคราะห์แมตช์วันนี้ (default)"""
    print("กำลังดึงข้อมูลแมตช์วันนี้...", file=sys.stderr)

    data = api_get("/matches")
    matches = data.get("matches", [])
    print(f"พบ {len(matches)} แมตช์", file=sys.stderr)

    if not matches:
        return "❌ ไม่พบแมตช์วันนี้"

    target = select_matches(matches, count)

    # Header
    output_lines = []
    output_lines.append(f"⚽ บทวิเคราะห์บอลวันนี้")
    output_lines.append(f"📅 วัน{DAY_TH}ที่ {DATE_TH}")
    if count != 2:
        output_lines.append(f"📌 วิเคราะห์ {len(target)} คู่เด็ด")
    output_lines.append("━" * 28)

    predictions = []

    for m in target:
        comp_code = m.get("competition", {}).get("code", "")
        mid = m.get("id")

        # ดึง standings
        standings = []
        if comp_code:
            try:
                sd = api_get(f"/competitions/{comp_code}/standings")
                table_data = sd.get("standings", [])
                for s in table_data:
                    if s.get("type") == "TOTAL":
                        standings = s.get("table", [])
                        break
                if not standings and table_data:
                    standings = table_data[0].get("table", [])
            except:
                pass

        # ดึง H2H
        h2h = []
        if mid:
            try:
                hd = api_get(f"/matches/{mid}/head2head?limit=5")
                h2h = hd.get("matches", [])
            except:
                pass

        analysis = write_analysis(m, standings, h2h, rated=rated)
        output_lines.append("")
        output_lines.append(analysis)

        # Save prediction for log
        home_full = m.get("homeTeam", {}).get("name", "?")
        away_full = m.get("awayTeam", {}).get("name", "?")
        home_th = th_name(m.get("homeTeam", {}).get("shortName", home_full))
        away_th = th_name(m.get("awayTeam", {}).get("shortName", away_full))
        home_info = next((entry for entry in standings if entry.get("team", {}).get("name", "").lower() == home_full.lower()), None)
        away_info = next((entry for entry in standings if entry.get("team", {}).get("name", "").lower() == away_full.lower()), None)
        pick = infer_pick(home_info, away_info, h2h, home_th, away_th)
        confidence_level, confidence_stars = compute_confidence(home_info, away_info, h2h, home_th, away_th)
        predictions.append({
            "date": local_match_date(m),
            "home": home_th,
            "away": away_th,
            "prediction": pick["label"],
            "pick_type": pick["pick_type"],
            "pick_value": pick["pick_value"],
            "confidence": confidence_level,
            "confidence_stars": confidence_stars,
            "league": comp_code,
            "actual": "",
            "correct": None,
        })

    output_lines.append("")
    output_lines.append("━" * 28)
    output_lines.append(_footer())

    # Save predictions to log
    save_predictions_to_log(predictions)

    return "\n".join(output_lines)


# ===================================================================
# CLI Entry Point
# ===================================================================
def main():
    parser = argparse.ArgumentParser(
        description=" Thai Football Analysis v5 — วิเคราะห์บอลภาษาไทย",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:
  python thai_analysis_gen.py                  วิเคราะห์ 2 คู่วันนี้ (default)
  python thai_analysis_gen.py --count 5        วิเคราะห์ 5 คู่
  python thai_analysis_gen.py --rated           เพิ่มระดับความมั่นใจ ★
  python thai_analysis_gen.py --schedule        โปรแกรม 7 วัน
  python thai_analysis_gen.py --standings PL    ตาราง พรีเมียร์ลีก
  python thai_analysis_gen.py --results         ผลบอลเมื่อวาน
  python thai_analysis_gen.py --scorers PL      ดาวซัลโว พรีเมียร์ลีก
  python thai_analysis_gen.py --parlay          บิลรวมแนะนำ
  python thai_analysis_gen.py --summary         สรุปผลทำนาย 7 วัน

รหัสลีก: PL (พรีเมียร์), PD (ลาลีกา), SA (เซเรียอา), BL1 (บุนเดส), FL1 (ลีกเอิง), ELC (แชมเปี้ยนชิพ)
        """
    )

    parser.add_argument("--schedule", action="store_true",
                        help="โปรแกรมแมตช์ 7 วันข้างหน้า")
    parser.add_argument("--standings", metavar="LEAGUE_CODE",
                        help="ตารางคะแนน (PL, PD, SA, BL1, FL1, ELC)")
    parser.add_argument("--results", action="store_true",
                        help="ผลบอลเมื่อวาน")
    parser.add_argument("--scorers", metavar="LEAGUE_CODE",
                        help="ดาวซัลโว Top 10 (PL, PD, SA, BL1, FL1, ELC)")
    parser.add_argument("--count", type=int, default=2,
                        help="จำนวนแมตช์ที่จะวิเคราะห์ (default: 2)")
    parser.add_argument("--rated", action="store_true",
                        help="เพิ่มระดับความมั่นใจ ★★★/★★/★")
    parser.add_argument("--parlay", action="store_true",
                        help="แนะนำบิลรวม 3-5 คู่")
    parser.add_argument("--summary", action="store_true",
                        help="สรุปผลทำนาย vs ผลจริง 7 วัน")
    parser.add_argument("--daily-summary", action="store_true",
                        help="สรุปผลทีเด็ดรายวัน")
    parser.add_argument("--pre-match-post", action="store_true",
                        help="โพสต์ก่อนแข่งแบบ ทีเด็ด/ตัวเต็ง/สเต็ป")
    parser.add_argument("--date", help="วันที่เป้าหมาย YYYY-MM-DD")

    args = parser.parse_args()

    # Dispatch
    if args.schedule:
        output = weekly_schedule()
    elif args.standings:
        output = league_standings(args.standings)
    elif args.results:
        output = yesterday_results()
    elif args.scorers:
        output = top_scorers(args.scorers)
    elif args.parlay:
        output = parlay_tips()
    elif args.summary:
        output = weekly_summary()
    elif args.daily_summary:
        output = daily_pick_summary(args.date or TODAY)
    elif args.pre_match_post:
        output = pre_match_post(count=args.count, rated=args.rated)
    else:
        # Default: daily analysis
        output = run_daily_analysis(count=args.count, rated=args.rated)

    print(output)

    # Save output
    out_path = os.path.join(SCRIPT_DIR, "thai_analysis.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\nบันทึกไว้ที่ {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
