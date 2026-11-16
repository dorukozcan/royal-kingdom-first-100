#!/usr/bin/env python3
"""Reproduce the reported study counts and tables from the data tables, then draw the figures.

Run:  python3 -I analysis/make_report.py [--lang en|tr] [--no-figures]

Reads data/levels.csv, data/attempts.csv, data/offers.csv and data/coin_income.csv, prints the
tables as markdown, and writes figures/*.png. One player, one pass: descriptive numbers only.

What stops this script: a first-try count that differs from the game's counter, a coin balance
that does not reconcile level by level, or a recorded first offer that breaks the ladder rule.
"""
import argparse
import csv
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FIGS = os.path.join(ROOT, "figures")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if v != "" and v.lstrip("-").replace(".", "", 1).isdigit():
                r[k] = float(v) if "." in v else int(v)
    return rows


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def report(levels, attempts, offers):
    last = levels[-1]["level"]
    print(f"# Reproduced tables, L1-L{last}\n")
    recs = json.load(open(os.path.join(DATA, "recordings.json"), encoding="utf-8"))
    print(f"Study: levels 1-{last}, first level saved {levels[0]['saved_utc'][:10]}, last {levels[-1]['saved_utc'][:10]} (UTC); "
          f"{len(recs)} recordings, {sum(r['duration_s'] for r in recs) / 60:.0f} minutes, "
          f"{sum(r['ocr_last_t'] + 1 for r in recs):,} frames at one per second; "
          f"levels from the form: {sum(1 for x in levels if x['source'] == 'form')}, from recordings: {sum(1 for x in levels if x['source'] == 'recording')}\n")

    # 1. phases
    phases = [("L1-L14 (form)", 1, 14), ("L15-L26", 15, 26), ("L27-L50", 27, 50),
              ("L51-L56", 51, 56), ("L57", 57, 57), ("L58-L67", 58, min(67, last))]
    if last > 67:
        phases.append((f"L68-L{last}", 68, last))
    phases.append((f"All, L1-L{last}", 1, last))
    rows = []
    for name, a, b in phases:
        lv = [x for x in levels if a <= x["level"] <= b]
        at = [x for x in attempts if a <= x["level"] <= b]
        of = [x for x in offers if a <= x["level"] <= b]
        rows.append([name, len(lv), len(at), sum(x["result"] == "loss" for x in at),
                     len(of), sum(x["decision"] == "bought" for x in of)])
    print("## Phases\n" + table(["Range", "Levels", "Attempts", "Fails", "Offer screens", "Continues bought"], rows) + "\n")

    # 2. checkpoints against the game's own counters
    def first_try(upto):
        return sum(1 for x in levels if x["level"] <= upto and x["attempts"] == 1)
    checks = [(10, 8), (24, 15), (50, 38), (100, 68)]   # (levels won, first-try wins shown by the game)
    checks = [c for c in checks if c[0] <= last]
    rows = [[f"after L{n}", first_try(n), g, "OK" if first_try(n) == g else "DIFFERS"] for n, g in checks]
    print("## First-try wins vs the game's counter\n" + table(["Checkpoint", "Log", "Game", ""], rows) + "\n")
    assert all(r[3] == "OK" for r in rows)

    # 3. coin ledger (recorded levels). Every term has its own source: balances and level rewards were read
    #    on the win screens, continue prices on the offer screens, and the non-level coin rewards on their own popups
    #    (data/coin_income.csv, one row per reward with the recording and second of the balance step).
    income = read("coin_income.csv")
    rec = [x for x in levels if x["level"] >= 15]
    by_level = {x["level"]: x for x in rec}
    assert all(i["balance_after"] - i["balance_before"] == i["amount"] for i in income), "an income row does not match its balance step"
    for x in rec:      # inside a level: reward, continue spending, and rewards collected during or right after it
        extra = sum(i["amount"] for i in income if i["timing"] in ("during", "after") and i["level"] == x["level"])
        assert x["balance_end"] - x["balance_begin"] == x["reward_coin"] - x["coins_spent"] + extra, f"level {x['level']} does not reconcile"
    for x in rec[1:]:  # between two levels: only the itemized rewards
        between = sum(i["amount"] for i in income if i["timing"] == "before" and i["level"] == x["level"])
        assert x["balance_begin"] - by_level[x["level"] - 1]["balance_end"] == between, f"step before level {x['level']} is not itemized"
    rows = []
    for name, a, b in [("L15-L25", 15, 25), ("L26-L50", 26, 50), ("L51-L67", 51, min(67, last))] + ([(f"L68-L{last}", 68, last)] if last > 67 else []) + [(f"L15-L{last}", 15, last)]:
        seg = [x for x in rec if a <= x["level"] <= b]
        start, end = seg[0]["balance_begin"], seg[-1]["balance_end"]
        rewards = sum(x["reward_coin"] for x in seg)
        spent = sum(x["coins_spent"] for x in seg)
        other = sum(i["amount"] for i in income
                    if (i["timing"] == "before" and a < i["level"] <= b) or (i["timing"] != "before" and a <= i["level"] <= b))
        assert start + rewards + other - spent == end, name
        rows.append([name, start, rewards, other, spent, end, "closes"])
    print("## Coin ledger\n" + table(["Range", "Start", "Level rewards", "Non-level coin rewards (itemized)", "Spent on continues", "End", ""], rows) + "\n")
    steps = len({(i["timing"], i["level"]) for i in income})
    print(f"Non-level coin rewards: {len(income)} items in {steps} balance steps, {sum(i['amount'] for i in income)} coins "
          f"({sum(i['timing'] != 'before' for i in income)} of them collected during or right after a level). "
          f"Every level reconciles on its own, and so does every step between two levels.\n")
    src = {}
    for i in income:
        src.setdefault(i["source"], []).append(i["amount"])
    print(table(["Source", "Times", "Coins"], [[k, len(v), sum(v)] for k, v in sorted(src.items(), key=lambda kv: -sum(kv[1]))]) + "\n")
    wins = [x for x in rec if x["level"] >= 26]
    print(f"Average level reward L26-L{last}: {sum(x['reward_coin'] for x in wins) / len(wins):.1f} coins "
          f"({sum(x['reward_coin'] for x in wins)} / {len(wins)})\n")

    # 4. win streak
    st = [x for x in attempts if x["streak_step_at_start"] != ""]
    rows = []
    for step in (5, 4, 3, 2, 1, 0):
        g = [x for x in st if x["streak_step_at_start"] == step]
        clean = sum(1 for x in g if x["result"] == "win" and not x["continue_bought"])
        cont = sum(1 for x in g if x["result"] == "win" and x["continue_bought"])
        rows.append([f"{step}/5", len(g), clean, cont, len(g) - clean - cont, pct(clean + cont, len(g))])
    print(f"## Attempts by Magic Pots stage at the start (L32-L{last}); descriptive, the stage is derived from the rule\n" +
          table(["Streak step", "Attempts", "Won", "Won with a continue", "Lost", "Level passed"], rows) + "\n")
    pos, zero = [x for x in st if x["streak_step_at_start"] > 0], [x for x in st if x["streak_step_at_start"] == 0]
    print(f"Every attempt above stage 0 is a first attempt ({sum(x['attempt'] == 1 for x in pos)} of {len(pos)}) and every stage-0 attempt "
          f"is a retry ({sum(x['attempt'] > 1 for x in zero)} of {len(zero)}), so the pass rates compare first attempts with retries, not stages.\n")
    full = [x["level"] for x in levels if x["streak_step_first_attempt"] == 5]
    print(f"Levels started with a full streak: {len(full)}: {full}; power-ups placed by the streak, all attempts (derived: sum of stages at the start): "
          f"{sum(x['streak_step_at_start'] for x in st)}\n")
    rows = []
    for name, a, b in (("L32-L56", 32, 56), ("L57-L67", 57, 67), ("L68-L100", 68, 100)):
        g = [x for x in st if a <= x["level"] <= b]
        if g:
            rows.append([name, len(g), sum(x["result"] == "win" for x in g), sum(x["result"] == "loss" for x in g),
                         f"{sum(x['streak_step_at_start'] for x in g) / len(g):.1f}"])
    print("## Streak by phase\n" + table(["Range", "Attempts", "Won", "Lost", "Average stage at start"], rows) + "\n")
    print(f"Boosters, attempts from level 32: {sum(x['pre_boosters'] for x in st)} pre-level picks, {sum(x['in_boosters'] for x in st)} in-level uses\n")
    run, best = 0, 0
    for x in levels:
        run = run + 1 if x["streak_step_first_attempt"] == 5 else 0
        best = max(best, run)
    before = [x for x in levels if 27 <= x["level"] <= 56]
    after = [x for x in levels if x["level"] >= 57]
    print(f"Longest run of levels started at stage 5: {best}. Failed attempts: {sum(x['fails'] for x in before)} in levels 27-56 "
          f"({len(before)} levels), {sum(x['fails'] for x in after)} in levels 57-{last} ({len(after)} levels)\n")

    # 5. offers
    recd = [o for o in offers if o["source"] == "recording"]
    def cell(g):
        return f"{sum(o['decision'] == 'bought' for o in g)} of {len(g)}"
    rows = []
    for name, sel in (("before level 32 (no Magic Pots yet)", lambda o: o["level"] < 32),
                      ("level 32 and later", lambda o: o["level"] >= 32), ("all recorded offers", lambda o: True)):
        g = [o for o in recd if sel(o)]
        rows.append([name, cell([o for o in g if o["affordable"] == 1]), cell([o for o in g if o["affordable"] == 0])])
    print("## Recorded offers: bought, by whether the balance covered the price\n" +
          table(["", "Affordable", "Not affordable"], rows) + "\n")

    rows = []
    for m in sorted({o["moves_offered"] for o in offers}):
        g = [o for o in offers if o["moves_offered"] == m and o["seq_in_attempt"] == 1]
        aff = [o for o in g if o["affordable"] == 1]
        rows.append([f"+{m}", len(g), sorted({o["price_coin"] for o in g}), sum(o["decision"] == "bought" for o in g),
                     len(aff), sum(o["decision"] == "bought" for o in aff)])
    print("## Offers by size (first offer of an attempt)\n" +
          table(["Moves offered", "Shown", "Price", "Bought", "Affordable", "Bought when affordable"], rows) + "\n")
    ladder = [o for o in offers if o["seq_in_attempt"] == 1 and o["source"] == "recording"]
    assert all(o["moves_offered"] == min(5 * o["attempt"], 35) and o["price_coin"] == 900 for o in ladder), "ladder rule broken"
    print(f"Ladder rule (+5 per failed attempt, capped at +35, always 900): holds on {len(ladder)} of {len(ladder)} recorded first offers")
    # how much of that is independent of the rule itself
    inferred = {a["level"] for a in attempts if a["source"] == "inferred"}
    circular = [o for o in ladder if o["level"] in inferred]
    print(f"- of these, {len(circular)} on a level whose attempt count was inferred from the offer itself (levels {sorted(inferred)}): {len(ladder) - len(circular)} independent")
    pairs = [(a, b) for a, b in zip(ladder, ladder[1:])
             if a["level"] == b["level"] and a["recording"] == b["recording"] and b["attempt"] == a["attempt"] + 1]
    ok = sum(1 for a, b in pairs if b["moves_offered"] == min(a["moves_offered"] + 5, 35) and b["price_coin"] == 900)
    assert ok == len(pairs)
    grew = sum(1 for a, b in pairs if b["moves_offered"] == a["moves_offered"] + 5)
    print(f"- {len(pairs)} consecutive pairs of first offers on the same level in the same recording: the second was 5 moves larger "
          f"or still at the cap in {ok} of {len(pairs)} ({grew} grew by 5, {len(pairs) - grew} stayed at the +35 cap)")
    gaps = [(a, b) for a, b in zip(ladder, ladder[1:]) if a["level"] == b["level"] and a["recording"] != b["recording"]]
    print(f"- a level's ladder continued in a later recording {len(gaps)} times; these assume no unrecorded attempt in the gap")
    big = [o for o in ladder if o["level"] >= 32 and o["moves_offered"] >= 10]
    print(f"- offers of +10 or more since Magic Pots unlocked: {len(big)}; at stage 0: {sum(o['streak_step_at_stake'] == 0 for o in big)} "
          f"(by construction: they come on a retry and the stage is reset when an attempt is lost)")
    step2 = [o for o in ladder if o["moves_offered"] >= 10]
    print(f"- recorded offers of +10 or more that came with 2 Electro Balls: {sum(o['extras'] == '2 Elektrik Topu' for o in step2)} of {len(step2)}")
    later = [o for o in offers if o["seq_in_attempt"] != 1]
    print(f"- offers after a bought continue in the same attempt: {[(o['offer_id'], o['level'], o['moves_offered'], o['price_coin']) for o in later]}")
    form = [o for o in offers if o["source"] == "form"]
    print(f"- form offers, not part of the check: {[(o['offer_id'], o['level'], o['attempt'], o['moves_offered'], o['price_coin'], o['decision']) for o in form]}\n")
    aff = [o for o in recd if o["affordable"] == 1 and o["level"] >= 32]
    rows = [[o["level"], o["attempt"], f"+{o['moves_offered']}", o["balance"], o["remaining"], o["streak_step_at_stake"], o["decision"]] for o in aff]
    print("## Every offer the balance covered, level 32 and later\n" +
          table(["Level", "Attempt", "Offer", "Balance", "Remaining", "Streak stage at stake", "Decision"], rows) + "\n")
    firsts = [o for o in recd if o["attempt"] == 1 and o["seq_in_attempt"] == 1]
    assert all(o["moves_offered"] == 5 and o["price_coin"] == 900 for o in firsts)
    print(f"First offer on a level: +5 moves for 900 on {len(firsts)} of {len(firsts)} recorded levels")
    pots = [o for o in firsts if o["level"] >= 32]
    by_stage = {k: sum(1 for o in pots if o["streak_step_at_stake"] == k) for k in (1, 2, 3, 4, 5)}
    assert sum(by_stage.values()) == len(pots)
    print(f"- of these, {len(pots)} after Magic Pots unlocked, by stage at stake: {by_stage}\n")

    # scope of the evidence
    src_a = {k: sum(1 for a in attempts if a["source"] == k) for k in ("recording", "form", "inferred")}
    src_o = {k: sum(1 for o in offers if o["source"] == k) for k in ("recording", "form")}
    src_b = {k: sum(1 for o in offers if o["source"] == k and o["decision"] == "bought") for k in ("recording", "form")}
    lost = {(a["level"], a["attempt"]) for a in attempts if a["result"] == "loss"}
    with_offer = {(o["level"], o["attempt"]) for o in offers}
    print(f"Scope: attempts by source {src_a}; logged offers by source {src_o}; continues bought by source {src_b}; "
          f"failed attempts with no offer row: {len(lost - with_offer)} {sorted(lost - with_offer)}")
    cont1 = [x["level"] for x in levels if x["attempts"] == 1 and x["coins_spent"]]
    print(f"First-try wins that used a bought continue (the game's counter includes them): levels {cont1}\n")

    # after a bought continue: the first offer seen on a later level
    rows = []
    for i, o in enumerate(offers):
        if o["decision"] != "bought":
            continue
        nxt = next((p for p in offers[i + 1:] if p["level"] > o["level"]), None)
        rows.append([o["source"], o["level"], f"+{o['moves_offered']}", nxt["level"], f"+{nxt['moves_offered']} for {nxt['price_coin']}",
                     "yes" if nxt["level"] == o["level"] + 1 else "no"])
        assert nxt["moves_offered"] == 5 and nxt["price_coin"] == 900
    print("## After each bought continue: the next level on which an offer was seen\n" +
          table(["Source", "Bought on level", "Step bought", "Next level with an offer", "Its first offer", "Immediately next level"], rows) + "\n")

    # the moment the proposed experiment targets
    elig = [o for o in firsts if o["level"] >= 32 and o["streak_step_at_stake"] >= 3]
    rows = [[o["level"], f"{o['streak_step_at_stake']}/5", o["balance"], "yes" if o["affordable"] == 1 else "no", o["remaining"], o["decision"],
             o["seconds_to_decision"]] for o in elig]
    can = [o for o in elig if o["affordable"] == 1]
    print("## First out-of-moves of a first attempt with 3 or more Magic Pots stages at stake\n" +
          table(["Level", "Stage at stake", "Balance", "Covers 900", "Remaining", "Decision", "Seconds"], rows) + "\n")
    print(f"{len(elig)} such moments; balance covered the price on {len(can)}; bought {sum(o['decision'] == 'bought' for o in can)} of {len(can)}\n")

    # stake and exit warning
    stake = lambda o: (o["streak_step_at_stake"] not in ("", 0)) or o["other_stake"] != ""
    rows = []
    for name, g in (("streak or event at stake", [o for o in recd if stake(o)]),
                    ("nothing at stake", [o for o in recd if not stake(o)])):
        d = [o for o in g if o["decision"] == "declined"]
        b = [o for o in g if o["decision"] == "bought"]
        rows.append([name, len(g), len(b), sum(o["exit_warning"] != "" for o in b),
                     len(d), sum(o["exit_warning"] != "" for o in d)])
    print("## Loss warning on the offer screen\n" +
          table(["", "Offers", "Bought", "...warning seen", "Declined", "...warning seen"], rows) + "\n")

    items = [o for o in recd if o["remaining_units"] != ""]
    near = [o for o in items if o["remaining_units"] <= 3 and o["goals_open"] == 1]
    print(f"Near misses (one goal open, 3 or fewer left): {len(near)} of {len(items)} recorded offers with an item goal "
          f"({len(recd) - len(items)} Kingdom-level offers have no item count); "
          f"bought {sum(o['decision'] == 'bought' for o in near)}; "
          f"affordable {sum(o['affordable'] == 1 for o in near)}; levels {[o['level'] for o in near]}\n")

    def secs(g):
        v = [o["seconds_to_decision"] for o in g if o["seconds_to_decision"] != ""]
        return f"n={len(v)} of {len(g)}, median {statistics.median(v):g} s, range {min(v)}-{max(v)} s" if v else "-"
    print("## Seconds from the offer appearing to the decision\n" +
          table(["Decision", "Seconds"], [["bought", secs([o for o in recd if o["decision"] == "bought"])],
                                          ["declined", secs([o for o in recd if o["decision"] == "declined"])]]) + "\n")
    late = [o for o in recd if o["level"] >= 32]
    print(f"Kingdom Pass card readable in the first four sampled frames under {sum(o['pass_card_first_4_frames'] == 1 for o in late)} "
          f"of {len(late)} recorded offers from level 32 on (its extra moves equal the coin offer's on all of them, checked when the tables "
          f"were built); not readable in those frames under {sum(o['pass_card_first_4_frames'] == 0 for o in late)}; offer on screen for a "
          f"single sampled frame: {sum(o['pass_card_first_4_frames'] == '' for o in late)}; readable before level 32: "
          f"{sum(o['pass_card_first_4_frames'] == 1 for o in recd if o['level'] < 32)}. The card shares a carousel with the starter pack "
          f"card, so frames after the first four can show either card.\n")
    pack = [o for o in recd if o["welcome_pack_shown"] == 1]
    print(f"Welcome pack shown under {len(pack)} offer screens; balance below 900 on {sum(o['affordable'] == 0 for o in pack)} of them\n")
    unaff = [o for o in offers if o["affordable"] == 0]
    print(f"Offers the balance could not cover: {len(unaff)}; bought: {sum(o['decision'] == 'bought' for o in unaff)}; "
          f"loss warning seen on {sum(o['exit_warning'] != '' for o in unaff)}; starter pack card shown under {sum(o['welcome_pack_shown'] == 1 for o in unaff)}\n")
    side_checks(levels, offers)


