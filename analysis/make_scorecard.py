#!/usr/bin/env python3
"""One-page scorecard of a first-100-levels study, in a form that another game can fill in.

Run:  python3 -I analysis/make_scorecard.py
Reads data/levels.csv, data/attempts.csv, data/offers.csv and the GAME block below.
Writes scorecard.csv (metric id, label, value, source) and scorecard.md.

Metrics marked "table" are computed from the data. Metrics marked "observed" are rules or
prices read from the screen; they live in the GAME block and are filled in by hand per game,
with the scope in which they were seen. Metrics marked "derived" rest on a rule applied to the
data (here: the Magic Pots stage of each attempt), so they describe the log, they do not test it.
"""
import csv
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# ---------------------------------------------------------------------------
# Game-specific facts, read from the screen (not computable from the tables)
# ---------------------------------------------------------------------------
GAME = {
    "game": "Royal Kingdom",
    "studio": "Dream Games",
    "platform": "iOS, Türkiye store",
    "played": "2026-11-04 to 2026-11-11",
    "real_money_spent": "0",
    "continue_first_offer": "+5 moves for 900 coins (first offer on a level, 30 of 30 recorded levels)",
    "continue_ladder": "first offer of each attempt: +5 moves per attempt on the level, up to +35, price 900 "
                       "(77 of 77 recorded first offers; 35 consecutive pairs of first offers in the same recording: 33 grew by 5, 2 stayed at the +35 cap). "
                       "Not yet at level 9: +5 on consecutive attempts (form entry; three attempts on a second account, on video)",
    "continue_extras": "2 Electro Balls from the second step (seen on every recorded step 2 to 7; placed on the board in the 2 purchases checked)",
    "continue_second_in_attempt": "1,900 coins for +5 moves and 1 Rocket, seen once (level 57)",
    "continue_reacts_to": "offer content and price: no change seen with distance to goal, coin balance or streak at stake (one account)",
    "continue_unaffordable_path": "seen on levels 57 and 86: the button opens the shop; cheapest coin pack 1,000 coins for TRY 99.99",
    "exit_friction": "with a streak or event at stake, closing the offer first showed what would be lost and a second tap closed "
                     "(23 of 23 such declines; 0 of 48 declines with nothing at stake)",
    "ad_continue": "none seen in 82 logged offers",
    "streak_feature": "Magic Pots: unlocks at level 32, 5 stages, one free power-up per stage; resets when an attempt is lost, "
                      "a bought continue that wins the attempt keeps it",
    "first_real_money_offer": "level 13: one-time starter pack, TRY 49.99, 2,000 coins plus timed boosters, timer of about two days",
    "special_level_cadence": "every 5th level Kingdom or Dark Kingdom; x4 hard, x9 super hard (from level 24)",
    "new_item_levels": "1, 4, 7, 11, 16, 21, 31, 41, 51, 61, 71, 81, 91 (from 11 on every level ending in 1, plus 16)",
    "in_level_booster_unlocks": "8, 12, 17, 23, 28 (each announced after the level before)",
    "lives": "5 lives, 30 minutes each; refill 900 coins",
}


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if v != "" and v.lstrip("-").replace(".", "", 1).isdigit():
                r[k] = float(v) if "." in v else int(v)
    return rows


