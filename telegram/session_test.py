"""Telegram diagnostic: liquidity windows are informational, not scan blockers."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from engine.session_filter import instrument_window_open

ROME = ZoneInfo("Europe/Rome")

TEST_INSTRUMENTS = [
    ("Petrolio WTI", "WTI/USD"),
    ("Petrolio Brent", "BRENT/USD"),
    ("Oro", "XAU/USD"),
    ("Argento", "XAG/USD"),
    ("Rame", "COPPER/USD"),
    ("Grano", "WHEAT/USD"),
    ("Mais", "CORN/USD"),
    ("Soia", "SOYBEAN/USD"),
    ("EUR/USD", "EUR/USD"),
    ("GBP/USD", "GBP/USD"),
]


def session_test_text() -> str:
    now = datetime.now(ROME)
    lines = [
        "TEST SCANSIONE SENZA FILTRO ORARIO",
        f"Ora italiana: {now.strftime('%H:%M')}",
        "PAPER ONLY",
        "",
    ]
    for name, symbol in TEST_INSTRUMENTS:
        allowed = instrument_window_open(symbol, now)
        status = "SCANSIONE CONSENTITA" if allowed else "MERCATO CHIUSO"
        lines.append(f"{name}: {status} - {'nessun blocco intraday' if allowed else 'weekend/mercato chiuso'}")
    return "\n".join(lines)


def test_session_filter_smoke() -> None:
    """All instruments remain scannable at this intraday time."""
    moment = datetime(2026, 10, 28, 15, 45, tzinfo=ROME)
    assert instrument_window_open("WTI/USD", moment) is True
    assert instrument_window_open("XAU/USD", moment) is True
    assert instrument_window_open("WHEAT/USD", moment) is True
