# Sources and related work

What I used, and what for. Summaries are in my own words.

## The game's own documentation

- **Royal Kingdom help center, Magic Pots.** The win-streak rule I applied to my win and loss sequence: each win adds a stage, each stage adds a free power-up at the start of the next level, and a lost attempt resets it. <https://dreamgames.helpshift.com/hc/en/6-royal-kingdom-1676903479/faq/307-magic-pots/>
- **Royal Kingdom help center, other articles.** The official English names of events, items and level types. My client was in Turkish.

## A/B testing in puzzle games

- **Katsarou et al. (King), "On a Scale-Invariant Approach to Bundle Recommendations in Candy Crush Saga", 2024.** <https://arxiv.org/abs/2408.06799> A team at King tested a model that recommends bundles against a rule written by the game's own experts, in live experiments, and reported that players clicked and took the model's bundles more often. The paper reports no revenue figure. I use it for one thing: the design of the follow-up test in the memo, a context-aware choice against a simple rule. Its numbers are about bundle recommendations and say nothing about a continue offer in another game.
- **My earlier analysis of the Cookie Cats A/B test.** <https://github.com/dorukozcan/cookie-cats-ab-test> It uses the public dataset from DataCamp's project *Mobile Games A/B Testing with Cookie Cats*: 90,189 players, the first gate at level 30 or at level 40, retention after one and seven days. This memo keeps the same form: one mechanic, one test, one primary metric.

## What I did not use

This study uses no analysis of the game's code. It looks only at what a player sees on the screen, and the reported counts and tables can be reproduced from the data in `data/`.
