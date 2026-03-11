"""Quick implied probability + value check helper."""

import argparse
import io
import sys

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def implied(decimal: float) -> float:
    return 1.0 / decimal if decimal > 0 else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="คำนวณค่าเปอร์เซ็นต์จากราคา (decimal)")
    parser.add_argument("--home", type=float, required=True, help="ราคาทีมเหย้า เช่น 1.85")
    parser.add_argument("--draw", type=float, help="ราคาเสมอ")
    parser.add_argument("--away", type=float, required=True, help="ราคาทีมเยือน เช่น 4.20")
    parser.add_argument("--model-home", type=float, help="เปอร์เซ็นต์โมเดล (0-100)")
    parser.add_argument("--model-draw", type=float)
    parser.add_argument("--model-away", type=float)
    parser.add_argument("--line", type=float, help="O/U line เพื่ออ้างอิงตอนสรุป")
    parser.add_argument("--handicap", type=float, help="ราคาต่อเอเชียนแฮนดิแคป เช่น -0.5")
    args = parser.parse_args()

    probs = {
        "home": implied(args.home),
        "draw": implied(args.draw) if args.draw else 0.0,
        "away": implied(args.away),
    }
    total = sum(v for v in probs.values() if v)
    margin = (total - 1.0) * 100

    print("📈 Implied Probability (รวมค่า water)")
    for key, odd in (("เหย้า", args.home), ("เสมอ", args.draw), ("เยือน", args.away)):
        if odd:
            prob = implied(odd) * 100
            print(f"• {key} @ {odd:.2f} → {prob:.2f}%")
    print(f"รวม = {total * 100:.2f}% | Margin เจ้ามือ ≈ {margin:.2f}%")

    if args.model_home and args.model_away:
        model_total = sum(filter(None, [args.model_home, args.model_draw, args.model_away]))
        if abs(model_total - 100) > 1e-6:
            print("⚠️ ค่าโมเดลไม่ได้รวม 100% พิจารณาปรับให้สมดุล")
        for label, implied_prob, model_prob in (
            ("ฝั่งเหย้า", probs["home"] * 100, args.model_home),
            ("เสมอ", probs["draw"] * 100 if args.draw else 0.0, args.model_draw or 0.0),
            ("ฝั่งเยือน", probs["away"] * 100, args.model_away),
        ):
            if model_prob is None:
                continue
            edge = model_prob - implied_prob
            verdict = "คุ้ม" if edge > 0 else "ต่ำกว่าราคา"
            print(f"→ {label}: โมเดล {model_prob:.2f}% เทียบราคา {implied_prob:.2f}% = {edge:+.2f} จุด ({verdict})")

    if args.handicap is not None:
        side = "ต่อ" if args.handicap < 0 else "รอง"
        print(f"💡 Asian Handicap: {side} {abs(args.handicap):.2f}")
    if args.line is not None:
        print(f"💡 O/U Line: {args.line:.2f} ลูก (ดูเทมโปเกมใน tactical-analysis.md)")

    print("\nคำแนะนำ: ใช้ร่วมกับ winrate_tracker.py เพื่อตรวจสอบผลจริง รักษาวินัย 2-3% ของทุนต่อบิล")


if __name__ == "__main__":
    main()
