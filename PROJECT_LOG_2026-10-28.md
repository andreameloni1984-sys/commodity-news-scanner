# Project log — 2026-10-28

## Change: narrow operational universe

- Gagarin enabled commodity universe reduced to gold, silver, copper, WTI and Brent.
- Invest universe keeps SPY and QQQ enabled; individual stock entries remain defined but disabled.
- Added regression tests for enabled lists and universe consistency.
- Updated Telegram commodity aliases to recognize copper/rame and reject excluded instruments.
- Initial CI found seven stale alias expectations; after updating those tests, a follow-up run found one missing copper alias. The alias resolver has now been corrected. CI must confirm the latest commit.
- Grain instruments (wheat, corn, soybean) are intentionally not enabled yet because provider-specific price mappings still need verification.
- Changes are in branch chore/focus-operational-universe; not merged/deployed.
