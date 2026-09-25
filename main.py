"""
SOYUZ GAGARIN — MAIN RUNNER v2.2

Pipeline:
    UNIVERSE
        ↓
    GAGARIN ENGINE
        ↓
    SAFETY
        ↓
    PAPER JOURNAL
        ↓
    TELEGRAM

PAPER ONLY:
nessun ordine reale viene eseguito.
"""

from __future__ import annotations

from datetime import datetime, timezone

from commodities.universe import (
    enabled_commodities,
    validate_universe,
)

from config import (
    PAPER_TRADING_ONLY,
    TELEGRAM_ENABLED,
)

from engine.gagarin import analyze_universe

from paper_trade_journal import (
    record_entries,
)

from telegram.bot import (
    format_report,
    send_telegram,
)


# ============================================================
# HEADER
# ============================================================

def _print_header():

    print()

    print("=" * 72)
    print("🚀 SOYUZ GAGARIN")
    print("=" * 72)

    print(
        "DATA → REGIME → STRUCTURE → SETUP → "
        "TRIGGER → RISK → SAFETY"
    )

    if PAPER_TRADING_ONLY:
        print("MODE: PAPER ONLY")
    else:
        print("MODE: UNSAFE CONFIGURATION")

    print(
        "UTC:",
        datetime.now(
            timezone.utc
        ).isoformat(),
    )

    print()


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================