"""
SOYUZ GAGARIN — DAILY FORECAST ENGINE

Produces the single morning market forecast shown in Telegram.

Evidence hierarchy:
1. Context-matched historical observations, when available.
2. Existing horizon validation samples from the long-term forecast file.
3. Current market context (structure/regime/news/fundamental metadata).

This module NEVER treats heuristic scores as calibrated probabilities.
It NEVER places orders. PAPER ONLY.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
FORECAST_FILE = ROOT / "commodities_long_term_forecasts.json"
ANALOG_FILE = ROOT / "historical_analog_dataset.json"

MIN_SAMPLES = 20


def _load(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _direction(value: Any) -> str:
    value = str(value or "").strip().upper()
    return value if value in {"LONG", "SHORT"} else "NONE"


def _forecast_map() -> dict[str, dict]:
    raw = _load(FORECAST_FILE, [])
    if not isinstance(raw, list):
        return {}
    result: dict[str, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        old = result.get(name)
        if old is None or str(item.get("forecast_date", "")) > str(old.get("forecast_date", "")):
            result[name] = item
    return result


def _context_direction(state: Any, forecast: dict | None) -> str:
    for attr in ("setup_direction", "structure_direction", "mtf_direction"):
        value = _direction(getattr(state, attr, "NONE"))
        if value != "NONE":
            return value

    horizons = (forecast or {}).get("horizons", {})
    votes = {"LONG": 0.0, "SHORT": 0.0}
    for horizon in ("30", "90", "180"):
        item = horizons.get(horizon, {})
        value = _direction(item.get("direction"))
        confidence = _num(item.get("confidence"), 0.0) or 0.0
        if value in votes:
            votes[value] += max(1.0, confidence)
    return max(votes, key=votes.get) if max(votes.values()) > 0 else "NONE"


def _historical_validation(forecast: dict | None, direction: str) -> dict:
    """Use only already-recorded validation samples; never invent observations."""
    if not forecast or direction not in {"LONG", "SHORT"}:
        return {"samples": 0, "hit_rates": [], "median_hit_rate": None, "horizons": []}

    horizons = forecast.get("horizons", {})
    samples = []
    hit_rates = []
    valid_horizons = []

    for horizon in ("30", "90", "180"):
        item = horizons.get(horizon, {})
        n = _num(item.get("historical_samples"), 0) or 0
        hit = _num(item.get("historical_hit_rate"))
        if n >= MIN_SAMPLES and hit is not None:
            samples.append(int(n))
            hit_rates.append(float(hit))
            valid_horizons.append(horizon)

    return {
        "samples": int(sum(samples)),
        "hit_rates": hit_rates,
        "median_hit_rate": round(median(hit_rates), 1) if hit_rates else None,
        "horizons": valid_horizons,
    }


def _context_alignment(state: Any, direction: str) -> int:
    """Small evidence adjustment, not a probability."""
    points = 0
    if _direction(getattr(state, "regime", "")) == direction:
        points += 1
    structure = str(getattr(state, "structure", "")).upper()
    if (direction == "LONG" and "BULL" in structure) or (
        direction == "SHORT" and "BEAR" in structure
    ):
        points += 2
    if _direction(getattr(state, "structure_direction", "")) == direction:
        points += 2
    if _direction(getattr(state, "mtf_direction", "")) == direction:
        points += 2

    metadata = getattr(state, "metadata", {}) or {}
    if isinstance(metadata, dict):
        for key in ("news_bias", "macro_bias", "fundamental_bias", "political_bias", "geopolitical_bias"):
            value = str(metadata.get(key, "")).upper()
            if (direction == "LONG" and value in {"LONG", "BULLISH", "POSITIVE"}) or (
                direction == "SHORT" and value in {"SHORT", "BEARISH", "NEGATIVE"}
            ):
                points += 1
    return points


def _explicit_analogs(name: str, direction: str) -> dict:
    """Read context-matched analogs if a real dataset has been supplied."""
    raw = _load(ANALOG_FILE, {})
    rows = raw.get("observations", []) if isinstance(raw, dict) else []
    if not isinstance(rows, list):
        return {"count": 0, "returns": []}

    matched = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("commodity", "")).strip().lower() != name.lower():
            continue
        if _direction(row.get("direction")) != direction:
            continue
        forward = _num(row.get("forward_return_10d"))
        if forward is not None:
            matched.append(forward)

    return {"count": len(matched), "returns": matched}


def predict_today(states: Iterable[Any]) -> dict[str, Any] | None:
    """Return the best evidence-backed forecast for today."""
    forecasts = _forecast_map()
    candidates = []

    for state in states:
        name = str(getattr(state, "commodity", "")).strip()
        if not name:
            continue

        forecast = forecasts.get(name)
        direction = _context_direction(state, forecast)
        if direction == "NONE":
            continue

        validation = _historical_validation(forecast, direction)
        analogs = _explicit_analogs(name, direction)

        # Explicit context-matched analogs have priority. Otherwise use
        # the repository's existing, recorded horizon validation evidence.
        if analogs["count"] >= MIN_SAMPLES:
            evidence_samples = analogs["count"]
            evidence_return = median(analogs["returns"])
            evidence_source = "context-matched historical analogs"
            hit_rate = sum(1 for x in analogs["returns"] if x > 0) / evidence_samples * 100
            if direction == "SHORT":
                hit_rate = 100.0 - hit_rate
        elif validation["samples"] >= MIN_SAMPLES:
            evidence_samples = validation["samples"]
            evidence_return = None
            evidence_source = "historical horizon validation"
            hit_rate = validation["median_hit_rate"]
        else:
            continue

        alignment = _context_alignment(state, direction)
        freshness_bonus = 1 if bool(getattr(state, "live", False)) else 0

        # Ranking index only. It is deliberately NOT called probability.
        evidence_index = float(hit_rate or 0) + alignment * 2 + freshness_bonus

        candidates.append({
            "commodity": name,
            "symbol": str(getattr(state, "symbol", "")),
            "direction": direction,
            "forecast": "SALE" if direction == "LONG" else "SCENDE",
            "evidence_index": round(evidence_index, 1),
            "historical_samples": evidence_samples,
            "historical_hit_rate": round(float(hit_rate), 1) if hit_rate is not None else None,
            "median_forward_return_10d": round(float(evidence_return), 3) if evidence_return is not None else None,
            "evidence_source": evidence_source,
            "alignment_points": alignment,
            "price": getattr(state, "price", None),
            "entry": getattr(state, "entry", None),
            "stop": getattr(state, "stop", None),
            "tp1": getattr(state, "tp1", None),
            "tp2": getattr(state, "tp2", None),
            "tp3": getattr(state, "tp3", None),
        })

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x["evidence_index"], x["historical_samples"]), reverse=True)
    winner = candidates[0]
    winner["alternatives"] = candidates[1:3]
    winner["paper_only"] = True
    return winner
