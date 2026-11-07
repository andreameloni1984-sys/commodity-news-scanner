"""Regression tests: Trading 212 CFD Telegram commands must not invoke futures."""

import pytest

from engine.trading212 import build_manual_cfd_quote, compare_price
from telegram import bot


def _forbidden(*args, **kwargs):
    raise AssertionError("A Trading 212 CFD command invoked the futures path.")


@pytest.mark.parametrize(
    "command",
    [
        "/aggressivo212",
        "/aggressivo212 WTI 78.10 78.13",
        "/soft212",
        "/soft212 WTI 78.10 78.13",
    ],
)
def test_t212_profile_commands_fail_closed_without_futures_or_fx(monkeypatch, command):
    monkeypatch.setattr(bot, "_run_analysis", _forbidden)
    monkeypatch.setattr(bot, "get_last_results", _forbidden)
    monkeypatch.setattr(bot, "set_last_results", _forbidden)
    monkeypatch.setattr(bot, "_format_classifica", _forbidden)

    message = bot._command_response(command)

    assert "TRADING 212 — CFD | GAGARIN" in message
    assert "BLOCCATO" in message
    assert "FEED CFD TRADING 212 NON VERIFICATO" in message
    assert "Entry / SL / TP: NON CALCOLATI." in message
    assert "FX AGGRESSIVE" not in message


def test_prezzo212_is_manual_quote_only_and_never_requests_futures(monkeypatch):
    monkeypatch.setattr(bot, "_run_analysis", _forbidden)
    monkeypatch.setattr(bot, "get_last_results", _forbidden)
    monkeypatch.setattr(bot, "set_last_results", _forbidden)

    message = bot._command_response("/prezzo212 WTI 78.10 78.13")

    assert "TRADING 212 — CFD QUOTE (INSERIMENTO MANUALE)" in message
    assert "Contratto: NON VERIFICATO" in message
    assert "Entry / SL / TP: NON CALCOLATI" in message
    assert "Nessun prezzo Yahoo futures o BiQuote" in message


@pytest.mark.parametrize("symbol", ["GAS", "PLATINO", "PALLADIO", "EURUSD", "SPY"])
def test_t212_manual_quote_rejects_every_out_of_scope_instrument(symbol):
    result = build_manual_cfd_quote(symbol, 10.0, 10.1)
    assert result["status"] == "UNSUPPORTED_INSTRUMENT"


def test_t212_legacy_comparison_shim_never_uses_futures_reference():
    result = compare_price("WTI", 78.12, 78.10, 78.13)
    assert result["verdict"] == "NO_COMPARABLE_CFD_REFERENCE"
    assert result["gagarin_price"] is None
    assert result["diff_pct"] is None


@pytest.mark.parametrize(
    "symbol",
    ["ORO", "ARGENTO", "RAME", "WTI", "BRENT", "GRANO", "MAIS", "SOIA"],
)
def test_t212_manual_quote_accepts_exactly_the_eight_selected_commodities(symbol):
    result = build_manual_cfd_quote(symbol, 10.0, 10.1)
    assert result["status"] == "MANUAL_QUOTE_ONLY"
    assert result["broker"] == "TRADING212"
    assert result["market_type"] == "CFD"
    assert result["broker_symbol"] is None
    assert result["contract"] is None
    assert result["expiry"] is None
    assert result["currency"] is None
    assert result["entry"] is None
    assert result["stop_loss"] is None
    assert result["take_profit"] is None


@pytest.mark.parametrize(
    "bid,ask",
    [(True, 78.13), (78.10, True), (False, 78.13), (78.10, False)],
)
def test_t212_manual_quote_rejects_boolean_prices(bid, ask):
    result = build_manual_cfd_quote("WTI", bid, ask)
    assert result["status"] == "INVALID_QUOTE"
    assert result.get("entry") is None
    assert result.get("stop_loss") is None
    assert result.get("take_profit") is None
