# Project log — 2026-10-28

## Change: align catalyst-to-instrument mapping

- Gagarin public-event intelligence now maps news to the selected operational universe: SPY, QQQ, gold, silver, copper, WTI, Brent, wheat, corn and soybean.
- Removed candidate mappings for USD/Forex, Nasdaq100 as a separate instrument, platinum, palladium, sugar, cocoa, coffee, rice, natural gas, defense stocks, crypto, media and real-estate baskets.
- SPUTNIK catalyst watchlist remains WATCH-only and cannot authorize execution.
- Added/updated regression tests for allowed and excluded instruments.
- Provider data mapping for wheat/corn/soybean is still a separate task; the catalyst can identify them, but Gagarin must not issue a price-based signal until verified data is available.
- Validation found that the previous universe cleanup caused seven legacy alias tests to fail because they still expected excluded commodities. Those tests have now been updated to the selected universe; the follow-up CI run must confirm the fix.
- Changes are in branch chore/align-catalyst-watchlist and have not been merged/deployed.
