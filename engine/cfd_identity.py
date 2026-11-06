"""Strict identity boundary for a future official Trading 212 CFD channel.

This module does not fetch quotes, map broker tickers, calculate trade levels,
or place orders. It only allows a quote series to be associated with a
Trading 212 CFD instrument after the exact broker symbol, contract, expiry,
and quote currency have been verified from the Trading 212 app.

Yahoo futures and BiQuote reference data are intentionally rejected here.
PAPER ONLY.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
import json
import math


TRADING212_BROKER = "TRADING212"
TRADING212_CFD_PROVIDER = "TRADING212_CFD"
TRADING212_APP_SCREEN = "TRADING_212_APP_SCREEN"

# Logical Gagarin universe only. These are not broker tickers.
GAGARIN_CFD_LOGICAL_SYMBOLS = frozenset(
    {
        "XAU/USD",
        "XAG/USD",
        "COPPER/USD",
        "WTI/USD",
        "BRENT/USD",
        "WHEAT/USD",
        "CORN/USD",
        "SOYBEAN/USD",
    }
)


def _required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} is required and must not contain outer whitespace")
    return value


def _aware_utc_timestamp(value: str, field: str) -> datetime:
    text = _required_text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset")
    return parsed


@dataclass(frozen=True)
class CFDInstrumentIdentity:
    """Verified identity copied from the Trading 212 CFD instrument screen."""

    broker: str
    market_type: str
    logical_symbol: str
    broker_symbol: str
    contract: str
    expiry: str
    currency: str
    verification_source: str
    verified_at_utc: str

    def validate(self) -> "CFDInstrumentIdentity":
        if self.broker != TRADING212_BROKER:
            raise ValueError("Only the Trading 212 broker identity is accepted")
        if self.market_type != "CFD":
            raise ValueError("Instrument market_type must be CFD")
        if self.logical_symbol not in GAGARIN_CFD_LOGICAL_SYMBOLS:
            raise ValueError("Instrument is outside the eight-commodity Gagarin CFD universe")
        _required_text(self.broker_symbol, "broker_symbol")
        _required_text(self.contract, "contract")
        expiry = _required_text(self.expiry, "expiry")
        try:
            date.fromisoformat(expiry)
        except ValueError as exc:
            raise ValueError("expiry must be the verified contract date in YYYY-MM-DD form") from exc
        currency = _required_text(self.currency, "currency")
        if len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
            raise ValueError("currency must be a three-letter uppercase ISO code")
        if self.verification_source != TRADING212_APP_SCREEN:
            raise ValueError("Identity must be verified from the Trading 212 app instrument screen")
        _aware_utc_timestamp(self.verified_at_utc, "verified_at_utc")
        return self


@dataclass(frozen=True)
class CFDQuoteSeriesIdentity:
    """Provenance attached to one homogeneous broker CFD candle series."""

    provider: str
    broker: str
    market_type: str
    broker_symbol: str
    contract: str
    expiry: str
    currency: str
    timeframe: str
    series_id: str

    def validate(self) -> "CFDQuoteSeriesIdentity":
        if self.provider != TRADING212_CFD_PROVIDER:
            raise ValueError("Quote series must come from the official Trading 212 CFD feed")
        if self.broker != TRADING212_BROKER or self.market_type != "CFD":
            raise ValueError("Quote series broker/market identity is not Trading 212 CFD")
        for field in ("broker_symbol", "contract", "expiry", "currency", "timeframe", "series_id"):
            _required_text(getattr(self, field), field)
        try:
            date.fromisoformat(self.expiry)
        except ValueError as exc:
            raise ValueError("quote-series expiry must use YYYY-MM-DD") from exc
        if len(self.currency) != 3 or not self.currency.isalpha() or self.currency != self.currency.upper():
            raise ValueError("quote-series currency must be a three-letter uppercase ISO code")
        return self


def validate_same_cfd_series(
    instrument: CFDInstrumentIdentity,
    series: CFDQuoteSeriesIdentity,
) -> None:
    """Raise unless every identity field matches the verified instrument."""
    instrument.validate()
    series.validate()
    fields = ("broker_symbol", "contract", "expiry", "currency")
    mismatches = [
        field for field in fields
        if getattr(instrument, field) != getattr(series, field)
    ]
    if mismatches:
        raise ValueError("CFD quote series identity mismatch: " + ", ".join(mismatches))


def build_cfd_signal_id(
    instrument: CFDInstrumentIdentity,
    series: CFDQuoteSeriesIdentity,
    *,
    direction: str,
    candle_timestamp: str,
    entry: float,
    stop_loss: float,
    take_profits: tuple[float, ...],
) -> str:
    """Create a namespaced CFD signal ID only after exact series validation.

    This is identity generation only; it does not calculate or authorize a
    signal. Levels must already have been computed from the same CFD series.
    """
    validate_same_cfd_series(instrument, series)
    side = _required_text(direction, "direction").upper()
    if side not in {"LONG", "SHORT"}:
        raise ValueError("direction must be LONG or SHORT")
    bar_time = _aware_utc_timestamp(candle_timestamp, "candle_timestamp")

    levels = (entry, stop_loss, *tuple(take_profits))
    if not take_profits:
        raise ValueError("At least one take-profit level is required")
    normalized_levels = []
    for value in levels:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Signal levels must be finite positive numbers") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError("Signal levels must be finite positive numbers")
        normalized_levels.append(format(number, ".12g"))

    payload = {
        "broker": instrument.broker,
        "market_type": instrument.market_type,
        "logical_symbol": instrument.logical_symbol,
        "broker_symbol": instrument.broker_symbol,
        "contract": instrument.contract,
        "expiry": instrument.expiry,
        "currency": instrument.currency,
        "provider": series.provider,
        "series_id": series.series_id,
        "timeframe": series.timeframe,
        "candle_timestamp": bar_time.astimezone().isoformat(),
        "direction": side,
        "levels": normalized_levels,
    }
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return "T212CFD-" + digest
