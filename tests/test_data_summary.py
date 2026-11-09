from types import SimpleNamespace

from main import _print_data_summary


def test_data_summary_prints_execution_quote_identity_and_provenance(capsys):
    state = SimpleNamespace(
        commodity="Oro",
        symbol="XAU/USD",
        data_age_seconds=602.8,
        data_source="YAHOO",
        price=4050.25,
        atr=2.7286,
        metadata={
            "data_status": "STALE",
            "quote_provider": "YAHOO",
            "quote_symbol": "GC=F",
            "quote_timestamp": "2026-11-04T06:50:00+00:00",
            "quote_market_type": "FUTURES_CONTINUOUS",
            "quote_age_seconds": 602.8,
            "execution_provider": "YAHOO",
            "execution_symbol": "GC=F",
            "execution_market_type": "FUTURES_CONTINUOUS",
        },
    )

    _print_data_summary([state])

    output = capsys.readouterr().out
    assert "[XAU/USD] STALE" in output
    assert "provider=YAHOO" in output
    assert "quote_symbol=GC=F" in output
    assert "market=FUTURES_CONTINUOUS" in output
    assert "expiry=N/D" in output
    assert "quote_ts=2026-11-04T06:50:00+00:00" in output
    assert "price=4050.25" in output
    assert "ATR=2.7286" in output


def test_data_summary_marks_unavailable_contract_provenance_as_not_available(capsys):
    state = SimpleNamespace(
        commodity="WTI",
        symbol="WTI/USD",
        data_age_seconds=None,
        data_source="",
        price=None,
        atr=None,
        metadata={"data_status": "DATA_ERROR"},
    )

    _print_data_summary([state])

    output = capsys.readouterr().out
    assert "quote_symbol=N/D" in output
    assert "market=N/D" in output
    assert "expiry=N/D" in output
    assert "quote_ts=N/D" in output
    assert "age=N/D" in output
