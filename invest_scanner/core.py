"""Small, deterministic long-only intraday selector; scores are not probabilities."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from math import isfinite
from statistics import mean


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    aliases: tuple[str, ...]
    ticker: str = ""
    eligibility: str = "DA_VERIFICARE_SU_INVEST"
    currency: str = "USD"


def ema(values, period):
    # Same seeded EMA used in engine/intraday_indicators.py (covered by its tests).
    if len(values) < period:
        return None
    value = mean(values[:period])
    alpha = 2 / (period + 1)
    for price in values[period:]:
        value = alpha * price + (1 - alpha) * value
    return value


def select_setup(instrument, payload, now, evidence=(), require_news=False):
    """Closed regular-session M5 only; use exchange session timestamps from provider.

    Rules: price above session VWAP and EMA20, positive 15m momentum, breakout
    of the previous 20 closed bars, not more than 2 ATR above EMA20. ATR/EMA
    exclude overnight jumps by using only today's regular-session candles.
    Returns (candidate or None, diagnostic reason); never synthesizes missing data.
    """
    if require_news and not evidence:
        return None, "NESSUNA_FONTE_PRIMARIA_PERTINENTE"
    meta = payload.get("meta", {})
    if meta.get("symbol", "").upper() != instrument.symbol.upper():
        return None, "SIMBOLO_NON_COINCIDENTE"
    if meta.get("currency") != instrument.currency or meta.get("instrumentType") != "EQUITY":
        return None, "VALUTA_O_TIPO_NON_COINCIDENTE"
    session = meta.get("currentTradingPeriod", {}).get("regular", {})
    start, end = session.get("start", 0), session.get("end", 0)
    ts = now.timestamp()
    if not start <= ts < end or end - ts < 900:
        return None, "MERCATO_CHIUSO_O_PROSSIMO_ALLA_CHIUSURA"
    quote_ts = meta.get("regularMarketTime", 0)
    if not 0 <= ts - quote_ts <= 120:
        return None, "PREZZO_NON_FRESCO"
    raw = payload.get("indicators", {}).get("quote", [{}])[0]
    rows = []
    for i, stamp in enumerate(payload.get("timestamp") or []):
        if not start <= stamp or stamp + 300 > min(ts, end):
            continue
        try:
            row = {k: float(raw[k][i]) for k in ("open", "high", "low", "close", "volume")}
        except (KeyError, IndexError, TypeError, ValueError):
            return None, "CANDELE_INCOMPLETE"
        if not all(isfinite(v) for v in row.values()) or min(row[k] for k in ("open", "high", "low", "close")) <= 0:
            return None, "CANDELE_NON_VALIDE"
        if row["volume"] <= 0 or not row["low"] <= min(row["open"], row["close"]) <= max(row["open"], row["close"]) <= row["high"]:
            return None, "OHLCV_NON_VALIDO"
        rows.append(dict(row, timestamp=stamp))
    if len(rows) < 21:
        return None, "ATTESA_21_CANDELE_M5_DI_SESSIONE"
    if any(b["timestamp"] - a["timestamp"] != 300 for a, b in zip(rows, rows[1:])):
        return None, "BUCHI_NELLE_CANDELE"
    if not 0 <= ts - (rows[-1]["timestamp"] + 300) <= 360:
        return None, "CANDELA_OBSOLETA"
    closes = [r["close"] for r in rows]
    price = closes[-1]
    try:
        current = float(meta["regularMarketPrice"])
    except (KeyError, TypeError, ValueError):
        return None, "PREZZO_ASSENTE"
    if not isfinite(current) or current <= 0:
        return None, "PREZZO_NON_VALIDO"
    atr = mean(max(b["high"] - b["low"], abs(b["high"] - a["close"]), abs(b["low"] - a["close"])) for a, b in list(zip(rows, rows[1:]))[-14:])
    if atr <= 0:
        return None, "ATR_NON_VALIDO"
    volume = sum(r["volume"] for r in rows)
    vwap = sum((r["high"] + r["low"] + r["close"]) / 3 * r["volume"] for r in rows) / volume
    avg = ema(closes, 20)
    momentum = price / closes[-4] - 1
    breakout = max(r["high"] for r in rows[-21:-1])
    if not price > max(vwap, avg, breakout) or momentum <= 0:
        return None, "LONG_NON_CONFERMATO"
    if price - avg > 2 * atr or abs(current - price) > 0.5 * atr:
        return None, "MOVIMENTO_GIA_ESTESO_O_PREZZO_ALLONTANATO"
    # Rank liquidity among setups; do not interpret a score as a win probability.
    dollar_volume = sum(r["close"] * r["volume"] for r in rows)
    if dollar_volume < 5_000_000:
        return None, "SCAMBI_DI_SESSIONE_INSUFFICIENTI"
    stop = min(price - 1.5 * atr, rows[-1]["low"])
    risk = current - stop
    if stop <= 0 or risk <= 0:
        return None, "LIVELLI_NON_VALIDI"
    relative_volume = rows[-1]["volume"] / mean(r["volume"] for r in rows[-21:-1])
    return {
        **asdict(instrument), "direction": "LONG", "status": "CANDIDATO_DEMO",
        "entry_reference": round(current, 4), "stop": round(stop, 4),
        "target": round(current + 2 * risk, 4), "risk_pct": round(risk / current * 100, 2),
        "vwap": round(vwap, 4), "ema20": round(avg, 4), "atr14": round(atr, 4),
        "momentum_15m_pct": round(momentum * 100, 3),
        "relative_volume": round(relative_volume, 2), "session_turnover_usd": round(dollar_volume),
        "rank_score": round(min(relative_volume, 5) + min(momentum * 100, 3) + min(dollar_volume / 1e9, 3), 3),
        "quote_time": datetime.fromtimestamp(quote_ts, timezone.utc).isoformat(),
        "bar_close_time": datetime.fromtimestamp(rows[-1]["timestamp"] + 300, timezone.utc).isoformat(),
        "exit_before": datetime.fromtimestamp(end - 300, timezone.utc).isoformat(),
        "news": list(evidence), "costs": "NON_INCLUSI: spread, slippage, cambio e imposte da verificare",
    }, "OK"


def top_two(candidates):
    unique = {c["symbol"]: c for c in candidates}
    return sorted(unique.values(), key=lambda c: (-c["rank_score"], c["symbol"]))[:2]
