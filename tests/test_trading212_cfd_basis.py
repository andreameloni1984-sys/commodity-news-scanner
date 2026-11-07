"""Regression tests for Trading 212 CFD quote basis isolation."""

from engine.trading212 import (
    build_manual_cfd_quote,
    compare_price,
    format_manual_cfd_quote,
)


def test_manual_t212_quote_keeps_broker_contract_and_currency_unverified():
    quote = build_manual_cfd_quote("WTI", 78.10, 78.13)

    assert quote["broker"] == "TRADING212"
    assert quote["market_type"] == "CFD"
    assert quote["logical_symbol"] == "WTI/USD"
    assert quote["broker_symbol"] is None
    assert quote["contract"] is None
    assert quote["expiry"] is None
    assert quote["currency"] is None
    assert quote["reference_price"] is None
    assert quote["entry"] is None
    assert quote["stop_loss"] is None
    assert quote["take_profit"] is None
    assert quote["levels_status"] == "BLOCKED_NO_VERIFIED_SAME_SERIES_CFD_CANDLES"

    message = format_manual_cfd_quote(quote)
    assert "Trading 212 | Mercato: CFD" in message
    assert "Contratto: NON VERIFICATO" in message
    assert "Entry / SL / TP: NON CALCOLATI" in message
    assert "Nessun prezzo Yahoo futures o BiQuote" in message


def test_manual_t212_quote_accepts_only_the_eight_selected_commodities():
    for symbol in ("SPY", "QQQ", "EURUSD", "GAS", "PLATINO", "PALLADIO"):
        assert build_manual_cfd_quote(symbol, 10, 10.1)["status"] == "UNSUPPORTED_INSTRUMENT"

    for symbol in ("ORO", "ARGENTO", "RAME", "WTI", "BRENT", "GRANO", "MAIS", "SOIA"):
        assert build_manual_cfd_quote(symbol, 10, 10.1)["status"] == "MANUAL_QUOTE_ONLY"


def test_legacy_comparison_never_uses_futures_price_as_cfd_reference():
    result = compare_price("WTI", 78.12, 78.10, 78.13)

    assert result["verdict"] == "NO_COMPARABLE_CFD_REFERENCE"
    assert result["gagarin_price"] is None
    assert result["diff_pct"] is None


def test_telegram_prezzo212_does_not_run_gagarin_futures_analysis(monkeypatch):
    from telegram import bot

    def forbidden(*args, **kwargs):
        raise AssertionError("T212 CFD quote must not request a futures reference.")

    monkeypatch.setattr(bot, "get_last_results", forbidden)
    monkeypatch.setattr(bot, "_run_analysis", forbidden)

    message = bot._command_response("/prezzo212 WTI 78.10 78.13")

    assert "TRADING 212 — CFD QUOTE" in message
    assert "Prezzo di riferimento CFD comparabile: N/D" in message

def test_aggressive_desk_routes_manual_cfd_quotes_to_dedicated_command(monkeypatch):
    from telegram import bot

    def forbidden(*args, **kwargs):
        raise AssertionError("A manual CFD quote must not trigger the futures desk.")

    monkeypatch.setattr(bot, "_run_analysis", forbidden)

    message = bot._command_response("/aggressivo212 WTI 78.10 78.13")

    assert "/prezzo212 SIMBOLO BID ASK" in message
    assert "/prezzo212 WTI 78.10 78.13" in message
    assert "motore futures GAGARIN" in message
