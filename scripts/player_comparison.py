"""Compare two players using per-90 stats from JSON."""

import argparse
import io
import json
import sys
from typing import Dict, Any

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from thai_analysis_gen import TEAM_TH  # type: ignore
except Exception:  # pragma: no cover
    TEAM_TH = {}

KEY_FIELDS = [
    ("goals", "ประตู"),
    ("assists", "แอสซิสต์"),
    ("shots", "ยิงทั้งหมด"),
    ("shots_on_target", "ยิงตรงกรอบ"),
    ("key_passes", "คีย์พาส"),
    ("progressive_carries", "ลากบอลทะลุ"),
    ("progressive_passes", "จ่ายทะลุ"),
    ("tackles_won", "แท็คเกิลสำเร็จ"),
    ("interceptions", "ตัดบอล"),
    ("pressures", "เพรสซิ่ง"),
    ("duels_won", "ชนะดวล"),
]


def load_stats(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def per90(value: float, minutes: float) -> float:
    if not minutes:
        return 0.0
    return (value / minutes) * 90


def render_player(name: str, data: Dict[str, Any]) -> str:
    team = TEAM_TH.get(data.get("team", ""), data.get("team", "ไม่ระบุ"))
    pos = data.get("position", "-")
    minutes = data.get("minutes", 0)
    lines = [f"{name} ({team} | {pos}) นาที {minutes}"]
    for key, label in KEY_FIELDS:
        if key in data:
            val = per90(float(data[key]), minutes)
            if val:
                lines.append(f"  • {label}: {val:.2f}/90")
    if data.get("notes"):
        lines.append(f"  • หมายเหตุ: {data['notes']}")
    return "\n".join(lines)


def highlight_edge(player_a: str, player_b: str, stats_a: Dict[str, Any], stats_b: Dict[str, Any]) -> None:
    print("\n🔥 จุดเด่น")
    minutes_a = stats_a.get("minutes", 0) or 1
    minutes_b = stats_b.get("minutes", 0) or 1
    edges = []
    for key, label in KEY_FIELDS[:6]:
        if key in stats_a and key in stats_b:
            a_val = per90(float(stats_a[key]), minutes_a)
            b_val = per90(float(stats_b[key]), minutes_b)
            diff = a_val - b_val
            if abs(diff) >= 0.3:
                winner = player_a if diff > 0 else player_b
                edges.append(f"• {label}: {winner} เหนือกว่า {abs(diff):.2f}/90")
    if edges:
        print("\n".join(edges))
    else:
        print("รูปเกมสูสี ใช้แผนแท็คติกประกอบการตัดสินใจ")


def main() -> None:
    parser = argparse.ArgumentParser(description="เทียบสถิติผู้เล่น 2 คน")
    parser.add_argument("--stats-file", required=True, help="ไฟล์ JSON ที่เก็บข้อมูลผู้เล่น")
    parser.add_argument("--player-a", required=True)
    parser.add_argument("--player-b", required=True)
    args = parser.parse_args()

    data = load_stats(args.stats_file)
    try:
        player_a = data[args.player_a]
        player_b = data[args.player_b]
    except KeyError as exc:  # pragma: no cover
        raise SystemExit(f"ไม่พบ {exc.args[0]} ในไฟล์ {args.stats_file}")

    print("⚖️ เปรียบเทียบผู้เล่น")
    print("━━━━━━━━━━━━━━━━")
    print(render_player(args.player_a, player_a))
    print("\nvs\n")
    print(render_player(args.player_b, player_b))

    highlight_edge(args.player_a, args.player_b, player_a, player_b)
    print("\n💡 ใช้อ้างอิงเขียนบทวิเคราะห์ + เลือก Anytime Scorer / Man of the Match")


if __name__ == "__main__":
    main()
