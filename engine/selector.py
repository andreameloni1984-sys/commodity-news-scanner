"""
SOYUZ GAGARIN — ANTICIPATION SELECTOR v1.0

Selettore anticipatorio separato dal gate ENTRY.

Obiettivo:
    scegliere la commodity più promettente PRIMA che il trigger
    operativo sia confermato.

Non autorizza ordini e non modifica final_decision.
Usa:
    - struttura/regime/MTF intraday
    - storico disponibile nello state
    - forecast long-term 30/90/180/365
    - driver politici/ciclici/election/weather dei forecast
    - weather cache
    - eventuali news/fundamental/geopolitical input già presenti in metadata

I punteggi sono SCORE DI SELEZIONE, non probabilità statistiche.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
FORECAST_FILE = ROOT / "commodities_long_term_forecasts.json"
WEATHER_FILE = ROOT / "commodities_weather_cache.json"

FORECAST_MAX_AGE_DAYS = 45.0
WEATHER_MAX_AGE_DAYS = 45.0


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def _fresh_enough(created_at: Any, max_age_days: float) -> bool:
    if not created_at:
        return False
    try:
        from datetime import datetime, timezone
        text = str(created_at).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (
            datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        ).total_seconds() / 86400.0
        return 0.0 <= age <= max_age_days
    except (TypeError, ValueError):
        return False


def _forecast_map() -> dict[str, dict]:
    raw = _load_json(FORECAST_FILE, [])
    if not isinstance(raw, list):
        return {}

    best: dict[str, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if not _fresh_enough(
            item.get("created_at") or item.get("forecast_date"),
            FORECAST_MAX_AGE_DAYS,
        ):
            continue
        previous = best.get(name)
        if previous is None or str(item.get("forecast_date", "")) > str(
            previous.get("forecast_date", "")
        ):
            best[name] = item
    return best


def _weather_map() -> dict[str, dict]:
    raw = _load_json(WEATHER_FILE, {})
    if not isinstance(raw, dict):
        return {}
    timestamp = raw.get("timestamp")
    if not _fresh_enough(timestamp, WEATHER_MAX_AGE_DAYS):
        return {}
    data = raw.get("data", {})
    return data if isinstance(data, dict) else {}


def _bias_score(value: Any, direction: str) -> float:
    bias = _norm(value)
    if bias in {"LONG", "BULLISH", "POSITIVE"}:
        return 1.0 if direction == "LONG" else -1.0
    if bias in {"SHORT", "BEARISH", "NEGATIVE"}:
        return 1.0 if direction == "SHORT" else -1.0
    return 0.0


def _direction(state: Any, forecast: dict | None) -> str:
    setup = _norm(getattr(state, "setup_direction", "NONE"))
    structure = _norm(getattr(state, "structure_direction", "NONE"))
    mtf = _norm(getattr(state, "mtf_direction", "NONE"))

    if setup in {"LONG", "SHORT"}:
        return setup
    if structure in {"LONG", "SHORT"}:
        return structure
    if mtf in {"LONG", "SHORT"}:
        return mtf

    horizons = (forecast or {}).get("horizons", {})
    votes = {"LONG": 0.0, "SHORT": 0.0}
    for horizon in ("30", "90", "180"):
        item = horizons.get(horizon, {})
        direction = _norm(item.get("direction"))
        confidence = _float(item.get("confidence"))
        if direction in votes:
            votes[direction] += max(1.0, confidence)
    return "LONG" if votes["LONG"] >= votes["SHORT"] else "SHORT"


def _technical_component(state: Any, direction: str) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    regime = _norm(getattr(state, "regime", "UNKNOWN"))
    structure = _norm(getattr(state, "structure", "UNKNOWN"))
    structure_direction = _norm(getattr(state, "structure_direction", "NONE"))
    mtf_direction = _norm(getattr(state, "mtf_direction", "NONE"))
    mtf_alignment = _float(getattr(state, "mtf_alignment", 0))
    setup_direction = _norm(getattr(state, "setup_direction", "NONE"))

    if direction == "LONG" and regime == "TREND_UP":
        score += 7
        reasons.append("trend rialzista")
    elif direction == "SHORT" and regime == "TREND_DOWN":
        score += 7
        reasons.append("trend ribassista")

    if direction == "LONG" and structure == "BULLISH":
        score += 7
        reasons.append("struttura bullish")
    elif direction == "SHORT" and structure == "BEARISH":
        score += 7
        reasons.append("struttura bearish")

    if structure_direction == direction:
        score += 5
        reasons.append("direzione strutturale coerente")

    if mtf_direction == direction:
        score += 5
        reasons.append(f"MTF {mtf_alignment:.0f}% coerente")

    if setup_direction == direction:
        score += 6
        reasons.append("setup già formato")

    if bool(getattr(state, "breakout", False)):
        if _norm(getattr(state, "breakout_direction", "")) == direction:
            score += 3
            reasons.append("breakout nella direzione")

    if bool(getattr(state, "retest", False)):
        if _norm(getattr(state, "retest_direction", "")) == direction:
            score += 2
            reasons.append("retest nella direzione")

    return _clamp(score, 0, 35), reasons


def _history_component(state: Any, direction: str) -> tuple[float, list[str]]:
    closes = []
    for value in getattr(state, "closes", []) or []:
        try:
            closes.append(float(value))
        except (TypeError, ValueError):
            pass

    if len(closes) < 12:
        return 0.0, ["storico insufficiente"]

    windows = [12, min(288, len(closes)), min(7 * 288, len(closes))]
    score = 0.0
    reasons = []

    for window in windows:
        sample = closes[-window:]
        if len(sample) < 2 or sample[0] == 0:
            continue
        move = (sample[-1] - sample[0]) / abs(sample[0])
        aligned = (direction == "LONG" and move > 0) or (
            direction == "SHORT" and move < 0
        )
        if aligned:
            score += 10.0 / len(windows)
        elif abs(move) > 0.01:
            score -= 5.0 / len(windows)

    if score > 0:
        reasons.append("storico recente coerente")
    return _clamp(score, 0, 10), reasons


def _forecast_component(forecast: dict | None, direction: str) -> tuple[float, list[str]]:
    if not forecast:
        return 0.0, ["forecast lungo termine non disponibile"]

    horizons = forecast.get("horizons", {})
    score = 0.0
    reasons = []

    weights = {"30": 0.45, "90": 0.35, "180": 0.20}
    for horizon, weight in weights.items():
        item = horizons.get(horizon, {})
        long_p = _float(item.get("long_probability"), 50)
        short_p = _float(item.get("short_probability"), 50)
        edge = long_p - short_p if direction == "LONG" else short_p - long_p
        score += _clamp(50 + edge / 2, 0, 100) * weight * 0.25

    if score >= 15:
        reasons.append("forecast 30/90/180 favorevole")
    elif score >= 8:
        reasons.append("forecast lungo termine moderatamente favorevole")
    return _clamp(score, 0, 25), reasons


def _intelligence_component(
    state: Any,
    forecast: dict | None,
    weather: dict | None,
    direction: str,
) -> tuple[float, list[str], dict[str, Any]]:
    score = 0.0
    reasons: list[str] = []
    coverage = {
        "political": False,
        "weather": False,
        "news": False,
        "fundamental": False,
        "historical": False,
    }

    metadata = getattr(state, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}

    for key, label in (
        ("political_bias", "politica"),
        ("geopolitical_bias", "geopolitica"),
        ("fundamental_bias", "fondamentali"),
        ("macro_bias", "macro"),
    ):
        if key in metadata:
            coverage["political" if "polit" in key or "geo" in key else "fundamental"] = True
            alignment = _bias_score(metadata.get(key), direction)
            score += 3.0 * alignment
            if alignment > 0:
                reasons.append(f"{label} favorevole")

    for key in ("news_bias", "news_score", "news_sentiment"):
        if key in metadata:
            coverage["news"] = True
            value = metadata.get(key)
            if isinstance(value, str):
                alignment = _bias_score(value, direction)
                score += 4.0 * alignment
            else:
                value = _float(value, 0)
                score += _clamp(value, -100, 100) / 25.0
            if score > 0:
                reasons.append("news favorevoli")

    drivers = (forecast or {}).get("drivers", {})
    if isinstance(drivers, dict):
        political = _float(drivers.get("political"), 0)
        elections = _float(drivers.get("elections"), 0)
        cyclical = _float(drivers.get("cyclical"), 0)
        weather_driver = _float(drivers.get("weather"), 0)

        # Driver forecast values are directional inputs; the selector
        # treats positive as LONG and negative as SHORT.
        for value, label, multiplier in (
            (political, "politica forecast", 2.0),
            (elections, "elections forecast", 0.8),
            (cyclical, "ciclo", 1.5),
        ):
            signed = value if direction == "LONG" else -value
            if abs(signed) > 0.05:
                score += max(-3.0, min(3.0, signed * multiplier))
                if signed > 0:
                    reasons.append(f"{label} favorevole")

        signed_weather = weather_driver if direction == "LONG" else -weather_driver
        if abs(signed_weather) > 0.05:
            score += max(-2.0, min(2.0, signed_weather))
            coverage["weather"] = True

    if weather:
        coverage["weather"] = True
        weather_score = _float(weather.get("score"), 0)
        signed_weather = weather_score if direction == "LONG" else -weather_score
        score += max(-3.0, min(3.0, signed_weather / 10.0))
        if signed_weather > 0:
            reasons.append("meteo favorevole")

    # Generic pre-computed intelligence containers are accepted without
    # creating a second engine.
    for key, category in (
        ("fundamental_events", "fundamental"),
        ("macro_factors", "fundamental"),
        ("supply_demand_factors", "fundamental"),
        ("political_events", "political"),
        ("geopolitical_events", "political"),
        ("weather_factors", "weather"),
    ):
        if metadata.get(key):
            coverage[category] = True

    return _clamp(score + 10.0, 0, 20), reasons, coverage


def select_anticipation(states: Iterable[Any]) -> list[dict[str, Any]]:
    forecasts = _forecast_map()
    weather_data = _weather_map()
    selections = []

    for state in states:
        name = str(getattr(state, "commodity", "")).strip()
        forecast = forecasts.get(name)
        weather = weather_data.get(name)

        direction = _direction(state, forecast)
        technical, technical_reasons = _technical_component(state, direction)
        history, history_reasons = _history_component(state, direction)
        long_term, forecast_reasons = _forecast_component(forecast, direction)
        intelligence, intelligence_reasons, coverage = _intelligence_component(
            state, forecast, weather, direction
        )

        total = _clamp(technical + history + long_term + intelligence)

        trigger_confirmed = bool(getattr(state, "trigger_confirmed", False))
        final_decision = _norm(getattr(state, "final_decision", "WAIT"))
        stage = "ENTRY" if final_decision == "ENTRY" and trigger_confirmed else "EARLY WATCH"

        blockers = list(getattr(state, "blockers", []) or [])
        if not trigger_confirmed:
            blockers.append("trigger non confermato")
        if not getattr(state, "live", False):
            blockers.append("dato non LIVE")

        selections.append({
            "commodity": name,
            "symbol": str(getattr(state, "symbol", "")),
            "direction": direction,
            "score": round(total, 1),
            "stage": stage,
            "decision": final_decision,
            "price": getattr(state, "price", None),
            "entry": getattr(state, "entry", None),
            "stop": getattr(state, "stop", None),
            "tp1": getattr(state, "tp1", None),
            "tp2": getattr(state, "tp2", None),
            "tp3": getattr(state, "tp3", None),
            "trigger": getattr(state, "trigger", "NONE"),
            "reasons": (technical_reasons + forecast_reasons + history_reasons + intelligence_reasons)[:7],
            "coverage": coverage,
            "blockers": blockers[:4],
        })

    selections.sort(
        key=lambda item: (item["score"], item["stage"] == "ENTRY"),
        reverse=True,
    )
    return selections
