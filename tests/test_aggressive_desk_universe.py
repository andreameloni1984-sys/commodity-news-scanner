from types import SimpleNamespace

from soyuz_gagarin.aggressive_desk import format_aggressive_desk


def _state(name, symbol):
    return SimpleNamespace(
        commodity=name,
        symbol=symbol,
        price=100.0,
        atr=1.0,
        data_ok=True,
        live=True,
        regime="TREND_DOWN",
        structure="BEARISH",
        structure_direction="SHORT",
        mtf_direction="SHORT",
        setup_direction="SHORT",
        trigger_confirmed=False,
        pre_move_score=70.0,
        pre_move_direction="SHORT",
        opportunity_score=60.0,
        opportunity_direction="SHORT",
        continuation_score=50.0,
        expected_move_pct=1.0,
        probability=55.0,
        quality=45.0,
        confidence=45.0,
        entry=100.0,
        stop=102.0,
        tp1=97.0,
        tp2=96.0,
        tp3=95.0,
        rr3=2.5,
        final_decision="WAIT",
        metadata={"data_status": "LIVE"},
    )


def test_aggressive_desk_excludes_removed_metals_and_keeps_selected_gold():
    message = format_aggressive_desk([
        _state("Palladio", "XPD/USD"),
        _state("Platino", "XPT/USD"),
        _state("Oro", "XAU/USD"),
    ])

    assert "Oro" in message
    assert "Palladio" not in message
    assert "Platino" not in message
