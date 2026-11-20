"""Read-only diagnostics for the same news intake and pricing rules as the worker."""
from dataclasses import asdict
from datetime import timedelta
import json
from xml.etree.ElementTree import ParseError

import exchange_calendars

from .engine import evaluate
from .macro import BLS_RELEASES, bls_release, compare, gdp_reading, rate_readings

EXPECTED_ERRORS = (OSError, ValueError, RuntimeError, KeyError, TypeError, ParseError)


def error_label(exc):
    if hasattr(exc, "code"):
        return f"HTTP {exc.code}"
    if isinstance(exc, RuntimeError):
        return str(exc)
    return type(exc).__name__


def expectations_from(path):
    if not path:
        return []
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, list):
        raise ValueError("Le attese macro devono essere un array JSON")
    return source


def macro_releases(fetch, user_agent, sources, expectations):
    releases, statuses = [], {}

    def add(title, url, published, readings):
        releases.extend({"title": title, "source": url, "published": published.isoformat(),
                         **compare(item, published, expectations)} for item in readings)

    for name, url in BLS_RELEASES.items():
        try:
            published, readings = bls_release(fetch(url, user_agent), cpi=name == "BLS CPI")
            add(name, url, published, readings)
            statuses[name] = "letto"
        except EXPECTED_ERRORS as exc:
            statuses[name] = str(exc) if isinstance(exc, ValueError) else error_label(exc)
    for title, url, published, summary in sources.get("BEA", []):
        data = gdp_reading(title, summary)
        if data:
            add(title, url, published, [data])
    for title, url, published, _ in sources.get("Federal Reserve", []):
        if title.strip().lower() != "federal reserve issues fomc statement":
            continue
        try:
            add(title, url, published, rate_readings(fetch(url, user_agent), published))
            statuses["FOMC target range"] = "letto"
        except EXPECTED_ERRORS as exc:
            statuses["FOMC target range"] = error_label(exc)
        break
    return releases, statuses


def check_market(market, universe, now, opened):
    # The liquid benchmark is a connectivity probe, independent of catalyst matching.
    symbol = "SPY" if "SPY" in universe else min(universe, default="SPY")
    end = now
    is_open = opened is not None
    if not is_open:
        calendar = exchange_calendars.get_calendar("XNYS")
        minute = now.replace(second=0, microsecond=0)
        session = calendar.minute_to_past_session(minute)
        opened = calendar.session_open(session).to_pydatetime()
        end = calendar.session_close(session).to_pydatetime()
    bars = market.bars([symbol], start=max(opened, end - timedelta(minutes=30)), end=end).get(symbol, [])
    latest = max((b.closed_at for b in bars if b.closed_at <= end), default=None)
    age = (now - latest).total_seconds() if latest else None
    return {"ticker_sonda": symbol, "feed": market.feed, "ultima_barra": latest.isoformat() if latest else None,
            "eta_secondi": age, "stato": "barre assenti" if age is None else
            "fresco" if is_open and age <= 120 else "storico / scaduto"}


def build_rows(reviewed, *, universe, market, opened, clock):
    rows, due = [], {}
    for event, reason in reviewed:
        row = asdict(event)
        for field in ("published", "detected"):
            row[field] = row[field].isoformat()
        row.update(selected=None if universe is None else False, exclusion=reason)
        rows.append(row)
        if reason:
            continue
        if clock() - event.published > timedelta(hours=1):
            row["exclusion"] = "pubblicazione oltre 60 minuti"
        elif universe is None:
            row["exclusion"] = "catalogo INVEST Demo non verificabile"
        elif event.symbol not in universe:
            row["exclusion"] = "ticker non presente nel catalogo INVEST Demo compatibile"
        elif opened is None:
            row.update(selected=True, exclusion="seduta XNYS chiusa")
        elif market is None:
            row.update(selected=True, exclusion="Alpaca non verificabile")
        else:
            row["selected"] = True
            due.setdefault(event.symbol, []).append((event, row))
    ranked = sorted(due, key=lambda symbol: (-max(event.impact for event, _ in due[symbol]), symbol))
    requested = ranked[:12]
    series = {}
    error = None
    if ranked:
        try:
            series = market.bars(requested, start=opened, end=clock())
        except EXPECTED_ERRORS as exc:
            error = "Alpaca: " + error_label(exc)
    for symbol in ranked:
        for event, row in due[symbol]:
            if symbol not in requested:
                row["exclusion"] = "oltre limite di 12 ticker per ciclo"
                continue
            if error:
                row["exclusion"] = error
                continue
            signal, reason = evaluate(event, series.get(symbol, []), clock())
            row.update(exclusion=reason, signal=signal)
    return rows
