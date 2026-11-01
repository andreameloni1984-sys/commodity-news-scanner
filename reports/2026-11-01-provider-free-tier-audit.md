# Free market-data provider audit — 2026-11-01

## Decision
Do not add a third provider to the execution route in this run. The current evidence supports one futures execution feed plus reference-only feeds with materially different bases or contract identity. A provider count must not be mistaken for independent, comparable futures coverage.

## Narwhal — free delayed futures reference only
Official sources checked on 2026-11-01:
- Pricing: https://narwhalapi.com/pricing
- Futures API: https://narwhalapi.com/api/futures

Verified documented conditions:
- Free plan: $0/month, 5,000 successful requests/month, 30 requests/minute, no automatic overage charges.
- A free API key is required.
- Free futures prices are delayed by 15 minutes and expose a source timestamp and delayed/stale state.
- The API series is the continuous front-month contract, not adjusted; it steps on roll days.
- Free history is daily OHLC only; one-minute bars require Basic/Pro.
- Futures responses do not include volume.

The repository's one-root-per-15-minute reference rotation is nominally about 2,880 requests per 30 days if it runs once each 15-minute slot and makes exactly one successful request per slot. This is below the documented 5,000 monthly quota, but actual usage and a live free-key response were not checked in this run.

Narwhal remains reference-only. It does not expose the exact delivery month in the integrated response and its upstream source independence is not independently verified. Do not calculate a futures deviation or use it for entry/SL/TP.

## SILV DATA — spot reference only
Official documentation: https://datadocs.silv.app/

- Free JSON API without authentication: https://data.silv.app/commodities.json
- Gold and silver spot observations are on a 15-minute update schedule.
- Energy reference data is on a 30-minute schedule; agricultural data is daily.
- The integrated SILV path is limited to gold/silver spot references and remains separate from Yahoo futures execution.
- Provider-reported component sources are metadata, not proof that each component is legally or technically independent.

SILV is not a futures execution or same-contract futures comparison source.

## Candidates rejected for execution
- commodities.sh: the catalog is free, but the price observation route is documented at $0.01 per observation and can return HTTP 402 when payment enforcement is enabled. Excluded.
  - https://commodities.sh/docs/getting-started
- ConvexTrade: the public API documents free non-commercial research use and daily WTI/Brent cash series with 30-minute cache; it is not an exchange futures quote feed and is not a same-contract execution reference. Not integrated.
  - https://convextrade.com/tools/api
- Stooq: the evidence found in this run did not establish a currently accessible, terms-compatible, same-contract commodity futures endpoint for this bot. Not integrated.

## Current Gagarin basis map
- Yahoo Finance continuous futures: sole active futures execution route.
- Narwhal: optional delayed continuous front-month futures reference, free key required, reference-only.
- SILV DATA: no-auth spot reference for gold/silver only.
- BiQuote commodity CFD/spot and Twelve Data legacy helpers are not futures execution fallbacks.

No averaging across these bases. No spot price is substituted for a futures entry, stop, or target. A percentage deviation is valid only when the exact instrument, currency, unit, contract month, and comparable timestamps are verified; otherwise report the basis separately or leave deviation null.

## Open
- Verify a real Narwhal free-key response and actual request usage in the bot runtime.
- Find a third independently sourced, free, accessible futures feed with exact contract/expiry metadata and compatible terms; do not promote a continuous front-month series with unknown provenance as same-contract confirmation.
- Keep provider timestamps, response receipt time, currency, unit, bid/ask, age, and status per observation.
- No live quote or realtime claim is made by this audit.
