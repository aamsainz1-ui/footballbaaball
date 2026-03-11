---
name: football-daily-analyst
description: Generate daily Thai-language football match analysis with betting insights. Use when the user asks for "วิเคราะห์บอล", "ทีเด็ดบอล", "football analysis", "match prediction", "บอลวันนี้", daily football tips, or automated match analysis posting to Telegram. Pulls live data from football-data.org API, translates to Thai team/league names, generates paragraph-style analysis with Thai football terminology, and posts to Telegram with  branding.
---

# Football Daily Analyst

Generate Thai-language football match analysis from live API data and post to Telegram.

## Quick Start

Run the analysis script:

```bash
python scripts/thai_analysis_gen.py
```

Output goes to stdout and saves to `thai_analysis.txt` in the script directory.

## How It Works

1. **Fetch matches** from football-data.org API (`/v4/matches` for today)
2. **Fetch standings** for each match's competition (`/v4/competitions/{code}/standings`)
3. **Fetch H2H** for each match (`/v4/matches/{id}/head2head?limit=5`)
4. **Translate** team/league names to Thai using built-in dictionaries
5. **Generate analysis** in Thai paragraph style with form indicators, goal averages, and betting insights
6. **Format output** with emoji,  branding, and proper Thai football terminology

## Environment

- `FOOTBALLDATA_KEY` — API key for football-data.org (required)

## Match Selection

Default: selects top 2 matches prioritizing major leagues (La Liga, Premier League, Serie A, etc.).

To analyze specific matches or more matches, modify the selection logic in the script or pass arguments.

## Output Format

```
⚽ บทวิเคราะห์บอลวันนี้
📅 วัน[DAY]ที่ DD/MM/YYYY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚽ [เหย้า] vs [เยือน]
🏆 [ลีก]
⏰ เวลาเตะ HH:MM น.

📊 สถานการณ์: (อันดับ, คะแนน, ฟอร์ม)
🔄 เจอกัน 5 นัดหลังสุด: (ผลสกอร์)
💡 วิเคราะห์: (ย่อหน้าภาษาไทย)

💰 เดิมพันอย่างมีสติ
👉 .com
```

## Thai Translation

- Team/league names use Thai dict (`TEAM_TH`, `LEAGUE_TH`) — see `references/thai-football-glossary.md` for full glossary
- Add new teams to `TEAM_TH` dict in the script when encountering unknown teams
- Form indicators: 🟢=Win 🟡=Draw 🔴=Loss

## Posting to Telegram

After generating, send to Telegram group using OpenClaw message tool:

```
message action=send target="-1003869825051" message="[analysis text]"
```

## Cron Integration

Set up daily cron job (isolated agentTurn) to auto-generate and post:

```
Schedule: cron "0 9 * * *" Asia/Bangkok (9:00 AM daily)
Task: "Run football-daily-analyst skill: execute thai_analysis_gen.py, then send output to Telegram group -1003869825051"
```

## Extending

- **Add teams**: Add entries to `TEAM_TH` dict in the script
- **Add leagues**: Add entries to `LEAGUE_TH` dict
- **More matches**: Change `target = target[:2]` to higher number
- **Different leagues**: Modify the selection filter in `__main__`
