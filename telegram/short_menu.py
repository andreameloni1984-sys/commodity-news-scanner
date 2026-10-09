"""Menu Telegram corto. PAPER only. Nessun ordine."""

from __future__ import annotations

import json
from pathlib import Path

PAPER = Path("data/paper_open.json")
DAY = Path("data/day_trading_filter.json")


def menu_text() -> str:
    return "GAGARIN\n1 Commodity\n2 Day\n3 Stato"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def commodity_text(paper: dict | None = None) -> str:
    paper = _load(PAPER) if paper is None else paper
    position = paper.get("position") or {}
    status = str(position.get("status", "")).upper()
    if status != "OPEN":
        return "COMMODITY\nNiente"
    symbol = position.get("symbol", "?")
    direction = position.get("direction", "?")
    entry = position.get("entry", "?")
    stop = position.get("stop", "?")
    tp1 = position.get("tp1", "?")
    tp2 = position.get("tp2", "?")
    return (
        "COMMODITY\n"
        f"{symbol} {direction}\n"
        f"{entry}\n"
        f"stop {stop}\n"
        f"esci a {tp1} e {tp2}"
    )


def day_text(report: dict | None = None) -> str:
    report = _load(DAY) if report is None else report
    allowed = report.get("allowed") or []
    if not allowed:
        return "DAY\nNiente"
    rows = {row.get("symbol"): row for row in report.get("rows", [])}
    lines = ["DAY"]
    for symbol in allowed:
        row = rows.get(symbol, {})
        lines.append(f"{symbol} {row.get('direction', '')}".strip())
        lines.append("stop: range")
        lines.append("esci: VWAP")
    return "\n".join(lines)


def stato_text(paper: dict | None = None, report: dict | None = None) -> str:
    paper = _load(PAPER) if paper is None else paper
    report = _load(DAY) if report is None else report
    position = paper.get("position") or {}
    lines = ["Aperti"]
    if str(position.get("status", "")).upper() == "OPEN":
        lines.append(f"{position.get('symbol', '?')} {str(position.get('direction', '')).lower()}")
    else:
        lines.append("Commodity: nessuno")
    allowed = report.get("allowed") or []
    lines.append("Day: " + (", ".join(allowed) if allowed else "nessuno"))
    return "\n".join(lines)