def side_checks(levels, offers):
    """Observations made outside the 100-level log. Printed only if their tables are present."""
    if os.path.exists(os.path.join(DATA, "side_checks.csv")):
        side = read("side_checks.csv")
        print("## Side checks: offers seen outside the 100-level log (not part of any count above)\n" +
              table(["Check", "Date", "Game", "Level", "Attempt", "Offer", "Price", "Balance", "Decision"],
                    [[s["check"], s["date"], s["game"], s["level"] if s["level"] != "" else "one level", s["attempt"],
                      f"+{s['moves_offered']}", s["price_coin"], s["balance"], s["decision"]] for s in side]) + "\n")
        assert all(s["moves_offered"] == 5 and s["price_coin"] == 900 and s["extras"] == "" for s in side), "a side-check offer is not +5 for 900"
        l9 = [s for s in side if s["check"] == "second_account" and s["level"] == 9]
        assert [s["attempt"] for s in l9] == [1, 2, 3] and all(s["decision"] == "declined" and s["balance"] >= 900 for s in l9)
        first_growth = min(o["level"] for o in offers if o["attempt"] >= 2 and o["seq_in_attempt"] == 1 and o["moves_offered"] >= 10)
        first_growth_rec = min(o["level"] for o in offers if o["attempt"] >= 2 and o["seq_in_attempt"] == 1 and o["moves_offered"] >= 10 and o["source"] == "recording")
        print(f"Second account, level 9: {len(l9)} failed attempts in a row, first offer +5 for 900 each time with the balance above the price "
              f"(the formula would give +5, +10, +15). First account: the form entry for level 9 also has +5 twice; "
              f"the first larger offer in the log is on level {first_growth} (form), on video on level {first_growth_rec}.")
        print()


