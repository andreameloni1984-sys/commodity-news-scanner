# SOYUZ GAGARIN — Execution Layer

Telegram is not part of the execution path.

Flow: GAGARIN -> canonical PAPER_SIGNAL -> execution/router -> broker adapter

Safe defaults: EXECUTION_ENABLED=0, EXECUTION_BROKER=paper, PAPER_TRADING_ONLY=1.

With these defaults simulated orders are recorded locally and no broker is contacted.

IBKR paper path requires an authenticated IBKR Client Portal Gateway session. Configure environment variables outside source files and keep PAPER_TRADING_ONLY=1 during validation.

Settings: EXECUTION_ENABLED=1, EXECUTION_BROKER=ibkr, PAPER_TRADING_ONLY=1, IBKR_GATEWAY_URL=https://localhost:5000/v1/api, EXECUTION_DEFAULT_QUANTITY=1.
