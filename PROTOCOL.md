# First-100-levels protocol

A repeatable way to measure the first 100 levels of a casual puzzle game as a new player, so that two games can be put side by side. Royal Kingdom (November 2026) is the first game measured this way.

Some scripts named below are not in this repository: the sanitising and checking helpers and `build_dataset.py` work on the recordings and on the raw level log, which are not published.

## What comes out

| Output | File | Comparable across games |
|---|---|---|
| One row per level | `data/levels.csv` | Yes, same columns |
| One row per attempt | `data/attempts.csv` | Yes |
| One row per out-of-moves offer | `data/offers.csv` | Yes |
| One page of fixed metrics | `scorecard.csv`, `scorecard.md` | Yes, same metric ids |
| Reproduced tables and figures | `analysis/make_report.py`, `figures/` | Same charts |
| Data checks: values computed from the tables against fixed expected values | `analysis/check_memo_numbers.py` | Per game |
| The written piece | `memo/` | One question per game |

## 1. Before playing

1. New account on a device where the game was never installed. State the store and the country.
2. Decide the spending rule and keep it: no real money, or a fixed budget written down in advance.
3. Play naturally. Deliberate fails and other experiments go on a second account, never on the main one.
4. After the tutorial stretch (about 15 levels), write down 5 to 10 predictions with how each will be measured. They are scored at level 100 and published either way.

## 2. While playing

1. Record the screen for every level. Focus mode on, notification center closed, no other apps.
2. One recording per sitting; note that file-name times can mean the start or the end of the recording depending on how the file was exported.
3. At levels 25, 50, 75 and 100 open the player statistics screen, the shop and the version number.
4. When a new feature or event appears, open its info screen once.
5. After each sitting, write one line per out-of-moves decision: why bought, why not. The recording has no reasons in it.
6. Log the number of moves each attempt starts with, read from the first board frame.

## 3. Processing a batch of recordings

Run in this order (details in `analysis/helpers/README.md`):

1. `video_ocr.swift`: one frame per second, on-device OCR, one JSON line per frame.
2. `helpers/sanitize.py`: remove other players' names, chat, system UI and the player's own username before anything else reads the text.
3. `helpers/events.py`: attempts, offers with decisions, wins with moves left, balances between levels.
4. `helpers/mk_checks.py`: montages of the goal panel at every win and offer, the pre-level popup and the booster bar. Read these by eye; OCR misreads single digits.
5. Write the level rows to the log, then `build_dataset.py`, `make_report.py`, `make_scorecard.py`.

## 4. Checks that must pass

- First-try wins and total wins in the log equal the game's own statistics screen at each checkpoint.
- The coin ledger closes: start + level rewards + non-level coin rewards - spending = balance on screen.
- Every recorded out-of-moves attempt has an offer row; every purchase matches a balance drop.
- Any rule claimed for the offer is asserted in code against all recorded offers.
- The moves at the start of an attempt are compared across the attempts of a level, and across accounts when there is a second one.
- Non-level coin rewards are itemized reward by reward, each with the recording and second of its balance step, so the ledger is not closed by a remainder.
- The OCR parser's reading of each offer is compared with the hand-entered table. Differences are printed, not fatal, and each one is explained in `data/README.md`.

## 5. Privacy

- Recordings stay local. Raw review text stays local.
- OCR text is published only after `sanitize.py` and one more read.
- No names of other players, teams or chat anywhere in tables, notes or figures.

## 5a. How the Royal Kingdom run differed from this protocol

The protocol was written during the first run, so that run does not follow it fully. A second game should.

| Protocol | What happened in Royal Kingdom |
|---|---|
| Record every level | Levels 1-14 come from a form filled in after each level; recording starts at level 15 |
| Statistics screen at levels 25, 50, 75, 100 | Read after levels 10, 24, 50 and 100 |
| One line per decision after each sitting | Reasons were collected on 11 and 12 November, after the play |
| Version number at each checkpoint | Not recorded; the game's settings screen does not show it |
| Predictions after about 15 levels | Written after level 14, before level 15 |
| Deliberate fails on a second account | One sitting on 12 November, after the main run: levels 1-17 on another phone, kept in `data/side_checks.csv` and outside every count |

Every value carries one of five labels: recording, form, inferred, derived or recalled (see `data/README.md`).

## 6. What is specific to one game

| Part | Where | What to change for a new game |
|---|---|---|
| Screen recognition | `analysis/parse_ocr.py`, `helpers/events.py` | The words that identify each screen (offer, fail, win, pre-level, home) and where the numbers sit |
| Rules read from the screen | `GAME` block in `analysis/make_scorecard.py` | Offer rule, streak rule, first real-money offer, cadence |
| Per-attempt details | Tables at the top of `analysis/build_dataset.py` | Offers, boosters per attempt, purchases |
| Language | The log is in the language of the client | Keep a glossary to the official English names |

## 7. Comparing two games

- Metric ids in the scorecard are fixed (A1 to F3). A new game adds a column, never a new definition.
- "table" metrics are computed; "observed" metrics are rules or prices read from the screen and must give the scope in which they were seen; "derived" metrics rest on a rule applied to the data and describe the log without testing it.
- Report the limits next to the numbers: one player, one pass, pace, store.
