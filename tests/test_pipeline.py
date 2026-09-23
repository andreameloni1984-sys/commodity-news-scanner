# ============================================================
# SOYUZ GAGARIN v1.2
# PIPELINE TESTS
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#   ↓
# SETUP
#   ↓
# TRIGGER
#   ↓
# RISK
#   ↓
# SAFETY
#
# Test deterministici.
# Nessuna API esterna.
# Nessun Twelve Data.
# Nessun Telegram.
#
# ============================================================

from engine.state import SoyuzState
from engine.regime import apply_regime
from engine.structure import apply_structure
from engine.setup import apply_setup
from engine.trigger import apply_trigger
from engine.risk import apply_risk
from engine.safety import apply_safety


# ============================================================
# HELPERS
# ============================================================


def _make_candles(direction="LONG", count=80):
    """
    Crea una serie OHLC deterministica.

    Non rappresenta dati reali di mercato.
    Serve esclusivamente per i test della pipeline.
    """

    opens = []
    highs = []
    lows = []
    closes = []
    timestamps = []

    price = 100.0

    for i in range(count):

        if direction == "LONG":
            open_price = price
            close_price = price + 0.20

            high_price = close_price + 0.10
            low_price = open_price - 0.05

            price = close_price

        else:
            open_price = price
            close_price = price - 0.20

            high_price = open_price + 0.05
            low_price = close_price - 0.10

            price = close_price

        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        timestamps.append(f"2026-01-01T00:{i:02d}:00Z")

    return {
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "timestamps": timestamps,
    }


def _make_state(direction="LONG"):
    """
    Costruisce uno stato deterministico già alimentato
    con dati OHLC.
    """

    candles = _make_candles(direction)

    state = SoyuzState(
        commodity="TEST",
        symbol="TEST/USD",
    )

    state.opens = candles["opens"]
    state.highs = candles["highs"]
    state.lows = candles["lows"]
    state.closes = candles["closes"]
    state.timestamps = candles["timestamps"]

    state.price = candles["closes"][-1]
    state.previous_price = candles["closes"][-2]

    # ATR deterministico.
    state.atr = 0.35

    state.data_ok = True
    state.live = True
    state.data_age_seconds = 30.0
    state.data_source = "TEST"

    state.timeframe = "5min"

    return state


def _prepare_directional_state(direction="LONG"):
    """
    Prepara manualmente uno stato coerente con la parte
    successiva della pipeline.

    In questo modo i test delle singole fasi non dipendono
    da dati esterni.
    """

    state = _make_state(direction)

    state.regime = (
        "TREND_UP"
        if direction == "LONG"
        else "TREND_DOWN"
    )

    state.structure = (
        "BULLISH"
        if direction == "LONG"
        else "BEARISH"
    )

    state.structure_direction = direction

    state.structure_pattern = (
        "HH_HL"
        if direction == "LONG"
        else "LH_LL"
    )

    state.mtf_structure = (
        "BULLISH"
        if direction == "LONG"
        else "BEARISH"
    )

    state.mtf_direction = direction
    state.mtf_alignment = 100.0

    state.breakout = False
    state.breakout_direction = "NONE"

    state.retest = False
    state.retest_direction = "NONE"

    return state


# ============================================================
# DATA / REGIME
# ============================================================


def test_regime_long():
    state = _make_state("LONG")

    apply_regime(state)

    assert state.data_ok is True
    assert state.regime in {
        "TREND_UP",
        "RANGE",
        "HIGH_VOLATILITY",
    }


def test_regime_short():
    state = _make_state("SHORT")

    apply_regime(state)

    assert state.data_ok is True
    assert state.regime in {
        "TREND_DOWN",
        "RANGE",
        "HIGH_VOLATILITY",
    }


# ============================================================
# SETUP
# ============================================================


def test_setup_long():
    state = _prepare_directional_state("LONG")

    apply_setup(state)

    assert state.setup == "TREND_CONTINUATION"
    assert state.setup_direction == "LONG"
    assert state.setup_quality > 0


def test_setup_short():
    state = _prepare_directional_state("SHORT")

    apply_setup(state)

    assert state.setup == "TREND_CONTINUATION"
    assert state.setup_direction == "SHORT"
    assert state.setup_quality > 0


