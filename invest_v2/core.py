"""Fail-closed equity/ETF BUY research signals, independent of legacy engines."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from re import fullmatch
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Signal:
    symbol: str
    asset_class: str
    account: str
    side: str
    quote_price: float
    quote_timestamp: datetime
    entry: float
    stop_loss: float
    take_profit: float
    source_url: str
    rationale: str
    event_id: str


def validate(signal: Signal, *, now: datetime | None = None, max_age_seconds: int = 60) -> tuple[bool, tuple[str, ...]]:
    now = now or datetime.now(timezone.utc)
    problems: list[str] = []
    if not isinstance(signal.symbol, str) or not fullmatch(r"[A-Z0-9][A-Z0-9.\\-]{0,19}", signal.symbol):
        problems.append("missing_symbol")
    if signal.asset_class not in ("STOCK", "ETF"):
        problems.append("not_stock_or_etf")
    if signal.account != "INVEST_DEMO":
        problems.append("not_invest_demo")
    if signal.side != "BUY":
        problems.append("not_buy")
    for field in ("quote_price", "entry", "stop_loss", "take_profit"):
        value = getattr(signal, field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value <= 0:
            problems.append("invalid_" + field)
    if not isinstance(signal.quote_timestamp, datetime) or not isinstance(now, datetime) or signal.quote_timestamp.tzinfo is None or now.tzinfo is None:
        problems.append("missing_quote_timezone")
    else:
        age = (now - signal.quote_timestamp).total_seconds()
        if not 0 <= age <= max_age_seconds:
            problems.append("stale_or_future_quote")
    if all(isinstance(getattr(signal, k), (int, float)) and isfinite(getattr(signal, k)) for k in ("stop_loss", "entry", "take_profit")):
        if not signal.stop_loss < signal.entry < signal.take_profit:
            problems.append("invalid_buy_levels")
    parsed_source = urlsplit(signal.source_url) if isinstance(signal.source_url, str) else urlsplit("")
    if parsed_source.scheme != "https" or not parsed_source.hostname or parsed_source.username or parsed_source.password:
        problems.append("invalid_source_url")
    if not isinstance(signal.rationale, str) or not signal.rationale.strip():
        problems.append("missing_rationale")
    if not isinstance(signal.event_id, str) or not signal.event_id.strip():
        problems.append("missing_event_id")
    return not problems, tuple(problems)


def format_telegram(signal: Signal, *, now: datetime | None = None) -> str | None:
    valid, _ = validate(signal, now=now)
    if not valid:
        return None
    return (f"🟢 INVEST DEMO — PROPOSTA BUY (PAPER ONLY)\n"
            f"{signal.symbol} ({signal.asset_class}) | BUY\n"
            f"Prezzo: {signal.quote_price:.4f} | Entry: {signal.entry:.4f}\n"
            f"SL: {signal.stop_loss:.4f} | TP: {signal.take_profit:.4f}\n"
            f"Quotazione UTC: {signal.quote_timestamp.isoformat()}\n"
            f"Motivo: {signal.rationale}\nFonte: {signal.source_url}\n"
            f"Evento: {signal.event_id}\nNESSUN ORDINE INVIATO")
