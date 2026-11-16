#!/usr/bin/env python3
"""Players needed per arm for the experiment proposed in the memo.

Primary metric: share of assigned players who pass the level in the same session, counted over
everyone assigned at their first eligible moment (not only buyers). The base rate is the control
arm's value of that metric. One player's log cannot give it; the team's data can. The grid below
only shows how the answer moves with the base rate and with the smallest lift worth detecting.

Two-sided two-proportion z-test, equal arms, alpha 0.05, power 0.80, one observation per player.
If assignment is by team instead of by player, multiply by the design effect 1 + (m - 1) * ICC,
where m is the number of assigned players per team and ICC the within-team correlation.

Run:  python3 -I analysis/sample_size.py [--base 0.60] [--lift 0.02]
"""
import argparse
from math import ceil, sqrt
from statistics import NormalDist

ALPHA, POWER = 0.05, 0.80


def per_arm(p1, p2, alpha=ALPHA, power=POWER):
    pbar = (p1 + p2) / 2
    za, zb = NormalDist().inv_cdf(1 - alpha / 2), NormalDist().inv_cdf(power)
    n = (za * sqrt(2 * pbar * (1 - pbar)) + zb * sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
    return ceil(n)


def design_effect(m, icc):
    return 1 + (m - 1) * icc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=float, help="control arm's same-session pass rate, e.g. 0.60")
    ap.add_argument("--lift", type=float, help="smallest absolute lift worth detecting, e.g. 0.02")
    args = ap.parse_args()
    if args.base and args.lift:
        print(f"base {args.base:.0%}, +{args.lift * 100:g} points: {per_arm(args.base, args.base + args.lift):,} players per arm")
    else:
        lifts = (0.01, 0.02, 0.03, 0.05)
        print("Players per arm, by base rate of the primary metric and absolute lift (placeholders, not estimates):\n")
        print("| Same-session pass rate in control | " + " | ".join(f"+{l * 100:g} points" for l in lifts) + " |")
        print("|---|" + "---|" * len(lifts))
        for p in (0.40, 0.50, 0.60, 0.70, 0.80):
            print(f"| {p:.0%} | " + " | ".join(f"{per_arm(p, p + l):,}" for l in lifts) + " |")
        print()
        for m, icc in ((5, 0.02), (20, 0.02), (20, 0.05)):
            print(f"team-level assignment, {m} assigned players per team, ICC {icc}: x{design_effect(m, icc):.2f}")
