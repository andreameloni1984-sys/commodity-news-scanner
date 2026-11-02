

## 2026-11-02 — Document private dashboard environment setup without secrets

- Finding: .env.example documented execution and demo-provider settings but omitted the three variables required by the private dashboard: APP_PASSWORD_HASH, APP_SESSION_SECRET, and CLOUD_API_KEY. The login route returns HTTP 503 when either authentication variable is absent. No secret values were inspected.
- Implemented on branch docs/gagarin-private-dashboard-env-20261102: documented local generation of the PBKDF2-SHA256 password hash (600,000 rounds, within the verifier's 200,000–2,000,000 accepted range), a separate random session-signing secret, and a distinct API key. All three assignments remain empty in .env.example; generated values must be configured directly in the hosting Environment UI and never committed or sent in chat.
- Files: .env.example (commit 503e2c8d784b4b46c24cb459b8279b4b977490d9); tests/test_personal_app_pwa.py (final test/code commit de873eafcd060e2e9cf56bf050ef32076b02846c); this research log.
- Regression: require each variable to appear exactly once with an empty assignment, and require the documented generator, accepted PBKDF2 range, and hosting-UI instruction.
- Verification: five PR workflow runs on de873eafcd060e2e9cf56bf050ef32076b02846c completed SUCCESS: SOYUZ Integration Tests 41431196509, Execution Layer 41431196203, NEWS Alert 41431196037, Public Event Brain 41431197836, and PAPER 41431196073. The log-only follow-up commit requires its own CI confirmation before merge.
- Limits/open: Render environment values were not read or changed; deployment, login/logout, API-key authentication, Sputnik handoff and Telegram delivery are not verified live. The Render workspace has not been explicitly confirmed for connector operations. The PWA still lacks a dedicated iOS PNG icon. No paid service, public private-data hosting, or live trading was enabled.
- Safety: no credentials were generated, read, logged or committed; no trading strategy, score, Governor, entry/SL/TP or PAPER authorization changed.
- Research note: Freqtrade's current Lookahead Analysis compares a full backtest against isolated signal backtests to detect indicator/entry/exit changes, but can only validate signals that actually trigger; this caveat must be preserved when adapting it to GAGARIN. Reference: https://www.freqtrade.io/en/stable/lookahead-analysis/
