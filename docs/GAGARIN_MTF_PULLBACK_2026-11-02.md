# GAGARIN — MTF 15m/5m timestamp and futures-contract contract

Date: 2026-11-02

## Purpose

The 15m/5m pullback overlay is a diagnostic only. It does not authorize an
entry, alter scores, change BIAS, modify the Governor, or create entry/SL/TP.

## Required producer payload

Each timeframe must be an object with:

- `provider`
- `symbol`
- `contract` (explicit contract identifier, not a continuous-series alias)
- `contract_expiry`
- `currency`
- `unit`
- `market_type=FUTURES`
- `completed=true`
- `candles`: at least 200 completed OHLC bars

Each candle must contain `timestamp` (UTC epoch seconds representing the
candle close) and finite `open`, `high`, `low`, `close`.

The 15m and 5m payloads must match on provider, symbol, exact contract,
expiry, currency and unit. Their latest completed candle timestamps must be
identical. Every timestamp must align to its timeframe and be strictly
increasing; gaps are permitted only when they are whole timeframe multiples.

## Freshness

- 15m: maximum age 1,800 seconds.
- 5m: maximum age 600 seconds.
- Future clock skew: maximum 120 seconds.
- Both timeframes must be completed; an in-progress candle is rejected.

## Basis and historical values

Only explicit futures contract data is accepted. Spot and CFD observations
are rejected. Finite negative settlements are accepted for historical replay
because WTI futures traded below zero in April 2020; ATR must remain positive.

## Current limitation

No production data producer has yet been verified to supply this complete
payload. Until one does, the adapter reports `NOT_PROVIDED` and Telegram
shows that state. The feature must not be described as live or validated on
market data until provider, contract, timestamps, currency and unit have
been observed from a real response.

## Public-project study

The independent implementation was informed by the general multi-timeframe
setup/confirmation pattern described by public Telegram bot repositories.
No source code was copied from projects without a verifiable reuse license.
The implementation is original and dependency-free.
