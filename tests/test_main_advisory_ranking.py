from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

from main import _print_ranking


def test_main_ranking_displays_separate_paper_early_warning_advisory():
    state = SimpleNamespace(
        commodity="Brent", symbol="UKOIL", setup_direction="LONG",
        structure_direction="LONG", mtf_direction="LONG", opportunity_direction="LONG",
        pre_move_direction="LONG", pre_move_score=70, opportunity_score=60,
        continuation_score=65, expected_move_pct=1.2, probability=70,
        quality=75, confidence=70, price=80.0, atr=0.8, data_ok=True,
        live=True, regime="TREND_UP", structure="BULLISH",
        trigger_confirmed=False, final_decision="WAIT", blockers=["TRIGGER_NOT_CONFIRMED"],
        metadata={"data_status": "OK", "early_warning": {
            "direction": "LONG", "score": 72.0, "stage": "WATCH",
        }},
    )
    output = StringIO()
    with redirect_stdout(output):
        _print_ranking([state])
    rendered = output.getvalue()
    assert "RANKING PREDITTIVO PAPER (ADVISORY, NON OPERATIVO)" in rendered
    assert "Brent" in rendered
    assert "early=LONG" in rendered
    assert "non probabilità calibrata" in rendered
