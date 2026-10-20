from paper_portfolio import PaperPortfolio


def signal(symbol="XAU/USD", direction="LONG", entry=100, stop=98, tp1=103, tp2=104, tp3=105):
    return {
        "action": "PAPER_ENTRY", "paper_only": True, "symbol": symbol,
        "commodity": symbol, "direction": direction, "entry": entry, "stop": stop,
        "tp1": tp1, "tp2": tp2, "tp3": tp3,
    }


def test_opens_valid_long_and_sizes_from_risk_budget():
    portfolio = PaperPortfolio(100)
    position = portfolio.open_signal(signal())
    assert position is not None
    assert position["allocation"] <= 25
    assert position["allocation"] * ((100 - 98) / 100) <= 1.0 + 0.01


def test_opens_valid_short_with_bracket_in_correct_order():
    portfolio = PaperPortfolio(100)
    position = portfolio.open_signal(signal("WTI/USD", "SHORT", 100, 102, 97, 96, 95))
    assert position is not None
    assert position["direction"] == "SHORT"


def test_rejects_bad_rr_before_reserving_cash():
    portfolio = PaperPortfolio(100)
    row = signal(tp1=102.5)
    assert portfolio.open_signal(row) is None
    assert portfolio.cash == 100


def test_rejects_duplicate_open_symbol():
    portfolio = PaperPortfolio(100)
    assert portfolio.open_signal(signal()) is not None
    assert portfolio.open_signal(signal()) is None


def test_staged_take_profit_closes_one_third_at_each_target():
    portfolio = PaperPortfolio(100)
    opened = portfolio.open_signal(signal())
    assert opened is not None
    symbol = opened["symbol"]
    portfolio.evaluate_exits({symbol: 103})
    position = next(p for p in portfolio.positions if p.symbol == symbol)
    assert position.tp1_hit and not position.tp2_hit
    assert position.remaining_fraction < 1
    portfolio.evaluate_exits({symbol: 104})
    assert position.tp2_hit
    portfolio.evaluate_exits({symbol: 105})
    assert position.status == "CLOSED"
    assert position.tp3_hit


def test_stop_has_priority_over_take_profit():
    portfolio = PaperPortfolio(100)
    opened = portfolio.open_signal(signal())
    assert opened is not None
    closed = portfolio.evaluate_exits({opened["symbol"]: 97})
    assert closed
    assert closed[0]["status"] == "CLOSED"
    assert closed[0]["exit"] == 98


def test_rejects_nonfinite_prices():
    portfolio = PaperPortfolio(100)
    assert portfolio.open_signal(signal(entry=float("nan"))) is None
    assert portfolio.open_signal(signal(entry=float("inf"))) is None
