from paper_portfolio import PaperPortfolio


def test_take_profit_uses_level_price_not_boolean():
    book = PaperPortfolio(100)
    opened = book.open_signal({
        "action": "PAPER_SIGNAL",
        "symbol": "GC",
        "commodity": "gold",
        "direction": "LONG",
        "entry": 100.0,
        "stop": 95.0,
        "tp1": 110.0,
        "tp2": 120.0,
        "tp3": 130.0,
    })
    assert opened is not None
    events = book.evaluate_exits({"GC": 110.0})
    assert events[0]["exit"] == 110.0
    assert events[0]["reason"] == "TP1"
    assert book.positions[0].status == "OPEN"
    snap = book.snapshot()
    assert snap["equity"] > 100


def test_stop_rejects_wrong_side_and_sizes_by_risk():
    book = PaperPortfolio(100)
    blocked = book.open_signal({
        "action": "PAPER_SIGNAL",
        "symbol": "CL",
        "direction": "LONG",
        "entry": 80.0,
        "stop": 90.0,
    })
    assert blocked is None
    opened = book.open_signal({
        "action": "PAPER_SIGNAL",
        "symbol": "CL",
        "direction": "LONG",
        "entry": 80.0,
        "stop": 76.0,
    })
    assert opened is not None
    # 1% of 100 / 5% stop distance = 20, under the 25% cap
    assert opened["allocation"] == 20.0
