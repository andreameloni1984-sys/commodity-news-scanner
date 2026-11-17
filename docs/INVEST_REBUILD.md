# Gagarin / Sputnik — Invest research rebuild

The production scan entry points now run the independent `invest_scanner` package.
Gagarin selects at most two long candidates from a starter universe of 40 US
stocks. Sputnik first selects dated company-specific primary-source events,
then requests prices only for the affected stocks. No orders are sent, including
in demo. Existing legacy helpers and historical rule files remain available for
regression research; the new scanner does not invoke the commodity pipeline,
its trading governor, CFD execution, or demo-order code.

## Run

```sh
python -m invest_scanner gagarin
python -m invest_scanner sputnik
python -m pytest -q tests/test_invest_scanner.py
```

`python main.py` in Gagarin and `python trump_tracker.py` in Sputnik route to the
new scanner. `--notify` explicitly enables Telegram delivery. The GitHub
workflow is manual only, with notifications off by default; it does not restart
previously paused schedules. Historical Telegram polling/listener and hosting
entry points remain paused and have not been migrated; do not start them for
Invest. Use the new scan workflow for the rebuilt bots.

## Prices, eligibility and timing

- A bounded starter list of 40 stocks, not the whole Trading 212 catalog. ETFs
  are intentionally not inferred from US ticker availability for an Italian
  retail account. Expansion requires explicit market/currency/symbol mappings.
- Optional `T212_API_KEY` and `T212_API_SECRET` read only
  `/api/v0/equity/metadata/instruments`. Metadata scope is sufficient. Environment
  is `demo` by default; `T212_ENVIRONMENT=live` changes only the catalog GET.
  The key must belong to the selected environment. No order endpoint exists in
  this package. Do not put keys or account data in repository files.
- Only exact STOCK/USD/shortName/broker-ticker matches are accepted from the
  account catalog. Without keys, research continues with an explicit
  `DA_VERIFICARE_SU_INVEST` label and Telegram opportunities are suppressed.
  Presence in metadata is not a guarantee that a broker will accept an order.
- Independent Yahoo M5 OHLCV and timestamped regular-market quotes, two hosts,
  four price workers, bounded timeout. The public endpoint is not a guaranteed
  live data service. There is no daily-price fallback for intraday signals.
- The provider's actual regular-session boundaries handle holidays, DST and
  early closes. At least 21 complete M5 candles *in that session* are required:
  the first setup can appear about 105 minutes after opening. This is a data
  warm-up, not a fixed Italian-hour trigger. Closed markets, stale quotes,
  missing bars, currency mismatches and incomplete candles cannot trigger.
- The initial setup is a 20-bar breakout above session VWAP and EMA20, positive
  15-minute momentum, and limited extension from EMA20. ATR14 stop, target 2R,
  and exit reminder five minutes before session close. There are no new entries
  in the last 15 minutes. Exits are research levels, not broker orders.
- Seeded EMA retains the formula tested in `engine/intraday_indicators.py` in
  Gagarin. These are engineering tests, not evidence of profitable trading.
- Spread, slippage, FX conversion and taxes are not modeled. No probability of
  success or net expected profit is claimed. Paper results with these costs are
  required before making performance claims.

## News

The White House news index is used only to discover individual official
articles; publication time and content come from the individual page. This
replaces the unavailable `/feed/` endpoint. Default feeds also include Nvidia
press releases and Federal Reserve releases. Approved official publishers can
be configured through semicolon-separated `INVEST_NEWS_FEEDS`; hosts must also
be explicitly present in `PRIMARY_HOSTS`.

Articles must be less than 24 hours old, have a timezone-aware publication time,
mention the stock's company, and contain a specific potentially favorable event
in the same sentence. The sentence must be found on the original article page.
Negations, rumor language and adverse-event words in relevant sentences exclude
an event. Index pages, social-media archives and Google News redirects cannot
serve as verified evidence. Source failures are visible in scan diagnostics;
complete source failure is an error for Sputnik.

Verification means original publisher and text have been checked. It does not
independently prove a publisher's assertion, causality, materiality or future
price direction. The keyword rule is deliberately limited, not a general news
understanding model. Policies without an explicit company match may be missed.
The new long setup still needs price confirmation. Gagarin can select a technical
setup without news; every attached news item passes the same provenance checks.

## Delivery and persistence

Maximum two candidates per scan and two new symbol alerts per New York session
date, with confirmed Telegram message IDs required before state is saved.
State is private operational data under `.invest-state`, ignored by git; the
manual workflow uses Actions cache and never commits it. Cache loss or eviction
can lose deduplication, so durable private storage is needed before unattended
schedules are re-enabled. A delivery timeout after Telegram accepts a message
can also cause a retry duplicate (Telegram has no idempotency key).

## Validation on 2026-11-17

Tests cover long-only selection, stop/target geometry, closed/incomplete/stale
candles, mismatched instruments, primary-source evidence, stale/future/rumored
news, catalog filtering, top-two ranking, news-first price scans, daily alert
limits and delivery failures. Live read-only smoke tests checked Yahoo prices,
Nvidia and Fed feeds. No broker credentials, orders or Telegram sends were used.

API reference: https://docs.trading212.com/api/instruments/instruments
