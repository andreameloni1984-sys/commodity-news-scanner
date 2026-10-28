# Project log — 2026-10-28

## Change: narrow operational universe

- Gagarin enabled universe reduced to gold, silver, copper, WTI and Brent.
- Invest universe keeps SPY and QQQ enabled; single-stock entries remain defined but disabled.
- Added regression tests for enabled lists and universe consistency.
- Grain instruments (wheat, corn, soybean) are intentionally not enabled yet because the current provider adapter's exact symbols have not been verified. Next task: inspect adapter symbol mapping and enable the three grains only after provider-specific symbols are confirmed.
- This branch has not been deployed or merged. Provider availability and full CI test results still need verification.
