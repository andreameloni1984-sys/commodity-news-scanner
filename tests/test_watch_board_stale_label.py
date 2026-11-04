from types import SimpleNamespace

from telegram.signals import format_watch_board


def _state(data_status):
    return SimpleNamespace(
        commodity="Oro",
        setup_direction="LONG",
        pre_move_direction=None,
        opportunity_direction=None,
        final_decision="WATCH",
        safety="BLOCKED",
        blockers=["LIVE_DATA_NOT_FRESH"] if data_status == "STALE" else ["TRIGGER_NOT_CONFIRMED"],
        live=data_status == "LIVE",
        data_ok=data_status == "LIVE",
        price=4050.0,
        atr=2.0,
        probability=60.0,
        quality=40.0,
        confidence=30.0,
        data_age_seconds=601.4 if data_status == "STALE" else 12.0,
        metadata={
            "data_status": data_status,
            "lubjanka_playbook": {
                "status": "CONDITIONAL_PLAN",
                "direction": "SHORT",
                "interceptor": "EARLY_MOVE",
                "activation": "candela M5 chiusa sotto 4039.5",
                "entry_trigger": 4039.5,
                "stop_loss": 4040.8,
                "take_profit_1": 4037.55,
                "take_profit_2": 4036.25,
                "rr_tp1": 1.5,
                "rr_tp2": 2.5,
                "invalidation": "superamento di 4040.8",
                "bar_age_seconds": 601.4 if data_status == "STALE" else 12.0,
            },
        },
    )


def test_stale_quote_is_labeled_without_suppressing_lubjanka_plan():
    message = format_watch_board([_state("STALE")], min_score=999.0)

    assert "QUOTAZIONE STALE (601s)" in message
    assert "piano LUBJANKA mantenuto come osservazione" in message
    assert "LUBJANKA SHORT / EARLY_MOVE" in message
    assert "Entry trigger 4039.5" in message
    assert "Solo monitoraggio. Non è un segnale di entrata." in message


def test_live_quote_does_not_receive_stale_warning():
    message = format_watch_board([_state("LIVE")], min_score=999.0)

    assert "LUBJANKA SHORT / EARLY_MOVE" in message
    assert "QUOTAZIONE STALE" not in message
