from types import SimpleNamespace

import engine.invest as invest


def setup_demo(monkeypatch):
    monkeypatch.setenv("T212_API_KEY", "demo-key")
    monkeypatch.setenv("T212_API_SECRET", "demo-secret")
    monkeypatch.setattr(invest, "_AUTO_BUY_LAST_DAY", None)
    monkeypatch.setattr(invest, "get_account_summary", lambda: (True, {
        "currency": "EUR", "cash": {"availableToTrade": 100.0}
    }))
    monkeypatch.setattr(invest, "get_positions", lambda: (True, []))
    monkeypatch.setattr(invest, "get_pending_orders", lambda: (True, []))


def test_auto_demo_buys_budget_only_after_validated_long(monkeypatch):
    setup_demo(monkeypatch)
    signal = SimpleNamespace(
        direction="LONG", score=55.0, ticker="AAPL_US_EQ", symbol="AAPL",
        price=100.0, name="Apple"
    )
    monkeypatch.setattr(invest, "analyze_invest_universe", lambda: [signal])
    calls = []
    monkeypatch.setattr(invest, "place_demo_order_by_value", lambda *args, **kwargs: (
        calls.append((args, kwargs)) or "🧪 ORDINE DEMO INVIATO"
    ))

    result = invest.auto_buy_best_signal_budget(amount=10.0, min_score=50.0)

    assert "ORDINE DEMO INVIATO" in result
    assert calls == [(("AAPL_US_EQ", "AAPL", 10.0), {"account_currency": "EUR"})]


def test_auto_demo_fails_closed_when_account_cannot_be_verified(monkeypatch):
    setup_demo(monkeypatch)
    monkeypatch.setattr(invest, "get_account_summary", lambda: (False, {"error": "offline"}))
    monkeypatch.setattr(invest, "analyze_invest_universe", lambda: [SimpleNamespace(
        direction="LONG", score=80.0, ticker="AAPL_US_EQ", symbol="AAPL", price=100.0, name="Apple"
    )])
    calls = []
    monkeypatch.setattr(invest, "place_demo_order_by_value", lambda *args, **kwargs: calls.append(args))

    result = invest.auto_buy_best_signal_budget(amount=10.0, min_score=50.0)

    assert "nessun ordine" in result.lower()
    assert calls == []


def test_auto_demo_skips_existing_position(monkeypatch):
    setup_demo(monkeypatch)
    monkeypatch.setattr(invest, "get_positions", lambda: (True, [{"ticker": "AAPL_US_EQ", "quantity": 0.2}]))
    monkeypatch.setattr(invest, "analyze_invest_universe", lambda: [SimpleNamespace(
        direction="LONG", score=80.0, ticker="AAPL_US_EQ", symbol="AAPL", price=100.0, name="Apple"
    )])
    calls = []
    monkeypatch.setattr(invest, "place_demo_order_by_value", lambda *args, **kwargs: calls.append(args))

    result = invest.auto_buy_best_signal_budget(amount=10.0, min_score=50.0)

    assert "nessun ordine" in result.lower()
    assert calls == []
