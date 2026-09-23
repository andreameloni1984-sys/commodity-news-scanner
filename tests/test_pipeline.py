from commodities.universe import COMMODITIES
from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# BASIC PIPELINE TEST
# ============================================================


def test_single_state_schema():
    """
    Verifica che il motore utilizzi un singolo stato canonico.
    """

    commodity = COMMODITIES[0]

    state = SoyuzState(
        commodity.name,
        commodity.symbol,
    )

    assert state.final_decision in {
        "ENTRY",
        "WAIT",
    }

    assert state.safety in {
        "SAFE",
        "BLOCKED",
    }

    assert isinstance(
        state.blockers,
        list,
    )