# ---------------------------------------------------------------------------
# Figures (light surface; palette and mark rules follow the chart guide)
# ---------------------------------------------------------------------------

C = {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
     "grid": "#e1e0d9", "axis": "#c3c2b7", "blue": "#2a78d6", "orange": "#eb6834", "wash": "#f0efec",
     "form_blue": "#9fc3ee", "form_grey": "#cfcdc6"}

TEXT = {
    "en": {
        "f1_title": "Failed attempts, win streak and coin balance by level",
        "f1_sub": "One player, levels 1-{last}. Levels 27-56: 1 failed attempt in 30 levels. Levels 57-{last}: {late} in {n_late} levels.",
        "f1_a": "Failed attempts before the win",
        "f1_b": "Magic Pots stage at the first attempt (win streak; each stage adds one free power-up at the start; unlocks at level 32)",
        "f1_c": "Coin balance after the level (read from recordings, level 15 on)",
        "f1_x": "Level",
        "f1_l57": "L57: 10 fails",
        "f1_full": "stage 5 for 21 levels in a row  |",
        "f1_lost": "lost on the first attempt of L57",
        "price": "first continue in an attempt: 900",
        "bought": "continue bought",
        "balance": "coin balance",
        "f2_title": "All {n} logged continue offers, levels 1-{last}: {rec} from recordings, {form} from the form",
        "f2_sub": "Recorded offers bought: {a} of {b} when the balance covered the price, {c} of {d} when it did not.",
        "f2_a": "Coin balance when the offer appeared",
        "f2_b": "Extra moves offered (first offer of an attempt: 900 coins; the one marked is a second offer in the same attempt)",
        "f2_x": "Offers in the order they appeared, grouped by level",
        "declined": "declined",
        "second": "second offer in the same attempt: 1,900",
        "stake": "x/5 = Magic Pots stage at stake",
        "unknown": "balance not recorded (level 9)",
        "form": "lighter marks: from the form (levels 9 and 13)",
    },
    "tr": {
        "f1_title": "Seviyeye göre kayıplar, galibiyet serisi ve coin bakiyesi",
        "f1_sub": "Tek oyuncu, 1-{last}. seviyeler. 27-56: 30 seviyede 1 kayıp. 57-{last}: {n_late} seviyede {late} kayıp.",
        "f1_a": "Galibiyetten önceki kayıp sayısı",
        "f1_b": "İlk denemedeki Sihirli Kazan basamağı (galibiyet serisi; her basamak başlangıca bir bedava booster ekler; 32. seviyede açılır)",
        "f1_c": "Seviye sonrası coin bakiyesi (ekran kaydından, 15. seviyeden itibaren)",
        "f1_x": "Seviye",
        "f1_l57": "L57: 10 kayıp",
        "f1_full": "seri dolu, art arda 21 seviye  |",
        "f1_lost": "L57'nin ilk denemesinde kaybedildi",
        "price": "denemedeki ilk devam: 900",
        "bought": "devam alındı",
        "balance": "coin bakiyesi",
        "f2_title": "Kayda geçen {n} devam teklifi, 1-{last}. seviyeler: {rec} ekran kaydından, {form} formdan",
        "f2_sub": "Ekran kaydındaki tekliflerden alınanlar: bakiye yettiğinde {a}/{b}, yetmediğinde {c}/{d}.",
        "f2_a": "Teklif çıktığı andaki coin bakiyesi",
        "f2_b": "Teklif edilen ek hamle (denemenin ilk teklifi: 900 coin; işaretli olan aynı denemedeki ikinci teklif)",
        "f2_x": "Teklifler çıkış sırasıyla, seviyeye göre gruplu",
        "declined": "alınmadı",
        "second": "aynı denemede ikinci teklif: 1.900",
        "stake": "x/5 = riskteki Sihirli Kazan basamağı",
        "unknown": "bakiye kaydı yok (9. seviye)",
        "form": "açık renkli işaretler: formdan (9. ve 13. seviye)",
    },
}


def setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 8.5,
        "figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"],
        "axes.edgecolor": C["axis"], "axes.linewidth": 0.6, "axes.labelcolor": C["ink2"],
        "xtick.color": C["muted"], "ytick.color": C["muted"], "xtick.labelcolor": C["ink2"], "ytick.labelcolor": C["ink2"],
        "xtick.major.size": 0, "ytick.major.size": 0, "axes.grid": False, "text.color": C["ink"],
    })
    return plt


def style(ax, ymax, yticks):
    ax.set_ylim(0, ymax)
    ax.set_yticks(yticks)
    for y in yticks[1:]:
        ax.axhline(y, color=C["grid"], lw=0.5, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(C["axis"])
    ax.tick_params(axis="both", labelsize=7.5, pad=3)


def panel_title(ax, s, y=1.06):
    ax.text(0, y, s, transform=ax.transAxes, fontsize=8.5, color=C["ink2"], va="bottom", ha="left")


def bars(ax, xs, hs, width, color):
    """Columns with a rounded data end and a square baseline."""
    from matplotlib.patches import FancyBboxPatch, Rectangle
    ax.figure.canvas.draw()
    box = ax.get_window_extent()
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    aspect = ((y1 - y0) / box.height) / ((x1 - x0) / box.width)   # y data units per x data unit, in pixels
    r = width / 2 * 0.72
    for x, h in zip(xs, hs):
        if not h:
            continue
        ry = min(r * aspect, h / 2)
        rx = ry / aspect
        ax.add_patch(FancyBboxPatch((x - width / 2, 0), width, h, boxstyle=f"round,pad=0,rounding_size={rx}",
                                    mutation_aspect=aspect, fc=color, ec="none", zorder=3))
        ax.add_patch(Rectangle((x - width / 2, 0), width, h - ry, fc=color, ec="none", zorder=3))


def figure_levels(plt, levels, attempts, lang):
    t = TEXT[lang]
    last = levels[-1]["level"]
    late = [x for x in levels if x["level"] >= 57]
    fig, axes = plt.subplots(3, 1, figsize=(8, 6.9), sharex=True, gridspec_kw={"height_ratios": [1.15, 0.8, 1.15]})
    fig.subplots_adjust(left=0.065, right=0.985, top=0.865, bottom=0.075, hspace=0.42)
    fig.text(0.065, 0.955, t["f1_title"], fontsize=12, fontweight="bold", color=C["ink"], ha="left")
    fig.text(0.065, 0.922, t["f1_sub"].format(last=last, late=sum(x["fails"] for x in late), n_late=len(late)),
             fontsize=8.5, color=C["ink2"], ha="left")
    xs = [x["level"] for x in levels]
    for ax in axes:
        ax.set_xlim(0.2, last + 0.8)

    ax = axes[0]
    style(ax, 11, [0, 2, 4, 6, 8, 10])
    bars(ax, xs, [x["fails"] for x in levels], 0.62, C["blue"])
    panel_title(ax, t["f1_a"])
    ax.annotate(t["f1_l57"], xy=(57, 10), xytext=(55.6, 10), fontsize=8, color=C["ink"], ha="right", va="center")

    ax = axes[1]
    style(ax, 5.6, [0, 1, 2, 3, 4, 5])
    st = [x for x in levels if x["streak_step_first_attempt"] != ""]
    bars(ax, [x["level"] for x in st], [x["streak_step_first_attempt"] for x in st], 0.62, C["blue"])
    panel_title(ax, t["f1_b"])
    ax.annotate(t["f1_full"], xy=(56.3, 5), xytext=(56.3, 5.25), fontsize=8, color=C["ink"], ha="right", va="bottom", annotation_clip=False)
    ax.annotate(t["f1_lost"], xy=(59.5, 5), xytext=(59.5, 5.25), fontsize=8, color=C["ink2"], ha="left", va="bottom", annotation_clip=False)

    ax = axes[2]
    style(ax, 2800, [0, 500, 1000, 1500, 2000, 2500])
    rec = [x for x in levels if x["balance_end"] != ""]
    ax.axhline(900, color=C["ink2"], lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(1.0, 850, t["price"], fontsize=7.5, color=C["ink2"], ha="left", va="top")
    ax.plot([x["level"] for x in rec], [x["balance_end"] for x in rec], color=C["blue"], lw=1.5,
            solid_joinstyle="round", solid_capstyle="round", zorder=3, label=t["balance"])
    buy = [x for x in rec if x["coins_spent"]]
    ax.plot([x["level"] for x in buy], [x["balance_end"] for x in buy], ls="none", marker="o", ms=6.5,
            mfc=C["orange"], mec=C["surface"], mew=1.4, zorder=4, label=t["bought"])
    panel_title(ax, t["f1_c"])
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.99), frameon=False, fontsize=7.5, ncol=2, handlelength=1.6,
              columnspacing=1.4, labelcolor=C["ink2"])
    ax.set_xticks([1] + list(range(10, last, 10)) + [last])
    ax.set_xlabel(t["f1_x"], fontsize=8, labelpad=4)
    path = os.path.join(FIGS, f"levels_fails_streak_balance_{lang}.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_offers(plt, levels, offers, lang):
    t = TEXT[lang]
    last = levels[-1]["level"]
    late = [o for o in offers if o["source"] == "recording"]
    aff = [o for o in late if o["affordable"] == 1]
    not_aff = [o for o in late if o["affordable"] == 0]
    wide = len(offers) > 50
    fig, axes = plt.subplots(2, 1, figsize=(11 if wide else 8, 5.9), sharex=True, gridspec_kw={"height_ratios": [1.45, 1]})
    left = 0.048 if wide else 0.065
    fig.subplots_adjust(left=left, right=0.99, top=0.815, bottom=0.105, hspace=0.36)
    fig.text(left, 0.953, t["f2_title"].format(last=last, n=len(offers), rec=len(late), form=len(offers) - len(late)),
             fontsize=12, fontweight="bold", color=C["ink"], ha="left")
    fig.text(left, 0.916, t["f2_sub"].format(a=sum(o["decision"] == "bought" for o in aff), b=len(aff),
                                             c=sum(o["decision"] == "bought" for o in not_aff), d=len(not_aff)),
             fontsize=8.5, color=C["ink2"], ha="left")
    n = len(offers)
    xs = list(range(1, n + 1))
    groups = {}
    for x, o in zip(xs, offers):
        groups.setdefault(o["level"], []).append(x)
    for ax in axes:
        ax.set_xlim(0.3, n + 0.7)
        for i, (lvl, g) in enumerate(groups.items()):
            if i % 2 == 0:
                ax.axvspan(g[0] - 0.5, g[-1] + 0.5, color=C["wash"], lw=0, zorder=0)

    ax = axes[0]
    style(ax, 3000, [0, 500, 1000, 1500, 2000, 2500])
    ax.axhline(900, color=C["ink2"], lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(0.6, 850, t["price"], fontsize=7.5, color=C["ink2"], ha="left", va="top")
    known = [(x, o) for x, o in zip(xs, offers) if o["balance"] != ""]
    dec = [(x, o) for x, o in known if o["decision"] == "declined" and o["source"] == "recording"]
    bought = [(x, o) for x, o in known if o["decision"] == "bought" and o["source"] == "recording"]
    for x, o in known:          # form entries: same marks, lighter
        if o["source"] == "form":
            big = o["decision"] == "bought"
            ax.plot([x], [o["balance"]], ls="none", marker="o", ms=7.6 if big else 5.9, mfc=C["form_blue"] if big else C["form_grey"],
                    mec=C["surface"], mew=1.4 if big else 1.2, zorder=4 if big else 3)
    ax.plot([x for x, _ in dec], [o["balance"] for _, o in dec], ls="none", marker="o", ms=5.9, mfc=C["muted"],
            mec=C["surface"], mew=1.2, zorder=3, label=t["declined"])
    ax.plot([x for x, _ in bought], [o["balance"] for _, o in bought], ls="none", marker="o", ms=7.6, mfc=C["blue"],
            mec=C["surface"], mew=1.4, zorder=4, label=t["bought"])
    for x, o in bought:
        if o["streak_step_at_stake"] != "":
            ax.annotate(f"{o['streak_step_at_stake']}/5", xy=(x, o["balance"]), xytext=(0, 8), textcoords="offset points",
                        fontsize=7.5, color=C["ink"], ha="center", va="bottom")
    for x, o in zip(xs, offers):
        if o["price_coin"] != 900:
            ax.annotate(t["second"], xy=(x, o["balance"]), xytext=(x + 1.2, 560), fontsize=7.5, color=C["ink"], ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=C["muted"], lw=0.6, shrinkA=1, shrinkB=4))
    panel_title(ax, t["f2_a"], y=1.13)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.012, 1.0), frameon=False, fontsize=7.5, ncol=2, handlelength=1.2,
              columnspacing=1.4, labelcolor=C["ink2"], handletextpad=0.3, borderaxespad=0.2)
    ax.text(0.2 if wide else 0.27, 1.045, t["stake"] + "  ·  " + t["form"] + "  ·  " + t["unknown"], transform=ax.transAxes,
            fontsize=7.5, color=C["muted"], ha="left", va="center")

    ax = axes[1]
    style(ax, 40, [0, 10, 20, 30])
    bars(ax, xs, [o["moves_offered"] if o["source"] == "recording" else 0 for o in offers], 0.6, C["blue"])
    bars(ax, xs, [o["moves_offered"] if o["source"] == "form" else 0 for o in offers], 0.6, C["form_blue"])
    panel_title(ax, t["f2_b"])
    for x, o in zip(xs, offers):
        if o["price_coin"] != 900:
            ax.text(x, 11.5, "1,900" if lang == "en" else "1.900", fontsize=7.5, color=C["ink"], ha="center", va="bottom")
    ax.set_xticks([sum(g) / len(g) for g in groups.values()])
    ax.set_xticklabels([str(k) for k in groups.keys()], fontsize=6.6 if wide else 7.5)
    ax.set_xlabel(t["f2_x"], fontsize=8, labelpad=4)
    path = os.path.join(FIGS, f"offers_balance_decision_{lang}.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["en", "tr"], default="en")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()
    levels, attempts, offers = read("levels.csv"), read("attempts.csv"), read("offers.csv")
    report(levels, attempts, offers)
    if not args.no_figures:
        os.makedirs(FIGS, exist_ok=True)
        plt = setup()
        for p in (figure_levels(plt, levels, attempts, args.lang), figure_offers(plt, levels, offers, args.lang)):
            print("wrote", os.path.relpath(p, ROOT), file=sys.stderr)   # keep stdout to the report itself
    return 0


if __name__ == "__main__":
    sys.exit(main())
