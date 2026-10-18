"""Descriptive intraday-window statistics for Gagarin.

Public reproducible input: Yahoo Finance chart endpoint for continuous futures.
These are descriptive range/return statistics, NOT strategy backtests or signals.
All timestamps are converted from UTC to Europe/Rome with DST handled by zoneinfo.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from statistics import mean, median
from threading import Lock
from time import monotonic
from typing import Any
from zoneinfo import ZoneInfo

import requests

ROME = ZoneInfo("Europe/Rome")
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
PERIOD = "60d"
INTERVAL = "5m"
REQUEST_TIMEOUT = 8
CACHE_SECONDS = 30 * 60
HEADERS = {"User-Agent": "Mozilla/5.0 Gagarin-Intraday-Research/1.0"}

ASSETS = {
    "Oro": "GC=F",
    "Argento": "SI=F",
    "WTI": "CL=F",
    "Brent": "BZ=F",
}
WINDOWS = (
    ("08:00–11:00", 8 * 60, 11 * 60, 36),
    ("14:00–18:00", 14 * 60, 18 * 60, 48),
    ("15:30–18:00", 15 * 60 + 30, 18 * 60, 30),
)
MIN_BAR_COVERAGE = 0.80

_CACHE: dict[str, Any] = {"at": 0.0, "report": None}
_CACHE_LOCK = Lock()


def _fetch_asset(name: str, symbol: str) -> tuple[str, list[dict[str, float]], str | None]:
    url = YAHOO_BASE + requests.utils.quote(symbol, safe="=")
    try:
        response = requests.get(
            url,
            params={"range": PERIOD, "interval": INTERVAL, "events": "history"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        chart = payload.get("chart", {})
        if chart.get("error"):
            return name, [], str(chart["error"])
        results = chart.get("result") or []
        if not results:
            return name, [], "NESSUN DATO NELLA RISPOSTA YAHOO"
        result = results[0]
        timestamps = result.get("timestamp") or []
        quote_list = (result.get("indicators", {}).get("quote") or [{}])
        quote = quote_list[0] if quote_list else {}
        arrays = [quote.get(key) or [] for key in ("open", "high", "low", "close")]
        rows = []
        for index, stamp in enumerate(timestamps):
            if any(index >= len(arr) or arr[index] is None for arr in arrays):
                continue
            try:
                o, h, low, close = (float(arr[index]) for arr in arrays)
                if min(o, h, low, close) <= 0 or h < max(o, close) or low > min(o, close) or h < low:
                    continue
                rows.append({
                    "timestamp": float(stamp),
                    "open": o,
                    "high": h,
                    "low": low,
                    "close": close,
                })
            except (TypeError, ValueError):
                continue
        if not rows:
            return name, [], "CANDLE OHLC VALIDE NON DISPONIBILI"
        return name, rows, None
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        return name, [], f"{type(exc).__name__}: {str(exc)[:100]}"


def _window_samples(rows: list[dict[str, float]], start_minute: int, end_minute: int, expected_bars: int) -> list[dict[str, float]]:
    by_date: dict[str, list[tuple[datetime, dict[str, float]]]] = {}
    for row in rows:
        local = datetime.fromtimestamp(row["timestamp"], tz=timezone.utc).astimezone(ROME)
        minute = local.hour * 60 + local.minute
        if start_minute <= minute < end_minute:
            by_date.setdefault(local.date().isoformat(), []).append((local, row))

    samples = []
    minimum_bars = int(expected_bars * MIN_BAR_COVERAGE + 0.999999)
    for day_rows in by_date.values():
        day_rows.sort(key=lambda item: item[0])
        # De-duplicate repeated timestamps and reject partial windows, e.g. market holidays.
        unique = {}
        for local, row in day_rows:
            unique[local] = row
        bars = [unique[key] for key in sorted(unique)]
        if len(bars) < minimum_bars:
            continue
        first_open = bars[0]["open"]
        last_close = bars[-1]["close"]
        if first_open <= 0:
            continue
        high = max(row["high"] for row in bars)
        low = min(row["low"] for row in bars)
        samples.append({
            "range_pct": (high - low) / first_open * 100.0,
            "close_open_pct": (last_close / first_open - 1.0) * 100.0,
        })
    return samples


def calculate_window_statistics(rows: list[dict[str, float]]) -> list[dict[str, Any]]:
    """Calculate descriptive metrics for complete-ish local-time windows."""
    output = []
    for label, start, end, expected in WINDOWS:
        samples = _window_samples(rows, start, end, expected)
        if not samples:
            output.append({
                "window": label, "n": 0, "mean_range_pct": None,
                "median_range_pct": None, "mean_close_open_pct": None,
                "median_close_open_pct": None,
            })
            continue
        ranges = [item["range_pct"] for item in samples]
        returns = [item["close_open_pct"] for item in samples]
        output.append({
            "window": label,
            "n": len(samples),
            "mean_range_pct": mean(ranges),
            "median_range_pct": median(ranges),
            "mean_close_open_pct": mean(returns),
            "median_close_open_pct": median(returns),
        })
    return output


def collect_intraday_window_statistics(force_refresh: bool = False) -> dict[str, Any]:
    """Fetch up to 60 days of public 5-minute futures data and summarize windows.

    A 30-minute cache protects Yahoo from repeated requests. Data failure for one
    asset does not suppress available results for the others.
    """
    now = monotonic()
    with _CACHE_LOCK:
        if not force_refresh and _CACHE["report"] is not None and now - _CACHE["at"] < CACHE_SECONDS:
            return _CACHE["report"]

    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_fetch_asset, name, symbol): (name, symbol)
            for name, symbol in ASSETS.items()
        }
        for future in as_completed(futures):
            name, symbol = futures[future]
            try:
                asset, rows, error = future.result()
            except Exception as exc:  # defensive isolation per asset
                asset, rows, error = name, [], f"{type(exc).__name__}: {str(exc)[:100]}"
            if error:
                results[asset] = {"symbol": symbol, "error": error, "windows": []}
            else:
                results[asset] = {
                    "symbol": symbol,
                    "bars": len(rows),
                    "first_utc": datetime.fromtimestamp(rows[0]["timestamp"], tz=timezone.utc).isoformat(),
                    "last_utc": datetime.fromtimestamp(rows[-1]["timestamp"], tz=timezone.utc).isoformat(),
                    "windows": calculate_window_statistics(rows),
                }

    report = {
        "source": "Yahoo Finance chart endpoint; continuous futures GC=F, SI=F, CL=F, BZ=F",
        "interval": INTERVAL,
        "period_requested": PERIOD,
        "timezone": "Europe/Rome",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "assets": results,
    }
    with _CACHE_LOCK:
        _CACHE["at"] = monotonic()
        _CACHE["report"] = report
    return report


def format_intraday_window_report(report: dict[str, Any] | None = None) -> str:
    """Telegram-safe Italian summary; never describes range as profitability."""
    try:
        report = report or collect_intraday_window_statistics()
        lines = [
            "⏰ FASCE ORARIE — ANALISI STATISTICA",
            "━━━━━━━━━━━━━━━━━━━━",
            "🧪 RICERCA DESCRITTIVA | PAPER ONLY",
            "Fonte: Yahoo Finance futures continui, barre 5m, periodo richiesto ultime 60 giornate.",
            "Orari Europe/Rome; cambio ora legale gestito automaticamente.",
            "",
        ]
        any_data = False
        for asset in ("Oro", "Argento", "WTI", "Brent"):
            item = (report.get("assets") or {}).get(asset, {})
            lines.append(f"▸ {asset} ({item.get('symbol', ASSETS[asset])})")
            if item.get("error"):
                lines.append(f"  Dati non disponibili: {item['error']}")
                lines.append("")
                continue
            if not item.get("windows"):
                lines.append("  Nessuna statistica disponibile.")
                lines.append("")
                continue
            any_data = True
            for stat in item["windows"]:
                if stat.get("n", 0) == 0:
                    lines.append(f"  {stat['window']}: campione insufficiente")
                    continue
                lines.append(
                    f"  {stat['window']} | n={stat['n']} | "
                    f"range med {stat['median_range_pct']:.3f}% "
                    f"(media {stat['mean_range_pct']:.3f}%) | "
                    f"close-open medio {stat['mean_close_open_pct']:+.3f}%"
                )
            lines.append("")
        if not any_data:
            lines.extend(["Nessun campione ottenuto dai provider; riprovare più tardi.", ""])
        lines.extend([
            "METRICHE: range=(massimo high−minimo low)/primo open; close-open=variazione descrittiva della finestra.",
            "Non è un backtest: nessuna redditività netta, win rate, expectancy, profit factor o drawdown.",
            "Dati futures continui Yahoo, non quotazioni CFD/bid-ask Trading 212; spread, commissioni e slippage esclusi.",
            "Non modifica segnali, ranking, soglie, rischio o ordini.",
        ])
        return "\n".join(lines)
    except Exception as exc:
        return (
            "⏰ FASCE ORARIE — ANALISI STATISTICA\n"
            "Dati non disponibili in questa esecuzione.\n"
            f"Dettaglio: {type(exc).__name__}: {str(exc)[:120]}\n"
            "Nessuna modifica alla strategia; PAPER/DEMO."
        )

def format_intraday_window_summary(report: dict[str, Any] | None = None) -> str:
    """Short summary suitable for appending to existing Telegram trading reports."""
    try:
        report = report or collect_intraday_window_statistics()
        lines = [
            "⏰ FASCE ORARIE — RANGE MEDIANO",
            "Fonte Yahoo futures M5 | ultime 60g richieste | Europe/Rome",
        ]
        for asset in ("Oro", "Argento", "WTI", "Brent"):
            item = (report.get("assets") or {}).get(asset, {})
            if item.get("error") or not item.get("windows"):
                lines.append(f"{asset}: dati non disponibili")
                continue
            values = []
            for stat in item["windows"]:
                if stat.get("n", 0) == 0:
                    values.append(f"{stat['window']} N/D")
                else:
                    values.append(f"{stat['window']} {stat['median_range_pct']:.3f}% (n={stat['n']})")
            lines.append(f"{asset}: " + " | ".join(values))
        lines.extend([
            "Range = movimento osservato, NON redditività. Costi e spread esclusi.",
            "Dettaglio: /fasceorario. Nessuna modifica a segnali o rischio.",
        ])
        return "\n".join(lines)
    except Exception as exc:
        return f"⏰ FASCE ORARIE: dati non disponibili ({type(exc).__name__}). Strategia invariata."
