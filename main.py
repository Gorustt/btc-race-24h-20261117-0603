"""Dip-ladder bot for make.fun btc-race-24h-20261117-0603.

Trades cbBTC/USDC 1-minute bars, long only, starting from 1,000 USDC paper.
The dev window (24h, BTC +0.53%, range 63,874-65,467) is a calm, choppy,
range-bound tape: 1-minute return stdev 0.064%, no capitulation, worst
60-minute drop only -2.06%. On it, shallow-dip and rolling-high dip-buying
LOSE (they buy into the grind and bleed on fees), and a deep-dip sniper
never fires at all. What works is buying a genuine excursion below a SLOW
trend: the close 0.5% below a 300-minute EMA, then scaling in with the
second half if it falls to 0.8% below, and selling the bounce at +1.8%
over the average entry (or -1.2% stop, or after 240 bars). Three round
trips on the dev window, all winners, max drawdown 0.73%.

Grid-searched on the dev window with an exact local replay harness, picked
for robustness, not dev rank: the parameters sit on a flat plateau
(dip 0.004-0.0055, TP 0.012-0.018, EMA 240-360 all give +20 to +24 USDC),
and every stress check stays positive (first half +21.01, second half
+3.05, -1% drift +19.26, +1% drift +10.50). TP 0.018 (revised from 0.016)
holds round trip 1 two bars longer for a higher exit; TP 0.019 was
rejected — its -1% drift check goes negative. The final race window is
unseen, so the bot is deliberately selective: if the race window has no
excursion below the slow EMA it stays in cash rather than bleeding out
in the grind.

Entry price is the position's average cost from the account state (never
an assumed price). All decisions are pure functions of the bar stream:
no clock, no environment, no randomness, so two runs agree byte for byte.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = None  # set from hello: the competition's single symbol
EMA_PERIOD = 300  # slow trend: 300 one-minute closes (~5 hours)
DIP1 = 0.005  # first arm: close this far below EMA300, half the cash
DIP2 = 0.008  # second arm: close this far below EMA300, the rest
TAKE_PROFIT = 0.018  # sell when close is this far above the average entry
STOP_LOSS = 0.012  # sell when close is this far below the average entry
MAX_HOLD = 240  # sell after this many bars held, whatever the price
MAX_SLIPPAGE_BPS = 200  # 2%: covers the largest 1-minute move seen (~0.65%)
NO_BUY_AFTER_BARS = 1380  # stop opening with 60 bars left in the window

_closes = []  # closes of scored bars, oldest first
_ema = None  # EMA(EMA_PERIOD) of closes
_buy_bar = 0  # scored bar of the first arm of the open position
_arms_filled = 0  # buy fills in the open position (0 when flat)


def on_hello(state):
    global SYMBOL
    SYMBOL = state.hello["symbols"][0]["symbol"]


def _note_fills(state, batch):
    """Count filled buys (arms), reset on a filled sell."""
    global _arms_filled
    for fill in batch.get("fills", []):
        if fill.get("symbol") != SYMBOL:
            continue
        if fill.get("side") == "buy" and fill.get("status") == "filled":
            _arms_filled += 1
        elif fill.get("side") == "sell" and fill.get("status") == "filled":
            _arms_filled = 0


def _avg_entry_price(state):
    """Average entry price of the open position, in raw price units.

    cost is quote units spent, qty is qty-scale units, price is
    price-scale units: value(qty, p) = qty * p * 10^6 / 10^13.
    """
    holding = state.positions.get(SYMBOL)
    if holding is None or holding.qty <= 0:
        return None
    return holding.cost * 10 ** 13 // (holding.qty * 10 ** 6)


def on_batch(state, batch):
    global _ema, _buy_bar
    _note_fills(state, batch)
    if state.warming_up:
        return []
    bar = None
    for b in batch.get("bars", []):
        if b.get("symbol") == SYMBOL:
            bar = b
            break
    if bar is None:
        return []
    close = int(bar["c"])
    _closes.append(close)
    k = 2.0 / (EMA_PERIOD + 1)
    _ema = float(close) if _ema is None else close * k + _ema * (1.0 - k)

    holding = state.positions.get(SYMBOL)
    if holding is not None and holding.qty > 0:
        avg = _avg_entry_price(state)
        if avg is not None:
            if close >= avg * (1.0 + TAKE_PROFIT):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if close <= avg * (1.0 - STOP_LOSS):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if state.seq - _buy_bar >= MAX_HOLD:
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        # Scale in: second arm if the dip deepened below DIP2.
        if _arms_filled == 1 and state.cash >= 1_000_000:
            if close < _ema * (1.0 - DIP2):
                notional = min(500_000_000, state.cash)
                if notional >= 1_000_000:
                    return [{"side": "buy", "symbol": SYMBOL,
                             "notional_quote_units": notional,
                             "max_slippage_bps": MAX_SLIPPAGE_BPS,
                             "client_id": state.client_id()}]
        return []

    # Flat: buy the first arm on a dip below the slow EMA, half the cash.
    if state.seq >= NO_BUY_AFTER_BARS:
        return []
    if len(_closes) < EMA_PERIOD + 1:
        return []
    if close < _ema * (1.0 - DIP1):
        _buy_bar = state.seq
        notional = state.cash // 2
        if notional >= 1_000_000:
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": notional,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS,
                     "client_id": state.client_id()}]
    return []


makefun_bars.run(on_batch, on_hello=on_hello)
