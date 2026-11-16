#!/usr/bin/env python3
"""Turn the OCR of a screen recording (video_ocr.swift output) into attempts, offers and events.

Usage: python3 -I parse_ocr.py <recording.jsonl> [<recording2.jsonl> ...]
Prints a compact table and writes <recording>.attempts.json next to each input.
OCR can misread single digits: moves left and offers still need a look at the key frames it lists.
"""
import json
import re
import sys

LEVEL = re.compile(r"B.{1,2}l.{1,2}m\s*(\d+)")
TIMER = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
NUMBER = re.compile(r"^\d[\d.,]*$")
OFFER_MOVES = re.compile(r"(\d+)\s*hamle daha ekle")
EVENT_TEXT = {
    "Yeni obje açıldı": "yeni obje",
    "Yeni takviye açıldı": "yeni booster",
    "Tamamlandı": "bölge tamamlandı",
    "takıma katıl": "takım teklifi",
    "İFADE ALBÜMÜ": "ifade albümü",
}


def to_int(text):
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def has(lines, word):
    return any(word in line["s"] for line in lines)


def number_at(lines, x0, x1, y0, y1):
    for line in lines:
        if x0 <= line["x"] <= x1 and y0 <= line["y"] <= y1 and NUMBER.match(line["s"]):
            return to_int(line["s"])
    return None


def classify(lines):
    """Name the screen a frame shows and pull out the numbers it carries."""
    if not lines:
        return {"kind": "other"}
    frame = {"kind": "other"}
    if has(lines, "Canın Kalmad"):
        frame["kind"] = "no_lives"
    elif has(lines, "Devam Et?") or has(lines, "hamle daha ekle"):
        frame["kind"] = "offer"
        text = " ".join(line["s"] for line in lines)
        match = OFFER_MOVES.search(text)
        frame["moves"] = int(match.group(1)) if match else None
        frame["coin"] = number_at(lines, 0.0, 0.35, 0.15, 0.27)
        frame["price"] = next((v for v in (to_int(line["s"]) for line in lines if "Devam Et" in line["s"] or (0.5 <= line["y"] <= 0.7 and NUMBER.match(line["s"]))) if v and v >= 100), None)
        frame["pack"] = has(lines, "Hoş Geldin Paketi")
        frame["remaining"] = number_at(lines, 0.3, 0.72, 0.05, 0.18)
    elif has(lines, "Hamlen Kalmad"):
        frame["kind"] = "out_of_moves"
    elif has(lines, "Bölüm Başarısız") or has(lines, "Kaybettin"):
        frame["kind"] = "fail"
    elif has(lines, "Güçlendirici") and has(lines, "Oyna"):
        frame["kind"] = "prelevel"
        match = next((LEVEL.search(line["s"]) for line in sorted(lines, key=lambda l: l["y"]) if LEVEL.search(line["s"])), None)
        frame["level"] = int(match.group(1)) if match else None
    elif has(lines, "Zafer") or has(lines, "Ödül") or has(lines, "Geçmek"):
        frame["kind"] = "win"
    elif has(lines, "Ana Ekran"):
        frame["kind"] = "home"
        frame["coin"] = number_at(lines, 0.1, 0.5, 0.05, 0.13)
        frame["iksir"] = number_at(lines, 0.68, 0.92, 0.05, 0.13)
        frame["full"] = has(lines, "Dolu")
        plus = next((to_int(line["s"]) for line in lines if re.match(r"^\+\d+$", line["s"])), None)
        frame["plus"] = plus
    elif has(lines, "Hamle") or has(lines, "Hedef"):
        frame["kind"] = "board"
        frame["moves"] = next((int(line["s"]) for line in lines if line["x"] > 0.72 and line["y"] < 0.2 and re.fullmatch(r"\d{1,2}", line["s"])), None)
    if has(lines, "ROYAL") and has(lines, "KINGDOM") and frame["kind"] == "board":
        frame["kind"] = "win"
    frame["events"] = [name for text, name in EVENT_TEXT.items() if has(lines, text)]
    return frame


