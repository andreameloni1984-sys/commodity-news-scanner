from engine.biquote_cfd_signals import evaluate_cfd_snapshot

def sample(breakout=True):
    candles = [{"open":100, "high":101, "low":99, "close":100} for _ in range(29)]
    candles.append({"open":100, "high":104 if breakout else 101, "low":99, "close":103 if breakout else 100})
    return {"requested_instrument":"XAU/USD","symbol":"XAUUSD","status":"LIVE",
            "candles_status":"LIVE","bid":102.9,"ask":103.1,"candles":candles}

def test_cfd_breakout_has_independent_price_basis():
    result=evaluate_cfd_snapshot(sample())
    assert result["decision"]=="PAPER_WATCH"
    assert result["market_type"]=="CFD"
    assert result["execution_eligible"] is False
    assert result["entry"]==103.1
    assert result["stop"]<result["entry"]<result["tp1"]<result["tp2"]
    assert result["instrument_id"]=="BIQUOTE:XAUUSD:CFD"

def test_no_breakout_no_signal():
    assert evaluate_cfd_snapshot(sample(False))["decision"]=="NO_SIGNAL"

def test_stale_cfd_never_generates_setup():
    s=sample();s["status"]="MARKET_CLOSED"
    assert evaluate_cfd_snapshot(s)["reason"]=="CFD_DATA_NOT_LIVE"

def test_futures_symbol_cannot_be_relabelled_cfd():
    s=sample();s["symbol"]="GC=F"
    assert evaluate_cfd_snapshot(s)["reason"]=="UNSUPPORTED_CFD_SYMBOL"
