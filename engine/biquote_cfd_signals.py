"""Independent BiQuote CFD paper setups. Never route to futures execution."""
from __future__ import annotations
from math import isfinite
from engine.data import BIQUOTE_CFD_REFERENCE_SYMBOLS, _fetch_biquote_cfd_reference

def evaluate_cfd_snapshot(snapshot):
    """Return a CFD-only M5 momentum hypothesis, or an explicit no-signal reason."""
    symbol = snapshot.get("requested_instrument")
    result = {"instrument_id": f"BIQUOTE:{snapshot.get('symbol')}:CFD",
              "symbol": symbol, "provider": "BIQUOTE", "market_type": "CFD",
              "mode": "PAPER_ONLY", "execution_eligible": False,
              "decision": "NO_SIGNAL"}
    if symbol not in BIQUOTE_CFD_REFERENCE_SYMBOLS or snapshot.get("symbol") != BIQUOTE_CFD_REFERENCE_SYMBOLS.get(symbol):
        return dict(result, reason="UNSUPPORTED_CFD_SYMBOL")
    if snapshot.get("status") != "LIVE" or snapshot.get("candles_status") != "LIVE":
        return dict(result, reason="CFD_DATA_NOT_LIVE")
    candles = snapshot.get("candles") or []
    if len(candles) < 30:
        return dict(result, reason="INSUFFICIENT_CLOSED_M5")
    try:
        bid, ask = float(snapshot["bid"]), float(snapshot["ask"])
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]
        if not all(isfinite(v) and v > 0 for v in [bid, ask, *highs, *lows, *closes]) or ask < bid:
            raise ValueError("INVALID_PRICE")
        if any(lo > min(hi, cl) or hi < cl for lo, hi, cl in zip(lows, highs, closes)):
            raise ValueError("INVALID_CANDLES")
        trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(len(closes)-14, len(closes))]
        atr = sum(trs)/len(trs)
        if atr <= 0:
            return dict(result, reason="ZERO_ATR")
        spread = ask-bid
        if spread > 0.25*atr:
            return dict(result, reason="SPREAD_TOO_WIDE_FOR_M5")
        # Breakout measured only against prior CLOSED bars. Bid/ask entry
        # is always from the same CFD provider, never from futures.
        prior_high, prior_low = max(highs[-21:-1]), min(lows[-21:-1])
        direction = "LONG" if closes[-1] > prior_high else "SHORT" if closes[-1] < prior_low else None
        if not direction:
            return dict(result, reason="NO_M5_BREAKOUT")
        entry = ask if direction == "LONG" else bid
        stop_distance = max(1.5*atr, 2*spread)
        stop = entry-stop_distance if direction == "LONG" else entry+stop_distance
        if stop <= 0:
            return dict(result, reason="INVALID_STOP")
        sign = 1 if direction == "LONG" else -1
        tp1, tp2 = entry+sign*1.5*stop_distance, entry+sign*2.5*stop_distance
        return dict(result, decision="PAPER_WATCH", direction=direction,
                    entry=round(entry, 6), stop=round(stop, 6),
                    tp1=round(tp1, 6), tp2=round(tp2, 6),
                    rr_tp1=1.5, rr_tp2=2.5, atr_m5=round(atr, 6),
                    spread=round(spread, 6), quote_timestamp=snapshot.get("quote_timestamp"),
                    reason="CLOSED_M5_BREAKOUT_NOT_AUTHORIZED_ENTRY")
    except (TypeError, ValueError, KeyError, IndexError):
        return dict(result, reason="INVALID_CFD_DATA")

def scan_biquote_cfds():
    return [evaluate_cfd_snapshot(_fetch_biquote_cfd_reference(symbol))
            for symbol in BIQUOTE_CFD_REFERENCE_SYMBOLS]