def main():
    levels, attempts, offers = read("levels.csv"), read("attempts.csv"), read("offers.csv")
    last = levels[-1]["level"]
    rec_levels = [x for x in levels if x["balance_end"] != ""]
    rec_offers = [o for o in offers if o["source"] == "recording"]
    rows = []

    def add(mid, label, value, source="table"):
        rows.append({"id": mid, "metric": label, "value": value, "source": source})

    def obs(mid, label, key):
        add(mid, label, GAME[key], "observed")

    # A. study
    obs("A1", "Game", "game")
    obs("A2", "Platform and store", "platform")
    obs("A3", "Played", "played")
    add("A4", "Levels covered", f"1-{last}")
    add("A5", "Attempts / failed attempts", f"{len(attempts)} / {sum(a['result'] == 'loss' for a in attempts)}")
    obs("A6", "Real money spent", "real_money_spent")

    # B. difficulty
    fails = {x["level"]: x["fails"] for x in levels}
    add("B1", "First level with a fail", min(l for l, f in fails.items() if f > 0))
    add("B2", "First level with 3 or more fails", min(l for l, f in fails.items() if f >= 3))
    for a in range(1, last + 1, 25):
        band = [x for x in levels if a <= x["level"] <= a + 24]
        add(f"B3_{a}", f"Levels {a}-{a + 24}: fails per level / first-try wins",
            f"{sum(x['fails'] for x in band) / len(band):.2f} / {sum(x['attempts'] == 1 for x in band)} of {len(band)}")
    worst = max(levels, key=lambda x: x["attempts"])
    add("B4", "Most attempts on one level", f"{worst['attempts']} (level {worst['level']})")
    add("B5", "Levels that took 5 or more attempts", sum(x["attempts"] >= 5 for x in levels))
    add("B6", "Levels on which lives ran out", sum(x["lives_out"] for x in levels))

    # C. out-of-moves offer
    obs("C1", "First continue offer", "continue_first_offer")
    obs("C2", "How the offer changes", "continue_ladder")
    obs("C3", "Extras", "continue_extras")
    obs("C4", "Second continue in the same attempt", "continue_second_in_attempt")
    obs("C5", "What the offer reacts to", "continue_reacts_to")
    obs("C6", "When the balance is short", "continue_unaffordable_path")
    obs("C7", "Friction on declining", "exit_friction")
    obs("C8", "Ad-funded continue", "ad_continue")
    add("C9", "Logged offer screens / continues bought",
        f"{len(offers)} / {sum(o['decision'] == 'bought' for o in offers)} ({len(rec_offers)} offers from recordings, {len(offers) - len(rec_offers)} from the form)")
    aff = [o for o in rec_offers if o["affordable"] == 1]
    not_aff = [o for o in rec_offers if o["affordable"] == 0]
    add("C10", "Recorded offers the balance covered: bought", f"{sum(o['decision'] == 'bought' for o in aff)} of {len(aff)}")
    add("C11", "Recorded offers the balance did not cover: bought", f"{sum(o['decision'] == 'bought' for o in not_aff)} of {len(not_aff)}")
    sec = lambda d: statistics.median([o["seconds_to_decision"] for o in rec_offers if o["decision"] == d and o["seconds_to_decision"] != ""])
    add("C12", "Median seconds to decide: bought / declined", f"{sec('bought'):g} / {sec('declined'):g}")
    items = [o for o in rec_offers if o["remaining_units"] != ""]
    near = [o for o in items if o["remaining_units"] <= 3 and o["goals_open"] == 1]
    add("C13", "Near-miss offers (one goal open, 3 or fewer items left), of recorded offers with an item goal", f"{len(near)} of {len(items)}")

    # D. economy
    rewards = sum(x["reward_coin"] for x in rec_levels)
    spent = sum(x["coins_spent"] for x in rec_levels)
    start, end = rec_levels[0]["balance_begin"], rec_levels[-1]["balance_end"]
    income = read("coin_income.csv")
    other = sum(i["amount"] for i in income)
    assert start + rewards + other - spent == end, "coin ledger does not close"
    n = len(rec_levels)
    add("D1", f"Coin income per level, levels {rec_levels[0]['level']}-{last}: level rewards / non-level coin rewards "
              f"({len(income)} itemized)", f"{rewards / n:.1f} / {other / n:.1f}")
    add("D2", "Share of coin income from non-level coin rewards", f"{100 * other / (rewards + other):.0f}%")
    add("D3", "First continue price in average level rewards", f"{900 / (rewards / n):.1f}")
    add("D4", "Coins spent on continues as a share of coin income", f"{100 * spent / (rewards + other):.0f}%")
    obs("D5", "First real-money offer", "first_real_money_offer")
    obs("D6", "Lives", "lives")

    # E. win streak
    obs("E1", "Win-streak feature", "streak_feature")
    st = [a for a in attempts if a["streak_step_at_start"] != ""]
    best, run = 0, 0
    for x in levels:
        run = run + 1 if x["streak_step_first_attempt"] == 5 else 0
        best = max(best, run)
    add("E2", "Longest run of levels started at the top stage", best, "derived")
    top = [a for a in st if a["streak_step_at_start"] == 5]
    zero = [a for a in st if a["streak_step_at_start"] == 0]
    add("E3", "Attempts started at the top stage: level passed (all are first attempts)",
        f"{sum(a['result'] == 'win' for a in top)} of {len(top)}", "derived")
    add("E4", "Attempts started at stage 0: level passed (all are retries, so E3 and E4 do not isolate the streak)",
        f"{sum(a['result'] == 'win' for a in zero)} of {len(zero)}", "derived")
    add("E5", "Free power-ups placed by the streak (sum of stages at the start of each attempt)",
        sum(a["streak_step_at_start"] for a in st), "derived")

    # F. content cadence
    obs("F1", "Special levels", "special_level_cadence")
    obs("F2", "Levels that introduce a new item", "new_item_levels")
    obs("F3", "In-level boosters first usable on levels", "in_level_booster_unlocks")

    with open(os.path.join(ROOT, "scorecard.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "metric", "value", "source"])
        w.writeheader()
        w.writerows(rows)
    lines = [f"# First-100-levels scorecard: {GAME['game']}", "",
             "Same metrics, same definitions, for every game measured with this protocol (see `PROTOCOL.md`).",
             "\"table\" = computed from `data/`; \"observed\" = read from the screen and entered by hand, with its scope; "
             "\"derived\" = computed after applying a rule to the data, descriptive only.", "",
             "| Id | Metric | " + GAME["game"] + " | Source |", "|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['metric']} | {r['value']} | {r['source']} |" for r in rows]
    with open(os.path.join(ROOT, "scorecard.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
