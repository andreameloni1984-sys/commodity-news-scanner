"""Catalyst-first session analysis and paper setup levels."""
from datetime import datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

from invest_v2.gagarin import _ema

MINUTE = timedelta(minutes=1)
HORIZONS = (5, 15, 30, 60)


def assess(event, bars, now):
    return evaluate(event, bars, now)[0]


def evaluate(event, bars, now):
    if event.direction not in ("LONG", "SHORT"):
        return None, "impatto direzionale ambiguo"
    bars = [bar for bar in bars if bar.closed_at <= now]
    if not bars:
        return None, "barre concluse assenti"
    if now - bars[-1].closed_at > 2 * MINUTE:
        return None, "ultima barra scaduta (oltre 120 secondi)"
    if any(not all(isfinite(value) and value > 0 for value in
                   (b.close, b.high, b.low, b.volume)) or not b.low <= b.close <= b.high
           for b in bars):
        return None, "prezzi o volumi non validi"
    if any(a.closed_at >= b.closed_at for a, b in zip(bars, bars[1:])):
        return None, "barre duplicate o fuori sequenza"
    last = bars[-1]
    if last.closed_at <= event.published:
        return None, "nessuna barra successiva alla notizia"
    prior = next((b for b in reversed(bars) if b.closed_at <= event.published), None)
    if prior is not None and event.published - prior.closed_at > 2 * MINUTE:
        prior = None
    if sum(b.close * b.volume for b in bars[-5:]) < 100_000:
        return None, "controvalore stimato insufficiente"
    result = {
        "state": "PREPARARE", "phase": "anticipato", "price": last.close,
        "quote_at": last.closed_at.isoformat(), "move": None,
        "reason": event.category, "heuristic_score": event.impact, "levels": None,
    }
    if prior is not None:
        result["move"] = last.close / prior.close - 1
    if len(bars) < 21 or any(b.closed_at - a.closed_at != MINUTE
                             for a, b in zip(bars[-21:-1], bars[-20:])):
        return result, None
    closes = [b.close for b in bars]
    baseline = bars[-21:-1]
    atr = sum(max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close))
              for a, b in zip(bars[-15:-1], bars[-14:])) / 14
    if atr <= 0:
        return result, None

    sign = 1 if event.direction == "LONG" else -1
    volume = last.volume / (sum(b.volume for b in baseline) / len(baseline))
    ema20 = _ema(closes, 20)
    momentum5, momentum15 = last.close - closes[-6], last.close - closes[-16]
    changes = [b - a for a, b in zip(closes[-15:-1], closes[-14:])]
    movement = sum(map(abs, changes))
    rsi = 100 * sum(max(x, 0) for x in changes) / movement if movement else 50
    has_vwap = all(b.vwap is not None and isfinite(b.vwap) and b.vwap > 0 for b in bars)
    vwap = sum(b.vwap * b.volume for b in bars) / sum(b.volume for b in bars) if has_vwap else None
    result["technical"] = {
        "ema20": ema20, "ema50": _ema(closes, 50) if len(closes) >= 50 else None,
        "ema200": _ema(closes, 200) if len(closes) >= 200 else None,
        "atr14": atr, "rsi14": rsi, "vwap": vwap, "relative_volume": volume,
        "momentum5": momentum5, "momentum15": momentum15,
    }
    if prior:
        if sign * (last.close - prior.close) >= 3 * atr:
            result.update(state="SCARTARE", phase="tardivo", reason="Movimento già esteso oltre 3 ATR")
            return result, None

    boundary = max(b.high for b in baseline) if sign > 0 else min(b.low for b in baseline)
    breakout = sign * (last.close - boundary) > 0
    pullback = sign * (closes[-2] - ema20) <= 0 < sign * (last.close - ema20)
    if prior is None or volume < 1.5 or min(sign * momentum5, sign * momentum15) <= 0:
        return result, None
    if not (breakout or pullback):
        return result, None

    risk = max(1.5 * atr, sign * (last.close - (boundary if breakout else ema20)) + 0.25 * atr)
    if risk > 3 * atr:
        return result, None
    precision = 2 if last.close >= 1 else 4
    entry = round(last.close, precision)
    stop = round(entry - sign * risk, precision)
    risk = abs(entry - stop)
    targets = [round(entry + sign * multiple * risk, precision) for multiple in (1, 2, 3)]
    if risk <= 0 or min(entry, stop, *targets) <= 0:
        return result, None
    setup = "Breakout" if breakout else "Pullback su EMA20"
    result.update(state="ENTRARE" if sign > 0 else "PREPARARE", phase="confermato",
                  reason=f"{event.category}. {setup}. Volume relativo {volume:.1f}×",
                  levels=[entry, stop, *targets], heuristic_score=event.impact + min(volume, 5))
    return result, None


def message(event, name, signal, now):
    lines = [
        "🚀 GAGARIN — INVEST", "", f"TITOLO: {name} ({event.symbol})",
        f"DIREZIONE: {event.direction}", f"STATO: {signal['state']} · {signal['phase']}",
    ]
    if signal["levels"]:
        lines.extend(f"{label}: {value}" for label, value in
                     zip(("ENTRY", "STOP LOSS", "TP1", "TP2", "TP3"), signal["levels"]))
        lines.append("R/R: 1:1 / 1:2 / 1:3")
    sample = signal.get("historical")
    if sample:
        lines.append(f"PRECEDENTI PRAVDA: {sample['samples']} · movimento medio a 60 min {sample['mean_return_60m']:+.2%}")
    if signal["move"] is not None:
        lines.append(f"MOVIMENTO DALLA NOTIZIA: {signal['move']:+.2%}")
    if event.direction == "SHORT":
        lines.append("SHORT analitico · Apertura di una posizione corta indisponibile")
    lines.extend([
        f"NOTIZIA: {event.title[:350]}", f"FONTE: {event.source} · {event.url}",
        f"MOTIVO: {signal['reason']}", f"PUNTEGGIO EURISTICO: {signal['heuristic_score']:.1f}",
        f"DATI: {datetime_rome(signal['quote_at'])}",
        f"ORARIO: {now.astimezone(ZoneInfo('Europe/Rome')).isoformat(timespec='seconds')}",
        "SIMULAZIONE INTERNA",
    ])
    return "\n".join(lines)


def datetime_rome(iso):
    return datetime.fromisoformat(iso).astimezone(ZoneInfo("Europe/Rome")).isoformat(timespec="seconds")