def test_setup_blocked_without_mtf():
    state = _prepare_directional_state("LONG")

    state.mtf_alignment = 0.0

    apply_setup(state)

    assert state.setup == "NONE"
    assert state.setup_direction == "NONE"
    assert state.setup_quality == 0.0


# ============================================================
# TRIGGER
# ============================================================


def test_trigger_long():
    state = _prepare_directional_state("LONG")

    apply_setup(state)

    assert state.setup_direction == "LONG"

    # Trigger deterministico:
    # forte momentum sull'ultima candela.
    apply_trigger(state)

    assert state.trigger_direction in {
        "LONG",
        "NONE",
    }


def test_trigger_short():
    state = _prepare_directional_state("SHORT")

    apply_setup(state)

    assert state.setup_direction == "SHORT"

    apply_trigger(state)

    assert state.trigger_direction in {
        "SHORT",
        "NONE",
    }


def test_trigger_blocked_without_live_data():
    state = _prepare_directional_state("LONG")

    state.live = False

    apply_setup(state)
    apply_trigger(state)

    assert state.trigger_confirmed is False


# ============================================================
# RISK
# ============================================================


def test_risk_long():
    state = _prepare_directional_state("LONG")

    apply_setup(state)
    apply_risk(state)

    assert state.entry is not None
    assert state.stop is not None
    assert state.tp1 is not None
    assert state.tp2 is not None
    assert state.tp3 is not None

    assert state.stop < state.entry
    assert state.tp1 > state.entry
    assert state.tp2 > state.tp1
    assert state.tp3 > state.tp2


def test_risk_short():
    state = _prepare_directional_state("SHORT")

    apply_setup(state)
    apply_risk(state)

    assert state.entry is not None
    assert state.stop is not None
    assert state.tp1 is not None
    assert state.tp2 is not None
    assert state.tp3 is not None

    assert state.stop > state.entry
    assert state.tp1 < state.entry
    assert state.tp2 < state.tp1
    assert state.tp3 < state.tp2


# ============================================================
# SAFETY
# ============================================================


def test_safety_blocks_missing_trigger():
    state = _prepare_directional_state("LONG")

    apply_setup(state)
    apply_risk(state)

    state.trigger_confirmed = False

    apply_safety(state)

    assert state.safety == "BLOCKED"
    assert state.final_decision == "WAIT"
    assert "TRIGGER_NOT_CONFIRMED" in state.blockers


def test_safety_blocks_bad_rr():
    state = _prepare_directional_state("LONG")

    apply_setup(state)
    apply_risk(state)

    state.trigger_confirmed = True
    state.rr3 = 1.0

    apply_safety(state)

    assert state.safety == "BLOCKED"
    assert state.final_decision == "WAIT"


# ============================================================
# COMPLETE PIPELINE
# ============================================================


def test_complete_pipeline_long():
    state = _prepare_directional_state("LONG")

    apply_regime(state)
    apply_structure(state)
    apply_setup(state)
    apply_trigger(state)
    apply_risk(state)
    apply_safety(state)

    assert state.data_ok is True
    assert state.setup_direction in {
        "LONG",
        "NONE",
    }

    assert state.final_decision in {
        "WAIT",
        "ENTRY",
    }


def test_complete_pipeline_short():
    state = _prepare_directional_state("SHORT")

    apply_regime(state)
    apply_structure(state)
    apply_setup(state)
    apply_trigger(state)
    apply_risk(state)
    apply_safety(state)

    assert state.data_ok is True
    assert state.setup_direction in {
        "SHORT",
        "NONE",
    }

    assert state.final_decision in {
        "WAIT",
        "ENTRY",
    }


# ============================================================
# DATA GATE
# ============================================================


def test_setup_blocked_when_data_invalid():
    state = _make_state("LONG")

    state.data_ok = False

    apply_setup(state)

    assert state.setup == "NONE"
    assert state.setup_direction == "NONE"
    assert state.setup_quality == 0.0


def test_trigger_blocked_when_data_invalid():
    state = _prepare_directional_state("LONG")

    state.data_ok = False

    apply_setup(state)
    apply_trigger(state)

    assert state.trigger_confirmed is False


def test_risk_blocked_when_data_invalid():
    state = _prepare_directional_state("LONG")

    state.data_ok = False

    apply_setup(state)
    apply_risk(state)

    assert state.entry is None
    assert state.stop is None
    assert state.tp1 is None
    assert state.tp2 is None
    assert state.tp3 is None