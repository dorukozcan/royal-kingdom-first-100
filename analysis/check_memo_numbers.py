#!/usr/bin/env python3
"""Data checks: compute values from the tables and compare each with a fixed expected value.

Run:  python3 -I analysis/check_memo_numbers.py
Each expected value is written into this script; it was copied from the memo when the memo was written.
The script does not read the memo or its PDF, so it shows that the tables still give those numbers,
not that the memo text quotes them correctly. It reads only data/*.csv and data/recordings.json,
prints one line per check and exits with an error if any check fails.
"""
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if v != "" and v.lstrip("-").replace(".", "", 1).isdigit():
                r[k] = float(v) if "." in v else int(v)
    return rows


def per_arm(p1, p2, alpha_z=1.959964, power_z=0.841621):
    """Players per arm for a two-sided two-proportion test (alpha 0.05, power 0.80)."""
    pbar = (p1 + p2) / 2
    n = (alpha_z * math.sqrt(2 * pbar * (1 - pbar)) + power_z * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
    return math.ceil(n)


def main():
    levels, attempts, offers, income = read("levels.csv"), read("attempts.csv"), read("offers.csv"), read("coin_income.csv")
    recs = json.load(open(os.path.join(DATA, "recordings.json"), encoding="utf-8"))
    L = {x["level"]: x for x in levels}
    recd = [o for o in offers if o["source"] == "recording"]
    ladder = [o for o in recd if o["seq_in_attempt"] == 1]
    firsts = [o for o in ladder if o["attempt"] == 1]
    pairs = [(a, b) for a, b in zip(ladder, ladder[1:])
             if a["level"] == b["level"] and a["recording"] == b["recording"] and b["attempt"] == a["attempt"] + 1]
    lost = {(a["level"], a["attempt"]) for a in attempts if a["result"] == "loss"}
    with_offer = {(o["level"], o["attempt"]) for o in offers}
    no_row = sorted(lost - with_offer)
    stake = lambda o: (o["streak_step_at_stake"] not in ("", 0)) or o["other_stake"] != ""
    declined = [o for o in recd if o["decision"] == "declined"]
    pots = [o for o in firsts if o["level"] >= 32]
    elig = [o for o in pots if o["streak_step_at_stake"] >= 3]
    can = [o for o in elig if o["affordable"] == 1]
    bought_elig = [o for o in can if o["decision"] == "bought"]
    run = best = 0
    for x in levels:
        run = run + 1 if x["streak_step_first_attempt"] == 5 else 0
        best = max(best, run)
    rec_levels = [x for x in levels if x["level"] >= 15]
    l57 = [o for o in offers if o["level"] == 57]
    l89 = [o for o in offers if o["level"] == 89]
    l86 = [o for o in offers if o["level"] == 86][0]
    l76 = [o for o in offers if o["level"] == 76][0]
    first_try = lambda n: sum(1 for x in levels if x["level"] <= n and x["attempts"] == 1)

    checks = [
        ("levels in the log", len(levels), 100),
        ("recordings / minutes", (len(recs), round(sum(r["duration_s"] for r in recs) / 60)), (23, 362)),
        ("attempts", len(attempts), 179),
        ("logged offers: all / on video / from the form", (len(offers), len(recd), len(offers) - len(recd)), (82, 78, 4)),
        ("failed attempts with no offer row: all / form period / off camera",
         (len(no_row), sum(1 for l, _ in no_row if l <= 14), sum(1 for l, _ in no_row if l == 68)), (6, 4, 2)),
        ("first-try wins after levels 10, 24, 50, 100", [first_try(n) for n in (10, 24, 50, 100)], [8, 15, 38, 68]),
        ("coins: balance before level 15", rec_levels[0]["balance_begin"], 878),
        ("coins: level rewards, levels 15-100", sum(x["reward_coin"] for x in rec_levels), 3117),
        ("coins: non-level coin rewards / number of items", (sum(i["amount"] for i in income), len(income)), (3305, 21)),
        ("coins: spent on continues, levels 15-100", sum(x["coins_spent"] for x in rec_levels), 6300),
        ("coins: balance after level 100", rec_levels[-1]["balance_end"], 1000),
        ("coins: the ledger closes", rec_levels[0]["balance_begin"] + sum(x["reward_coin"] for x in rec_levels)
         + sum(i["amount"] for i in income) - sum(x["coins_spent"] for x in rec_levels), 1000),
        ("level 57: first offer, balance, decision", (l57[0]["moves_offered"], l57[0]["price_coin"], l57[0]["balance"], l57[0]["decision"]), (5, 900, 940, "bought")),
        ("level 57: second offer in the attempt, price, balance", (l57[1]["moves_offered"], l57[1]["extras"], l57[1]["price_coin"], l57[1]["balance"]), (5, "1 Roket", 1900, 40)),
        ("level 57: first offer of the next attempt", (l57[2]["attempt"], l57[2]["moves_offered"], l57[2]["extras"], l57[2]["price_coin"]), (2, 10, "2 Elektrik Topu", 900)),
        ("level 57: seconds to the first purchase", l57[0]["seconds_to_decision"], 2),
        ("recorded first offers that fit +5 per attempt, capped at +35, for 900",
         (sum(o["moves_offered"] == min(5 * o["attempt"], 35) and o["price_coin"] == 900 for o in ladder), len(ladder)), (77, 77)),
        ("consecutive pairs of first offers in the same recording: all / grew by five / stayed at the +35 cap",
         (len(pairs), sum(b["moves_offered"] == a["moves_offered"] + 5 for a, b in pairs),
          sum(a["moves_offered"] == 35 and b["moves_offered"] == 35 for a, b in pairs)), (35, 33, 2)),
        ("offers of +10 or more that came with two Electro Balls",
         (sum(o["extras"] == "2 Elektrik Topu" for o in ladder if o["moves_offered"] >= 10), sum(o["moves_offered"] >= 10 for o in ladder)), (47, 47)),
        ("level 9, form: offers on attempts 1 and 2", [(o["attempt"], o["moves_offered"]) for o in offers if o["level"] == 9], [(1, 5), (2, 5)]),
        ("first level with a larger offer in the log", min(o["level"] for o in offers if o["seq_in_attempt"] == 1 and o["moves_offered"] >= 10), 13),
        ("first offers on a level after Magic Pots unlocked: count / all +5 for 900 / stages seen",
         (len(pots), all(o["moves_offered"] == 5 and o["price_coin"] == 900 for o in pots), sorted({o["streak_step_at_stake"] for o in pots})), (23, True, [1, 2, 3, 4, 5])),
        ("declines with a streak or event at stake: warning shown / all", (sum(o["exit_warning"] != "" for o in declined if stake(o)), sum(1 for o in declined if stake(o))), (23, 23)),
        ("other declines: warning shown / all", (sum(o["exit_warning"] != "" for o in declined if not stake(o)), sum(1 for o in declined if not stake(o))), (0, 48)),
        ("offers of +10 or more after level 32: all / with the pots empty",
         (sum(1 for o in ladder if o["level"] >= 32 and o["moves_offered"] >= 10),
          sum(1 for o in ladder if o["level"] >= 32 and o["moves_offered"] >= 10 and o["streak_step_at_stake"] == 0)), (42, 42)),
        ("longest run of levels started with full pots", best, 21),
        ("failed attempts: levels 27-56 (30 levels) / levels 57-100 (44 levels)",
         (sum(x["fails"] for x in levels if 27 <= x["level"] <= 56), sum(1 for x in levels if 27 <= x["level"] <= 56),
          sum(x["fails"] for x in levels if x["level"] >= 57), sum(1 for x in levels if x["level"] >= 57)), (1, 30, 61, 44)),
        ("recorded offers the balance did not cover: bought / all", (sum(o["decision"] == "bought" for o in recd if o["affordable"] == 0), sum(o["affordable"] == 0 for o in recd)), (0, 59)),
        ("recorded offers the balance covered: bought / all", (sum(o["decision"] == "bought" for o in recd if o["affordable"] == 1), sum(o["affordable"] == 1 for o in recd)), (7, 19)),
        ("level 86: coins short, stage at stake, other run at stake", (l86["price_coin"] - l86["balance"], l86["streak_step_at_stake"], l86["other_stake"] != ""), (9, 2, True)),
        ("first out-of-moves with stage 3 or more at stake: all / balance covered / bought", (len(elig), len(can), len(bought_elig)), (11, 6, 4)),
        ("levels of those four purchases, and seconds to each", ([o["level"] for o in bought_elig], sorted(o["seconds_to_decision"] for o in bought_elig)), ([53, 54, 57, 65], [2, 2, 3, 10])),
        ("level 76: first offer declined, items left", (l76["decision"], l76["remaining_units"], l76["affordable"]), ("declined", 31, 1)),
        ("level 89: offers and decisions", [(o["moves_offered"], o["decision"]) for o in l89],
         [(5, "declined"), (10, "declined"), (15, "declined"), (20, "declined"), (25, "bought")]),
        ("level 89: items left at the purchase, moves left at the win, coins before the level", (l89[-1]["remaining_units"], L[89]["moves_left"], L[89]["balance_begin"]), (5, 22, 957)),
        ("sample size per arm at 60% and +2 points", per_arm(0.60, 0.62), 9336),
    ]
    if os.path.exists(os.path.join(DATA, "side_checks.csv")):
        side = read("side_checks.csv")
        checks.append(("second account, level 9: offers on three attempts in a row",
                       [(s["attempt"], s["moves_offered"], s["price_coin"]) for s in side if s["check"] == "second_account" and s["level"] == 9],
                       [(1, 5, 900), (2, 5, 900), (3, 5, 900)]))
    bad = 0
    for label, got, want in checks:
        ok = got == want
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {label}: {got}" + ("" if ok else f"   expected {want}"))
    print(f"\n{len(checks)} data checks passed" if not bad else f"\n{bad} of {len(checks)} data checks failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
