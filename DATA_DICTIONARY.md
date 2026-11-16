# Data dictionary

One player's first 100 levels of Royal Kingdom (iOS, Türkiye store, 4 to 11 November 2026, no money spent). Blank cells mean "not recorded", never zero.

## How each value was obtained

| Label | Meaning | Where it shows |
|---|---|---|
| recording | Read from a frame of a screen recording and checked by eye | `source = recording` |
| form | Typed into a form right after the level (levels 1-14, before recording started) | `source = form` |
| inferred | Two attempts on level 68 made off camera, counted from the +15 offer that followed | `source = inferred` in `attempts.csv` |
| derived | Computed by applying the game's published Magic Pots rule to the win and loss sequence | `streak_step_*` columns |
| recalled | My reasons for buying or declining, given on 11 and 12 November | Not in these tables; quoted in the memo |

The game's client was in Turkish. A few text values are the Turkish names: `Elektrik Topu` is Electro Ball, `Roket` is Rocket, `Sihirli Kazan` is Magic Pots, `Zindandan Kacis` is Dungeon Escape, `Guc Akini` is Power Rush and `Alevler` is its flame counter. Goal items (`kutu`, `buz`, `sarmaşık`, `baykuş`, `kadeh`, `vazo` and so on) are the game's Turkish item names.

## `data/levels.csv`: one row per level (100)

| Column | Meaning |
|---|---|
| `level` | Level number, 1 to 100 |
| `type` | `normal`, `hard`, `superhard`, or `pve` for Kingdom and Dark Kingdom levels (every fifth level) |
| `goal` | The level's goal as written in the log, in Turkish |
| `goal_units` | Total number of goal items. Blank for Kingdom and Dark Kingdom levels |
| `moves` | Moves at the start of the level |
| `attempts`, `fails` | Attempts on the level, and how many of them were lost |
| `moves_left` | Moves left when the level was won |
| `coins_spent` | Coins spent on continues on this level |
| `offer_seen` | 1 if an out-of-moves offer was seen on this level |
| `lives_out` | 1 if lives ran out on this level |
| `pre_boosters`, `in_boosters` | Pre-level boosters picked and in-level boosters used, over all attempts |
| `streak_step_first_attempt` | Magic Pots stage when the first attempt started, 0 to 5. Derived. Blank before level 32, where the feature unlocks |
| `reward_coin`, `reward_elixir` | Coins and potions shown on the win screen. Recorded levels only |
| `balance_begin`, `balance_end` | Coin balance before the first attempt and after the win. Recorded levels only |
| `started_utc`, `saved_utc` | Day the level was started and finished (UTC). Times of day are removed in this package |
| `source` | `form` for levels 1-14, `recording` for levels 15-100 |

## `data/attempts.csv`: one row per attempt (179)

| Column | Meaning |
|---|---|
| `level`, `type` | As above |
| `attempt` | Attempt number on this level, from 1 |
| `attempts_on_level` | Total attempts on this level |
| `result` | `win` or `loss` |
| `out_of_moves` | 1 if the attempt ran out of moves at least once. Blank for six lost attempts with no offer row |
| `continue_bought` | 1 if a continue was bought in this attempt |
| `streak_step_at_start` | Magic Pots stage when the attempt started. Derived. Blank before level 32 |
| `pre_boosters`, `in_boosters` | Pre-level boosters picked and in-level boosters used in this attempt |
| `source` | `recording`, `form` or `inferred` |

## `data/offers.csv`: one row per logged continue offer (82)

| Column | Meaning |
|---|---|
| `offer_id` | Order in which the offers appeared |
| `level`, `type`, `attempt` | Where the offer appeared |
| `seq_in_attempt` | 1 for the first offer of an attempt, 2 for an offer after a bought continue in the same attempt |
| `moves_offered` | Extra moves offered |
| `extras` | What came with the moves, if anything |
| `price_coin` | Price in coins |
| `balance` | Coin balance when the offer appeared. Blank for the two form offers on level 9 |
| `affordable` | 1 if the balance covered the price |
| `decision` | `bought` or `declined` |
| `remaining` | Goal items still open when the moves ran out, as text |
| `remaining_units`, `goals_open` | The same as a number of items and a number of open goals. Blank for Kingdom and Dark Kingdom levels |
| `remaining_share` | `remaining_units` as a share of the level's `goal_units` |
| `streak_step_at_stake` | Magic Pots stage that a lost attempt would reset. Derived |
| `other_stake` | An event run that a lost attempt would end |
| `exit_warning` | What the loss warning named when the offer was closed. Blank if no warning appeared |
| `seconds_to_decision` | From the first frame showing the offer to the purchase or the fail screen, at one-second resolution. It measures the time between two visible screens, not a tap |
| `welcome_pack_shown` | 1 if the one-time starter pack card was on screen under the offer (25 offers, levels 18-57). Entered from the frames and checked against the OCR |
| `pass_card_first_4_frames` | 1 if the Kingdom Pass card is readable in the first four sampled frames of the offer screen (the second it appears and the three after it); on all 53 such offers it shows the same number of extra moves as the coin offer. 0 if it is not readable in those frames. Blank where the offer was on screen for a single sampled frame (one offer) and for the form offers. The card shares a carousel with the starter pack card, so later frames can show either card; this column says nothing about the rest of the screen time |
| `recording`, `t` | Recording (R01 to R23) and second at which the offer appears |
| `time_utc` | Day (UTC) |
| `source` | `recording` or `form` |

## `data/coin_income.csv`: one row per non-level coin reward (21)

Coins that did not come from a level's win screen: chests, event stages, the Kingdom Pass free track, a team reward and one reward for helping a teammate. Most were collected between levels; four during or right after one.

| Column | Meaning |
|---|---|
| `item` | Row number |
| `timing`, `level` | Whether the reward was collected `before`, `during` or `after` this level |
| `source` | Where the coins came from, with the official English event names. Büyülü Hazine is the Turkish client name of an event whose English name I could not verify |
| `amount` | Coins |
| `balance_before`, `balance_after` | Balance read on screen around the reward |
| `recording`, `t_from`, `t_to` | Recording, the last second the old balance is visible and the first second the new one is |

## `data/side_checks.csv`: six offers seen outside the 100 levels

Two short checks on 12 November 2026. They are not part of any count in the tables above.

| Column | Meaning |
|---|---|
| `check` | `second_account` (a new account on another phone, levels 1 to 17, three planned fails on level 9), `english_client` (the study account with the client in English, level 102) |
| `date`, `game`, `account`, `client` | When, which game, which account, client language |
| `recording` | S1 or E1. These recordings are separate from R01 to R23 |
| `level`, `attempt`, `seq_in_attempt` | As in `offers.csv` |
| `moves_offered`, `extras`, `price_coin`, `balance`, `streak_step_at_stake`, `decision` | As in `offers.csv` |
| `card_under_offer` | What was shown under the offer, where I noted it |
| `t` | Second in the recording |
| `note` | Context |

## `data/recordings.json`: one entry per recording (23)

`id` (R01 to R23, in order of recording), `date` (UTC day the recording started), `duration_s`, and `ocr_last_t` (the last second read, so `ocr_last_t + 1` is the number of frames).
