"""Catalyst-first paper setup: light price confirmation and indicative levels."""
from datetime import datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

from invest_v2.gagarin import _ema

MINUTE = timedelta(minutes=1)
MAX_QUOTE_AGE = 3 * MINUTE
HORIZONS = (5, 15, 30, 60)
RANK = {None: 0, "PREPARARE": 1, "ENTRARE": 2}


def assess(event, bars, now):
    return evaluate(event, bars, now)[0]


def evaluate(event, bars, now):
    """Return (signal, None) or (None, reason). Never invents levels."""
    if event.direction not in ("LONG", "SHORT"):
        return None, "impatto direzionale ambiguo"
    bars = [bar for bar in bars if bar.closed_at <= now]
    if not bars:
        return None, "barre concluse assenti"
    if now - bars[-1].closed_at > MAX_QUOTE_AGE:
        return None, "ultima barra scaduta (oltre 180 secondi)"
    if any(not all(isfinite(value) and value > 0 for value in
                   (b.close, b.high, b.low, b.volume)) or not b.low <= b.close <= b.high
           for b in bars):
        return None, "prezzi o volumi non validi"
    if any(a.closed_at >= b.closed_at for a, b in zip(bars, bars[1:])):
        return None, "barre duplicate o fuori sequenza"
    last = bars[-1]
    if last.closed_at <= event.published:
        return None, "nessuna barra successiva alla notizia"
    if sum(b.close * b.volume for b in bars[-5:]) < 100_000:
        return None, "controvalore stimato insufficiente"
    # Reference: last bar before the news; pre-market news uses the first session bar.
    ref = next((b for b in reversed(bars) if b.closed_at <= event.published), bars[0])
    sign = 1 if event.direction == "LONG" else -1
    move = last.close / ref.close - 1
    if ref is last or sign * move <= 0:
        return None, "il prezzo non conferma ancora la direzione"
    signal = {
        "state": "PREPARARE", "price": last.close, "quote_at": last.closed_at.isoformat(),
        "move": move, "reason": event.category, "heuristic_score": float(event.impact),
        "levels": None,
    }
    if len(bars) < 15:
        return signal, None  # direction confirmed, too few bars for ATR: no levels

    closes = [b.close for b in bars]
    atr = sum(max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close))
              for a, b in zip(bars[-15:-1], bars[-14:])) / 14
    if atr <= 0:
        return signal, None
    if sign * (last.close - ref.close) > 3 * atr:
        return None, "movimento già esteso oltre 3 ATR"
    ema20 = _ema(closes, 20)
    baseline = bars[-21:-1]
    volume = last.volume / (sum(b.volume for b in baseline) / len(baseline))
    trend = sign * (last.close - ema20) > 0
    risk = min(max(1.5 * atr, sign * (last.close - ema20) + 0.25 * atr), 3 * atr)
    precision = 2 if last.close >= 1 else 4
    entry = round(last.close, precision)
    stop = round(entry - sign * risk, precision)
    target = round(entry + sign * 2 * abs(entry - stop), precision)
    if entry == stop or min(entry, stop, target) <= 0:
        return signal, None
    signal.update(
        state="ENTRARE" if sign > 0 and trend else "PREPARARE", levels=[entry, stop, target],
        heuristic_score=event.impact + trend + min(volume, 3),
        technical={"atr14": atr, "ema20": ema20, "relative_volume": volume, "trend": trend},
    )
    return signal, None


def rome(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.astimezone(ZoneInfo("Europe/Rome"))


def message(event, name, signal, now):
    levels = signal["levels"]
    if levels:
        entry, stop, target = levels
        quote = rome(signal["quote_at"]).strftime("%H:%M")
        price_lines = [f"ENTRY: {entry} (quotazione {quote})", f"STOP LOSS: {stop}",
                       f"TAKE PROFIT: {target}"]
    else:
        price_lines = ["ENTRY: n.d. (dati insufficienti)", "STOP LOSS: n.d.", "TAKE PROFIT: n.d."]
    lines = [
        "🚀 GAGARIN INVEST", "",
        f"STRUMENTO: {event.symbol} — {name}",
        f"DIREZIONE: {event.direction}",
        f"STATO: {signal['state']}",
        *price_lines,
        f"NOTIZIA: {event.category} — {event.title[:220]}",
        f"FONTE: {event.url}",
        f"ORARIO: {rome(now).strftime('%d/%m/%Y %H:%M')} (ora italiana)",
    ]
    if event.direction == "SHORT":
        lines.append("NOTA: SHORT solo previsione analitica, non eseguibile su INVEST")
    lines += ["", "PAPER ONLY"]
    return "\n".join(lines)
