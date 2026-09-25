"""
SOYUZ GAGARIN — DATA FRESHNESS GATE v1.0

Scopo:
- verificare l'età dei dati
- distinguere LIVE / STALE / BLOCKED
- applicare limiti diversi per timeframe
- impedire che dati vecchi alimentino il trigger operativo

NON decide LONG/SHORT.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


# ============================================================
# CONFIGURAZIONE
# ============================================================

MAX_AGE_SECONDS = {
    "M1": 60,
    "M5": 120,
    "M15": 300,
    "M30": 600,
    "H1": 900,
    "H4": 3600,
}


# ============================================================
# RISULTATO
# ============================================================

@dataclass(frozen=True)
class FreshnessResult:
    status: str
    age_seconds: Optional[float]
    max_age_seconds: Optional[int]
    reason: str

    @property
    def usable(self) -> bool:
        return self.status == "FRESH"

    @property
    def blocked(self) -> bool:
        return self.status == "BLOCKED"

    @property
    def stale(self) -> bool:
        return self.status == "STALE"


# ============================================================
# UTILS
# ============================================================

def _now_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


def _normalize_timestamp(timestamp) -> Optional[float]:
    """
    Accetta:
    - Unix timestamp
    - datetime
    - None
    """

    if timestamp is None:
        return None

    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return timestamp.timestamp()

    try:
        return float(timestamp)
    except (TypeError, ValueError):
        return None


# ============================================================
# CORE
# ============================================================

def check_freshness(
    timestamp,
    timeframe: str,
    now_timestamp: Optional[float] = None,
) -> FreshnessResult:

    timeframe = str(timeframe).upper().strip()

    max_age = MAX_AGE_SECONDS.get(timeframe)

    if max_age is None:
        return FreshnessResult(
            status="BLOCKED",
            age_seconds=None,
            max_age_seconds=None,
            reason=f"UNKNOWN_TIMEFRAME:{timeframe}",
        )

    ts = _normalize_timestamp(timestamp)

    if ts is None:
        return FreshnessResult(
            status="BLOCKED",
            age_seconds=None,
            max_age_seconds=max_age,
            reason="MISSING_TIMESTAMP",
        )

    now = (
        float(now_timestamp)
        if now_timestamp is not None
        else _now_timestamp()
    )

    age = now - ts

    # --------------------------------------------------------
    # Timestamp futuro = problema del provider / clock
    # --------------------------------------------------------

    if age < -5:
        return FreshnessResult(
            status="BLOCKED",
            age_seconds=age,
            max_age_seconds=max_age,
            reason="TIMESTAMP_IN_FUTURE",
        )

    # --------------------------------------------------------
    # Dato troppo vecchio
    # --------------------------------------------------------

    if age > max_age:
        return FreshnessResult(
            status="STALE",
            age_seconds=age,
            max_age_seconds=max_age,
            reason="DATA_TOO_OLD",
        )

    # --------------------------------------------------------
    # Dato utilizzabile
    # --------------------------------------------------------

    return FreshnessResult(
        status="FRESH",
        age_seconds=max(0.0, age),
        max_age_seconds=max_age,
        reason="DATA_FRESH",
    )


# ============================================================
# OPERATIVE GATE
# ============================================================

def operational_data_gate(
    timestamp,
    timeframe: str,
    now_timestamp: Optional[float] = None,
) -> FreshnessResult:
    """
    Gate specifico per GAGARIN.

    Solo FRESH può alimentare:
    - trigger
    - entry
    - SL
    - TP
    - RR
    """

    result = check_freshness(
        timestamp=timestamp,
        timeframe=timeframe,
        now_timestamp=now_timestamp,
    )

    if result.status != "FRESH":
        return FreshnessResult(
            status="BLOCKED",
            age_seconds=result.age_seconds,
            max_age_seconds=result.max_age_seconds,
            reason=f"OPERATIONAL_DATA_BLOCKED:{result.reason}",
        )

    return result


# ============================================================
# FORMATTAZIONE TELEGRAM / LOG
# ============================================================

def format_freshness(result: FreshnessResult) -> str:

    age = (
        f"{result.age_seconds:.1f}s"
        if result.age_seconds is not None
        else "N/A"
    )

    max_age = (
        f"{result.max_age_seconds}s"
        if result.max_age_seconds is not None
        else "N/A"
    )

    if result.status == "FRESH":
        icon = "🟢"

    elif result.status == "STALE":
        icon = "🟠"

    else:
        icon = "🔴"

    return (
        f"{icon} DATA {result.status} | "
        f"AGE={age} | "
        f"MAX={max_age} | "
        f"{result.reason}"
    )


# ============================================================
# TEST RAPIDI
# ============================================================

if __name__ == "__main__":

    now = _now_timestamp()

    tests = [
        ("M5", now - 30),
        ("M5", now - 180),
        ("M15", now - 200),
        ("M15", now - 400),
        ("H1", now - 600),
        ("H1", now - 1200),
        ("H1", None),
    ]

    print("\nSOYUZ GAGARIN — DATA FRESHNESS TEST")
    print("=" * 60)

    for timeframe, timestamp in tests:

        result = operational_data_gate(
            timestamp=timestamp,
            timeframe=timeframe,
            now_timestamp=now,
        )

        print(
            f"{timeframe:>4} | "
            f"{format_freshness(result)}"
        )