# SPDX-License-Identifier: MIT
"""Crash-dip long-only bot for the make.fun btc-race-24h-20261111-0801 bounty.

Strategy (one asset, CBBTC, 1-minute bars, $1,000 paper, long only):

  * Wait for a washout: the close falls at least DROP_BPS below the highest
    close of the previous LOOKBACK bars.
  * Then wait for a bounce: the close recovers at least REC_BPS from the
    lowest close seen since that high.
  * Buy with all cash. Exits, whichever comes first:
      - take profit at TP_BPS above the entry close,
      - stop loss at SL_BPS below the entry close,
      - trailing stop at TRAIL_BPS below the highest close since entry.
  * After an exit the bot re-arms and can catch the next washout.

Why this shape: a full-size round trip costs about 26 bps (4 bps fee,
2 bps slippage, ~7 bps of own price impact each way), so chasing every
1-minute wiggle loses money to fees. The dev window's money was in one
large intraday washout and recovery; this bot sits in cash through the
noise and only trades a washout big enough to pay the round trip several
times over. All thresholds are integer basis-point comparisons, so two
runs on the same bars produce byte-identical orders.

Run: python3 -P -s main.py  (stdin/stdout speak agent-fun/bars-replay/v1)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
LOOKBACK = 120          # bars of history defining the recent high
DROP_BPS = 120          # washout: close this far below the recent high
REC_BPS = 30            # bounce: close this far above the washout low
TP_BPS = 150            # take profit above the entry close
SL_BPS = 80             # stop loss below the entry close
TRAIL_BPS = 150         # trailing stop below the post-entry peak
MAX_SLIPPAGE_BPS = 200  # cap on the fill vs the latest close

closes = []             # closes seen so far (ints, price_scale 5)
armed_low = None        # lowest close since the washout started, else None
entry_close = None      # close the current position was entered at
peak_close = None       # highest close since entry


def _below(price, ref, bps):
    """price <= ref * (1 - bps/10000), in integers."""
    return price * 10000 <= ref * (10000 - bps)


def _above(price, ref, bps):
    """price >= ref * (1 + bps/10000), in integers."""
    return price * 10000 >= ref * (10000 + bps)


def on_batch(state, batch):
    global armed_low, entry_close, peak_close
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    close = int(bar["c"])
    closes.append(close)

    held = state.positions.get(SYMBOL)
    if held is not None:
        if peak_close is None or close > peak_close:
            peak_close = close
        if entry_close is not None:
            if _above(close, entry_close, TP_BPS):
                return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS,
                         "client_id": "s%d" % state.seq}]
            if _below(close, entry_close, SL_BPS):
                return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS,
                         "client_id": "s%d" % state.seq}]
        if peak_close is not None and _below(close, peak_close, TRAIL_BPS):
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS,
                     "client_id": "s%d" % state.seq}]
        return []

    # Flat: look for a washout + bounce.
    entry_close = None
    peak_close = None
    if len(closes) <= LOOKBACK:
        return []
    high = max(closes[-LOOKBACK - 1:-1])
    if _below(close, high, DROP_BPS):
        if armed_low is None or close < armed_low:
            armed_low = close
        if armed_low is not None and _above(close, armed_low, REC_BPS):
            armed_low = None
            entry_close = close
            peak_close = close
            if state.cash >= 1000000:
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": state.cash,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS,
                         "client_id": "b%d" % state.seq}]
    else:
        armed_low = None
    return []


makefun_bars.run(on_batch)
