# ============================================================
# SOYUZ GAGARIN v1.3
# DATA ENGINE + DIAGNOSTICS
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#   ↓
# SETUP
#   ↓
# TRIGGER
#   ↓
# RISK
#   ↓
# SAFETY
#   ↓
# GAGARIN
#
# Single data adapter:
# Twelve Data
#
# Nessun fallback parallelo in questa versione.
#
# v1.3
# - diagnostica completa errori Twelve Data
# - mantiene compatibilità con fetch_twelve_data()
# - errori salvati in state.metadata
# - distingue:
#     HTTP_ERROR
#     API_ERROR
#     NO_VALUES
#     INVALID_RESPONSE
#     INSUFFICIENT_CANDLES
#     INVALID_TIMESTAMP
#     INVALID_ATR
#     DATA_NOT_LIVE
# - non espone API key
# ============================================================

from datetime import datetime, timezone
from typing import Optional

import requests

from config import (
    TWELVE_DATA_API_KEY,
    LOOKBACK,
    TIMEOUT_SECONDS,
    LIVE_MAX_AGE_SECONDS,
)

from engine.state import SoyuzState


API_URL = "https://api.twelvedata.com/time_series"

BASE_INTERVAL = "5min"

BAR_SECONDS = 300

LIVE_BUFFER_SECONDS = 60

EFFECTIVE_LIVE_MAX_AGE = max(
    LIVE_MAX_AGE_SECONDS,
    BAR_SECONDS + LIVE_BUFFER_SECONDS,
)


# ============================================================
# TIME
# ============================================================


def _parse_time(value: str) -> Optional[datetime]:
    """
    Converte il timestamp Twelve Data in datetime UTC.
    """

    if not value:
        return None

    try:
        value = value.strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except (TypeError, ValueError):
        return None


# ============================================================
# ATR
# ============================================================


def _true_range(
    high: float,
    low: float,
    previous_close: Optional[float],
) -> float:

    if previous_close is None:
        return high - low

    return max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def _calculate_atr(
    candles: list[dict],
    period: int = 14,
) -> Optional[float]:
    """
    ATR semplice basato sugli ultimi `period` true ranges.
    """

    if len(candles) < period + 1:
        return None

    ranges = []

    start = max(
        1,
        len(candles) - period,
    )

    for i in range(start, len(candles)):

        current = candles[i]
        previous = candles[i - 1]

        tr = _true_range(
            current["high"],
            current["low"],
            previous["close"],
        )

        ranges.append(tr)

    if not ranges:
        return None

    return sum(ranges) / len(ranges)


# ============================================================
# CANDLE NORMALIZATION
# ============================================================


def _normalize_candle(row: dict) -> Optional[dict]:
    """
    Normalizza una candela Twelve Data.
    """

    try:

        timestamp = row.get("datetime")

        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])

        if high_price < low_price:
            return None

        if not (
            low_price <= open_price <= high_price