def parse(path):
    level, attempt, last_win = None, None, None
    attempts, events, homes = [], [], []
    pending = None  # reading seen once, accepted when repeated
    after_win = False  # end-of-level animation still shows the board
    for raw in open(path, encoding="utf-8"):
        row = json.loads(raw)
        t = int(row["t"])
        lines = [l for l in row["lines"] if l["c"] >= 0.3]
        frame = classify(lines)
        kind = frame["kind"]
        for name in frame.get("events", []):
            if not events or events[-1][1] != name or t - events[-1][0] > 10:
                events.append((t, name, level))
        if kind in ("prelevel", "home"):
            after_win = False
        if kind == "prelevel" and frame["level"]:
            level = frame["level"]
        elif kind == "board":
            if after_win:
                continue
            value = frame.get("moves")
            if attempt is None:
                attempt = {"level": level, "t_start": t, "moves_start": value, "moves_last": value, "offers": [], "result": None, "bought": False, "out_t": None}
                pending = None
            elif value is not None:
                if attempt["moves_start"] is None:
                    attempt["moves_start"] = attempt["moves_last"] = value
                elif attempt["offers"] and value > (attempt["moves_last"] or 0):
                    attempt["bought"] = True
                    attempt["offers"][-1]["decision"] = "aldı"
                    attempt["moves_last"] = value
                elif value <= (attempt["moves_last"] or 99) and (attempt["moves_last"] or 99) - value <= 2:
                    attempt["moves_last"] = value
                    pending = None
                elif pending == value:
                    attempt["moves_last"] = value
                    pending = None
                else:
                    pending = value
        elif kind == "out_of_moves" and attempt:
            attempt["out_t"] = attempt["out_t"] or t
            attempt["moves_last"] = 0
        elif kind == "offer" and attempt:
            if not attempt["offers"] or attempt["offers"][-1].get("decision"):
                attempt["offers"].append({"t": t, "moves": frame["moves"], "price": frame["price"], "coin": frame["coin"], "pack": frame["pack"], "remaining": frame["remaining"], "decision": None})
            else:
                current = attempt["offers"][-1]
                current["moves"] = max(filter(None, [current["moves"], frame["moves"]]), default=None)
                for key in ("price", "coin", "remaining"):
                    current[key] = current[key] or frame[key]
                current["pack"] = current["pack"] or frame["pack"]
        elif kind == "fail" and attempt:
            attempt["result"] = "kayıp"
            attempt["t_end"] = t
            for offer in attempt["offers"]:
                offer["decision"] = offer["decision"] or "almadı"
            attempts.append(attempt)
            attempt = None
        elif kind == "win" and attempt:
            attempt["result"] = "kazandı"
            attempt["t_end"] = t
            for offer in attempt["offers"]:
                offer["decision"] = offer["decision"] or "almadı"
            attempts.append(attempt)
            last_win = attempt
            attempt = None
            after_win = True
        elif kind == "no_lives":
            if not events or events[-1][1] != "can bitti" or t - events[-1][0] > 30:
                events.append((t, "can bitti", level))
        elif kind == "home":
            homes.append((t, frame["coin"], frame["iksir"]))
            if frame["plus"] and last_win is not None and "reward" not in last_win:
                last_win["reward"] = frame["plus"]
    if attempt:
        attempt["result"] = "kayıt bitti"
        attempts.append(attempt)
    return attempts, events, homes


def main():
    for path in sys.argv[1:]:
        attempts, events, homes = parse(path)
        print(f"== {path.rsplit('/', 1)[-1]}")
        for a in attempts:
            offers = "; ".join(f"+{o['moves']} / {o['price']} (bakiye {o['coin']}, kalan {o['remaining']}, paket {'var' if o['pack'] else 'yok'}): {o['decision']}" for o in a["offers"])
            print(f"L{a['level']} {a['t_start']:>4}-{a.get('t_end', '?'):>4}s hamle {a['moves_start']} son {a['moves_last']} {a['result']} ödül {a.get('reward', '-')}" + (f" | {offers}" if offers else ""))
        print("olaylar:", ", ".join(f"{t}s {name} (L{level})" for t, name, level in events) or "yok")
        if homes:
            first = next((h for h in homes if h[1] is not None), None)
            last = next((h for h in reversed(homes) if h[1] is not None), None)
            print(f"bakiye: başta {first[1]} coin, {first[2]} iksir; sonda {last[1]} coin, {last[2]} iksir")
        with open(path.rsplit(".", 1)[0] + ".attempts.json", "w", encoding="utf-8") as out:
            json.dump({"attempts": attempts, "events": events}, out, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
