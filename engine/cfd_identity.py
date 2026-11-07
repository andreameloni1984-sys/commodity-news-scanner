"""Strict identity boundary for a future official Trading 212 CFD channel.

This module does not fetch quotes, authenticate a data feed, map broker tickers,
calculate trade levels, or place orders. It validates a manually reviewed
instrument allowlist and checks claimed quote-series metadata. A provider label
is not proof of feed origin; a trusted official adapter is still required.

Yahoo futures and BiQuote reference data are intentionally rejected here.
PAPER ONLY.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse


TRADING212_BROKER = "TRADING212"
TRADING212_CFD_PROVIDER = "TRADING212_CFD"
TRADING212_APP_SCREEN = "TRADING_212_APP_SCREEN"
TRADING212_OFFICIAL_CATALOG = "TRADING212_OFFICIAL_CATALOG"

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


def _verified_expiry(value: str, field: str) -> str:
    text = _required_text(value, field)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError(f"{field} must use YYYY-MM-DD")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid calendar date") from exc
    return text


def _validate_contract_expiry(contract_type: str, value: str | None, field: str) -> None:
    """Require an explicit spot/no-expiry or expiring-future identity."""
    kind = _required_text(contract_type, "contract_type")
    if kind == "SPOT":
        if value is not None:
            raise ValueError(f"{field} must be None for SPOT")
        return
    if kind != "EXPIRING_FUTURE":
        raise ValueError("contract_type must be SPOT or EXPIRING_FUTURE")
    _verified_expiry(value, field)


def _aware_utc_timestamp(value: str, field: str) -> datetime:
    text = _required_text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _validate_verification_evidence(source: str, reference: str) -> None:
    """Accept app-screen evidence or a canonical official Trading 212 CFD product page."""
    selected_source = _required_text(source, "verification_source")
    selected_reference = _required_text(reference, "verification_reference")
    if selected_source == TRADING212_APP_SCREEN:
        return
    if selected_source != TRADING212_OFFICIAL_CATALOG:
        raise ValueError(
            "Identity evidence must be a Trading 212 app screen or official CFD catalogue page"
        )

    parsed = urlparse(selected_reference)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() not in {"trading212.com", "www.trading212.com"}
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(
            r"/(?:[a-z]{2}/)?trading-instruments/cfd/[A-Za-z0-9][A-Za-z0-9._-]*",
            parsed.path,
        )
    ):
        raise ValueError(
            "Official catalogue evidence must be a canonical Trading 212 CFD product URL"
        )


def _positive_level(value: float, field: str) -> str:
    # bool is a subclass of int in Python; float(True) == 1.0 would otherwise
    # let a malformed flag masquerade as a valid CFD price level.
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite positive number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be a finite positive number")
    return format(number, ".12g")


@dataclass(frozen=True)
class CFDInstrumentIdentity:
    """Candidate screen-derived identity; registry membership is required for approval."""

    broker: str
    market_type: str
    logical_symbol: str
    broker_symbol: str
    contract: str
    contract_type: str
    expiry: str | None
    currency: str
    verification_source: str
    verification_reference: str
    verification_evidence_sha256: str
    verified_at_utc: str

    def validate(self) -> "CFDInstrumentIdentity":
        """Validate field shape; registry membership is the approval boundary."""
        if self.broker != TRADING212_BROKER:
            raise ValueError("Only the Trading 212 broker identity is accepted")
        if self.market_type != "CFD":
            raise ValueError("Instrument market_type must be CFD")
        if self.logical_symbol not in GAGARIN_CFD_LOGICAL_SYMBOLS:
            raise ValueError("Instrument is outside the eight-commodity Gagarin CFD universe")
        _required_text(self.broker_symbol, "broker_symbol")
        _required_text(self.contract, "contract")
        _validate_contract_expiry(self.contract_type, self.expiry, "expiry")
        currency = _required_text(self.currency, "currency")
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
            raise ValueError("currency must be a three-letter uppercase ISO code")
        _validate_verification_evidence(self.verification_source, self.verification_reference)
        evidence_hash = _required_text(
            self.verification_evidence_sha256, "verification_evidence_sha256"
        )
        if not re.fullmatch(r"[0-9a-f]{64}", evidence_hash):
            raise ValueError(
                "verification_evidence_sha256 must be a lowercase SHA-256 hex digest"
            )
        _aware_utc_timestamp(self.verified_at_utc, "verified_at_utc")
        return self


@dataclass(frozen=True)
class CFDInstrumentRegistry:
    """Allowlist of contract identities manually reviewed against app screenshots.

    A syntactically valid identity is not approved by itself. Only an exact
    record in this registry can be bound to a quote series or signal ID.
    """

    records: tuple[CFDInstrumentIdentity, ...] = ()

    def validate(self) -> "CFDInstrumentRegistry":
        if not isinstance(self.records, tuple):
            raise ValueError("Registry records must be an immutable tuple")
        seen = set()
        for record in self.records:
            if not isinstance(record, CFDInstrumentIdentity):
                raise ValueError("Registry contains an invalid instrument record")
            record.validate()
            key = (
                record.logical_symbol,
                record.broker_symbol,
                record.contract,
                record.contract_type,
                record.expiry,
                record.currency,
            )
            if key in seen:
                raise ValueError("Registry contains a duplicate CFD contract identity")
            seen.add(key)
        return self

    def require(self, instrument: CFDInstrumentIdentity) -> None:
        self.validate()
        instrument.validate()
        if instrument not in self.records:
            raise ValueError(
                "Instrument identity is not present in the reviewed Trading 212 CFD registry"
            )


def load_verified_instrument_registry(
    path: str | Path | None = None,
) -> CFDInstrumentRegistry:
    """Load the manually reviewed contract allowlist; an empty registry blocks all CFD use."""
    registry_path = (
        Path(path)
        if path is not None
        else Path(__file__).with_name("trading212_cfd_contract_registry.json")
    )
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(
            "Reviewed Trading 212 CFD contract registry is unavailable; CFD use is blocked"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported Trading 212 CFD contract registry schema")
    raw_records = payload.get("instruments")
    if not isinstance(raw_records, list):
        raise ValueError("Trading 212 CFD registry instruments must be a list")
    records = []
    for item in raw_records:
        if not isinstance(item, dict):
            raise ValueError("Trading 212 CFD registry contains a malformed record")
        try:
            records.append(CFDInstrumentIdentity(**item))
        except TypeError as exc:
            raise ValueError("Trading 212 CFD registry record has invalid fields") from exc
    return CFDInstrumentRegistry(records=tuple(records)).validate()


@dataclass(frozen=True)
class CFDQuoteSeriesIdentity:
    """Claimed series metadata; this class does not authenticate the feed source."""

    provider: str
    broker: str
    market_type: str
    logical_symbol: str
    broker_symbol: str
    contract: str
    contract_type: str
    expiry: str | None
    currency: str
    timeframe: str
    series_id: str

    def validate(self) -> "CFDQuoteSeriesIdentity":
        if self.provider != TRADING212_CFD_PROVIDER:
            raise ValueError("Quote series provider label must be TRADING212_CFD; feed origin is not authenticated here")
        if self.broker != TRADING212_BROKER or self.market_type != "CFD":
            raise ValueError("Quote series broker/market identity is not Trading 212 CFD")
        if self.logical_symbol not in GAGARIN_CFD_LOGICAL_SYMBOLS:
            raise ValueError("Quote series logical_symbol is outside the eight-commodity Gagarin CFD universe")
        for field in ("logical_symbol", "broker_symbol", "contract", "contract_type", "timeframe", "series_id"):
            _required_text(getattr(self, field), field)
        _validate_contract_expiry(self.contract_type, self.expiry, "quote-series expiry")
        currency = _required_text(self.currency, "quote-series currency")
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
            raise ValueError("quote-series currency must be a three-letter uppercase ISO code")
        return self


@dataclass(frozen=True)
class CFDSignalLevels:
    """Pre-calculated levels with explicit provenance to one CFD candle series."""

    source_series_id: str
    entry: float
    stop_loss: float
    take_profits: tuple[float, ...]

    def validate_for(self, series: CFDQuoteSeriesIdentity) -> tuple[str, ...]:
        source_id = _required_text(self.source_series_id, "source_series_id")
        if source_id != series.series_id:
            raise ValueError("CFD levels were not calculated from the matched Trading 212 CFD series")
        if not self.take_profits:
            raise ValueError("At least one take-profit level is required")
        values = [
            _positive_level(self.entry, "entry"),
            _positive_level(self.stop_loss, "stop_loss"),
        ]
        values.extend(_positive_level(value, "take_profit") for value in self.take_profits)
        return tuple(values)


def validate_same_cfd_series(
    instrument: CFDInstrumentIdentity,
    series: CFDQuoteSeriesIdentity,
    *,
    registry: CFDInstrumentRegistry | None = None,
) -> None:
    """Require a registry-approved instrument and matching claimed series metadata."""
    active_registry = (
        registry if registry is not None else load_verified_instrument_registry()
    )
    active_registry.require(instrument)
    series.validate()
    fields = ("logical_symbol", "broker_symbol", "contract", "contract_type", "expiry", "currency")
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
    levels: CFDSignalLevels,
    registry: CFDInstrumentRegistry | None = None,
) -> str:
    """Create a namespaced CFD ID after exact series and levels provenance checks.

    Identity generation only: this function does not authenticate the feed,
    calculate or authorize a signal. A trusted adapter must supply levels from
    the matched official CFD series.
    """
    validate_same_cfd_series(instrument, series, registry=registry)
    side = _required_text(direction, "direction").upper()
    if side not in {"LONG", "SHORT"}:
        raise ValueError("direction must be LONG or SHORT")
    bar_time = _aware_utc_timestamp(candle_timestamp, "candle_timestamp")
    normalized_levels = levels.validate_for(series)

    payload = {
        "broker": instrument.broker,
        "market_type": instrument.market_type,
        "logical_symbol": instrument.logical_symbol,
        "broker_symbol": instrument.broker_symbol,
        "contract": instrument.contract,
        "contract_type": instrument.contract_type,
        "expiry": instrument.expiry,
        "currency": instrument.currency,
        "verification_source": instrument.verification_source,
        "verification_reference": instrument.verification_reference,
        "verification_evidence_sha256": instrument.verification_evidence_sha256,
        "verified_at_utc": instrument.verified_at_utc,
        "provider": series.provider,
        "series_id": series.series_id,
        "timeframe": series.timeframe,
        "candle_timestamp": bar_time.isoformat(),
        "direction": side,
        "levels": normalized_levels,
    }
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return "T212CFD-" + digest
