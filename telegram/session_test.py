"""Test del filtro di sessione. PAPER only."""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from engine.session_filter import session_allowed, filter_order

ROME = ZoneInfo("Europe/Rome")

TEST_INSTRUMENTS = [
    "Petrolio WTI",
    "Petrolio Brent",
    "Oro",
    "DAX",
    "SPY",
    "QQQ",
    "EURUSD",
]

def session_test_text() -> str:
    now = datetime.now(ROME)
    lines = [
        "TEST FILTRO SESSIONE",
        f"Ora italiana: {now.strftime('%H:%M')}",
        "PAPER ONLY",
        "",
    ]
    for name in TEST_INSTRUMENTS:
        check = session_allowed(name, now)
        status = "OK" if check["allowed"] else "BLOCCATO"
        size = "100%" if check["size_factor"] == 1.0 else f"{int(check['size_factor']*100)}%" if check["size_factor"] > 0 else "0%"
        lines.append(f"{name}: {status} ({size}) - {check['reason']}")
    return "\n".join(lines)
