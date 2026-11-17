[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/Gorustt/btc-race-24h-20261117-0603/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/Gorustt/btc-race-24h-20261117-0603/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

# Dip-Ladder BTC Bot — make.fun btc-race-24h-20261117-0603

[![make.fun](https://img.shields.io/badge/make.fun-btc--race--24h--20261117--0603-blue)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A long-only cbBTC/USDC trading bot for make.fun's "Race a BTC trading bot
live for 24 hours" bounty ($250 in USDC, top 10 paid).

## Strategy

Buy a genuine excursion below a slow trend, scale in if it deepens, sell
the bounce — and sit in cash the rest of the time.

- **Reference:** 300-minute EMA of 1-minute closes (~5 hours).
- **Arm 1:** close 0.5% below EMA300 → buy with half the cash.
- **Arm 2:** close 0.8% below EMA300 → buy with the rest.
- **Exit:** close 1.8% above the average entry (take profit), 1.2% below
  it (stop loss), or 240 bars held (timeout). No new entries after bar
  1380, so a position is never opened with no time to exit.
- **Entry price** is the position's average cost from the account state,
  never an assumed price. Pure function of the bar stream: no clock, no
  environment, no randomness — two runs agree byte for byte.

## Why this shape

The dev window (24h, BTC +0.53%, range 63,874–65,467) is a calm, choppy,
range-bound tape: 1-minute return stdev 0.064%, worst 60-minute drop only
-2.06%. Shallow-dip and rolling-high dip-buying lose on it (they buy into
the grind and bleed on fees), and a deep-dip sniper never fires at all.
Buying only a 0.5% excursion below a 300-minute EMA is selective enough
to catch the real bounces and rare enough to stay out of the chop.

## Local verification (exact replay harness, integer math)

```
cd scratch && python3 replay.py ../repo/main.py
run1: PnL +24.325331 USDC  trades 8  fees 2.025828  maxDD 0.7334%  final cash 1024.325331
run2: PnL +24.325331 USDC  trades 8  fees 2.025828  maxDD 0.7334%  final cash 1024.325331
deterministic (action logs identical): True
```

Robustness (same bot, other windows): first half +21.01, second half
+3.05, −1% drift +19.26, +1% drift +10.50 — every stress check positive.
Parameters sit on a flat plateau (dip 0.004–0.0055, TP 0.012–0.018,
EMA 240–360 all give +20 to +24 USDC), not on an edge.

## Layout

- `main.py` — the bot (Python 3.13, stdlib only)
- `vendor/makefun_bars.py` — byte-identical copy of the kit's Python shim
- `LICENSE` — MIT
- `.makefun/owner.json` — claim file for the entry wallet
