# btc-race-bot

A long-only trading bot for the make.fun bounty
`btc-race-24h-20261111-0801`: it trades Coinbase Wrapped BTC (cbBTC) on
1-minute on-chain bars, starting with $1,000 of paper money.

## Strategy

Crash-dip with strict exits — it sits in cash through the noise and only
trades a washout big enough to pay the ~26 bps round-trip cost (4 bps fee,
2 bps slippage, ~7 bps own price impact each way) several times over:

1. **Washout:** the close falls at least 120 bps below the highest close of
   the previous 120 bars.
2. **Bounce:** the close then recovers at least 30 bps from the lowest close
   seen since that high.
3. **Buy** with all cash. **Exit** on the first of: +150 bps take profit,
   −80 bps stop loss, or −150 bps trailing stop from the post-entry peak.
4. Re-arm and wait for the next washout.

All decisions are integer basis-point comparisons on closes only, so two
runs on the same bars produce identical orders. No network, no wall clock,
no files outside the repo, standard library only.

## Dev-window backtest (frozen 24 h window from the kit)

| Metric | Value |
|---|---|
| Net PnL (after all fees) | **+$8.48** |
| Trades | 1 (buy after the intraday washout, held to the end) |
| Max drawdown | 1.01% (cap: 25%) |
| Fees paid | $0.80 |

Dev gate (net PnL > $0): **cleared**.

## Run

```sh
python3 -P -s main.py
```

The bot speaks `agent-fun/bars-replay/v1` (newline-delimited JSON on
stdin/stdout). Grade locally with the kit:

```sh
node cli/makefun.mjs grade-local --kit <kit-dir> --bot <this-repo> --driver docker
```

## License

MIT — see [LICENSE](LICENSE).
