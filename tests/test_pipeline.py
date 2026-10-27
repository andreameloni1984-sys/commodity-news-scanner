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
from engine.regime import apply_regime, _safe_float, _rsi_wilder, _volatility_diagnostics
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
    state.analysis_timestamp = "2026-01-01T02:00:00Z"

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

# ============================================================
# BREAKOUT REJECTION FILTER
# ============================================================


def test_breakout_trigger_rejects_long_upper_wick():
    state = _prepare_directional_state("LONG")
    state.breakout = True
    state.breakout_direction = "LONG"
    state.price = 100.38
    state.breakout_level = 100.20
    state.mtf_data = {
        "5min": [
            {"open": 100.0, "high": 100.2, "low": 99.9, "close": 100.15, "timestamp": "2026-01-01T01:50:00Z"},
            {"open": 100.15, "high": 100.90, "low": 100.10, "close": 100.20, "timestamp": "2026-01-01T01:55:00Z"},
        ]
    }
    apply_setup(state)
    apply_trigger(state)
    assert state.trigger_confirmed is False
    assert state.trigger == "NOT_CONFIRMED"


def test_breakout_trigger_accepts_clean_long_close():
    state = _prepare_directional_state("LONG")
    state.breakout = True
    state.breakout_direction = "LONG"
    state.price = 100.38
    state.breakout_level = 100.20
    state.mtf_data = {
        "5min": [
            {"open": 100.0, "high": 100.2, "low": 99.9, "close": 100.15, "timestamp": "2026-01-01T01:50:00Z"},
            {"open": 100.15, "high": 100.40, "low": 100.10, "close": 100.38, "timestamp": "2026-01-01T01:55:00Z"},
        ]
    }
    apply_setup(state)
    apply_trigger(state)
    assert state.trigger == "BREAKOUT_MOMENTUM"
    assert state.trigger_confirmed is True


# ============================================================
# RETEST FALSIFICATION
# ============================================================

def _prepare_retest_state(direction="LONG", close=100.04):
    state = _prepare_directional_state(direction)
    state.retest = True
    state.retest_direction = direction
    state.retest_level = 100.0
    if direction == "LONG":
        open_price = 99.90
        high = 100.10
        low = 99.90
    else:
        open_price = 100.10
        high = 100.10
        low = 99.80
        close = 99.96
    state.mtf_data = {
        "5min": [
            {"open": open_price - 0.10, "high": open_price, "low": open_price - 0.15, "close": open_price, "timestamp": "2026-01-01T01:50:00Z"},
            {"open": open_price, "high": high, "low": low, "close": close, "timestamp": "2026-01-01T01:55:00Z"},
        ]
    }
    state.price = close
    return state


def test_retest_trigger_requires_current_level_interaction():
    state = _prepare_retest_state("LONG", close=101.0)
    state.mtf_alignment = 50.0
    apply_setup(state)
    apply_trigger(state)
    assert state.trigger == "NOT_CONFIRMED"
    assert state.trigger_confirmed is False


def test_retest_trigger_accepts_current_long_retest():
    state = _prepare_retest_state("LONG", close=100.04)
    apply_setup(state)
    apply_trigger(state)
    assert state.trigger == "RETEST_MOMENTUM"
    assert state.trigger_confirmed is True


def test_retest_trigger_rejects_wrong_side_close():
    state = _prepare_retest_state("LONG", close=99.96)
    apply_setup(state)
    apply_trigger(state)
    assert state.trigger == "NOT_CONFIRMED"
    assert state.trigger_confirmed is False


# ============================================================
# TELEGRAM DASHBOARD CONTRACT
# ============================================================


def test_intraday_dashboard_is_paper_and_compact():
    from telegram.bot import _format_intraday
    state = _prepare_directional_state("LONG")
    state.setup = "TREND_CONTINUATION"
    state.setup_direction = "LONG"
    state.trigger = "NOT_CONFIRMED"
    state.final_decision = "WAIT"
    text = _format_intraday([state])
    assert "INTRADAY" in text
    assert "PAPER ONLY" in text
    assert "TREND_CONTINUATION" in text
    assert "WAIT" in text


def test_buy_board_never_claims_buy_when_no_entry():
    from telegram.bot import _format_buy
    state = _prepare_directional_state("LONG")
    state.final_decision = "WAIT"
    text = _format_buy([state])
    assert "GAGARIN — OGGI" in text
    assert "PAPER ONLY" in text


def test_telegram_dashboard_menu_matches_gagarin_sections():
    from telegram.bot import telegram_menu

    menu = telegram_menu()
    labels = [button["text"] for row in menu["keyboard"] for button in row]

    assert labels == [
        "🚀 AGGRESSIVE 212",
        "🛡 SOFT 212",
        "🔗 COLLEGAMENTO INVEST TRADING212",
    ]
    assert menu["resize_keyboard"] is True
    assert menu["is_persistent"] is True


def test_telegram_start_uses_dashboard_keyboard():
    from telegram.bot import _command_response, telegram_menu

    text = _command_response("/start")
    menu = telegram_menu()

    assert "GAGARIN" in text
    assert "PAPER/DEMO" in text
    assert "🚀 AGGRESSIVE 212" in [
        button["text"] for row in menu["keyboard"] for button in row
    ]



def test_telegram_dashboard_uses_real_line_breaks():
    from telegram.bot import _format_intraday, _format_morning_pick

    assert "\\n" not in _format_intraday([])
    assert "\\n" not in _format_morning_pick([])
    assert "INTRADAY\n" in _format_intraday([])
    assert "GAGARIN — COSA COMPRO?\n" in _format_morning_pick([])

def test_morning_pick_hides_engine_rationale():
    from telegram.bot import _format_morning_pick
    import telegram.bot as bot

    state = _prepare_directional_state("LONG")
    state.symbol = "TEST/USD"
    state.commodity = "Oro"
    state.setup_direction = "LONG"
    state.entry = 100.0
    state.stop = 99.0
    state.tp1 = 101.5
    state.tp2 = 102.0
    state.tp3 = 102.5
    state.rr3 = 2.5

    class Decision:
        symbol = "TEST/USD"
        action = "PAPER_SIGNAL"

    original = bot.evaluate_states
    try:
        bot.evaluate_states = lambda results: [Decision()]
        text = _format_morning_pick([state])
    finally:
        bot.evaluate_states = original

    assert "COMMODITY: Oro" in text
    assert "DIREZIONE: LONG" in text
    assert "ENTRY: 100" in text
    assert "SL: 99" in text
    assert "TP3: 102.5" in text
    assert "Confluence" not in text
    assert "Quality" not in text
    assert "Confidence" not in text
    assert "Analisi fresca" not in text
    assert "PAPER ONLY" in text


def test_cosa_compro_uses_daily_forecast_result(monkeypatch):
    from telegram.bot import _format_buy
    state = _prepare_directional_state("LONG")
    monkeypatch.setattr("telegram.bot.predict_today", lambda results: {
        "commodity": "Oro", "direction": "LONG", "forecast": "SALE",
        "historical_samples": 25, "historical_hit_rate": 68.0,
        "evidence_source": "test", "entry": 100.0, "stop": 98.0,
        "tp1": 103.0, "tp2": 105.0, "median_forward_return_10d": 2.1,
    })
    text = _format_buy([state])
    assert "GAGARIN — OGGI" in text
    assert "Oro" in text
    assert "PREVISIONE: SALE" in text


def test_volatility_diagnostics_detect_expansion_and_contraction():
    from engine.regime import _volatility_diagnostics

    state = _make_state("LONG")
    state.highs = [100.1] * 4 + [101.0] * 4
    state.lows = [99.9] * 4 + [99.0] * 4
    expansion = _volatility_diagnostics(state)
    assert expansion["status"] == "EXPANDING"
    assert expansion["recent_to_older_ratio"] >= 1.25

    state.highs = [101.0] * 4 + [100.1] * 4
    state.lows = [99.0] * 4 + [99.9] * 4
    contraction = _volatility_diagnostics(state)
    assert contraction["status"] == "CONTRACTING"
    assert contraction["recent_to_older_ratio"] <= 0.80


def test_volatility_diagnostics_fail_closed_with_insufficient_data():
    from engine.regime import _volatility_diagnostics

    state = _make_state("LONG")
    state.highs = [101.0, 102.0]
    state.lows = [99.0, 100.0]
    result = _volatility_diagnostics(state)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "INSUFFICIENT_VALID_RANGES"


def test_rsi_wilder_handles_up_down_flat_and_insufficient_series():
    from engine.regime import _rsi_wilder

    assert _rsi_wilder(list(range(15)), 14) == 100.0
    assert _rsi_wilder(list(range(15, 0, -1)), 14) == 0.0
    assert _rsi_wilder([100.0] * 15, 14) == 50.0
    assert _rsi_wilder([1.0, 2.0, 3.0], 14) is None


def test_rsi_wilder_rejects_invalid_values():
    from engine.regime import _rsi_wilder

    assert _rsi_wilder([100.0, "bad", 102.0], 2) is None


# ============================================================
# NON-FINITE NUMERIC INPUTS
# ============================================================


def test_safe_float_rejects_nan_and_infinity():
    import math

    assert _safe_float(float("nan")) is None
    assert _safe_float(float("inf")) is None
    assert _safe_float(float("-inf")) is None
    assert _safe_float("not-a-number") is None
    assert _safe_float("12.5") == 12.5


def test_rsi_wilder_fails_closed_on_non_finite_closes():
    closes = [float(i) for i in range(15)]
    closes[-1] = float("nan")
    assert _rsi_wilder(closes) is None
    closes[-1] = float("inf")
    assert _rsi_wilder(closes) is None


def test_volatility_diagnostics_ignore_non_finite_ranges():
    state = _make_state("LONG")
    state.highs = [float(value) for value in state.highs]
    state.lows = [float(value) for value in state.lows]
    state.highs[-1] = float("nan")
    state.lows[-2] = float("inf")

    result = _volatility_diagnostics(state)

    assert result["samples"] == 8
    assert result["status"] in {"EXPANDING", "CONTRACTING", "STABLE", "UNKNOWN"}


# ============================================================
# RISK ENGINE NUMERIC INTEGRITY
# ============================================================


def test_risk_rejects_non_finite_price_and_atr():
    for direction in ("LONG", "SHORT"):
        for field, value in (
            ("price", float("nan")),
            ("price", float("inf")),
            ("atr", float("nan")),
            ("atr", float("inf")),
            ("atr", 0.0),
        ):
            state = _prepare_directional_state(direction)
            setattr(state, field, value)
            apply_risk(state)
            assert state.entry is None
            assert state.stop is None
            assert state.tp1 is None
            assert state.metadata["risk_diagnostics"]["status"] == "PRECONDITION_FAILED"


def test_risk_ignores_non_finite_structural_swing_and_uses_atr_fallback():
    state = _prepare_directional_state("LONG")
    state.last_swing_low = float("nan")
    apply_setup(state)
    apply_risk(state)

    assert state.entry is not None
    assert state.stop is not None
    assert state.metadata["risk_diagnostics"]["stop_source"] == "ATR_FALLBACK"
    assert state.metadata["risk_diagnostics"]["status"] == "RISK_VALID"


def test_risk_clears_overflowed_target_bracket():
    state = _prepare_directional_state("LONG")
    state.price = 1e308
    state.atr = 1e308
    apply_setup(state)
    apply_risk(state)

    assert state.entry is None
    assert state.stop is None
    assert state.tp1 is None
    assert state.tp2 is None
    assert state.tp3 is None
    assert state.metadata["risk_diagnostics"]["status"] == "NON_FINITE_OR_NON_POSITIVE_BRACKET"



# ============================================================
# LATE BREAKOUT / DIRECTION CONSISTENCY
# ============================================================


def test_breakout_trigger_rejects_late_entry_after_extended_move():
    state = _prepare_directional_state("LONG")
    state.breakout = True
    state.breakout_direction = "LONG"
    state.price = 101.0
    state.breakout_level = 100.20
    state.mtf_data = {
        "5min": [
            {"open": 100.0, "high": 100.2, "low": 99.9, "close": 100.15, "timestamp": "2026-01-01T01:50:00Z"},
            {"open": 100.15, "high": 100.90, "low": 100.10, "close": 100.80, "timestamp": "2026-01-01T01:55:00Z"},
        ]
    }
    apply_setup(state)
    apply_trigger(state)

    assert state.trigger_confirmed is False
    assert state.trigger == "NOT_CONFIRMED"


def test_breakout_trigger_rejects_conflicting_breakout_direction():
    state = _prepare_directional_state("LONG")
    state.breakout = True
    state.breakout_direction = "SHORT"
    state.price = 100.38
    state.breakout_level = 100.20
    state.mtf_data = {
        "5min": [
            {"open": 100.0, "high": 100.2, "low": 99.9, "close": 100.15, "timestamp": "2026-01-01T01:50:00Z"},
            {"open": 100.15, "high": 100.40, "low": 100.10, "close": 100.38, "timestamp": "2026-01-01T01:55:00Z"},
        ]
    }
    apply_setup(state)
    apply_trigger(state)

    assert state.trigger_confirmed is False
    assert state.trigger == "NOT_CONFIRMED"


# SAFETY NUMERIC INTEGRITY / PRICE-DERIVED R:R

def test_safety_blocks_non_finite_numeric_scores_and_rr():
    for field, value in (("probability", float("nan")), ("quality", float("inf")), ("rr3", float("nan"))):
        state = _prepare_directional_state("LONG")
        apply_setup(state)
        apply_risk(state)
        state.trigger_confirmed = True
        state.trigger_direction = "LONG"
        setattr(state, field, value)
        apply_safety(state)
        assert state.safety == "BLOCKED"
        assert state.final_decision == "WAIT"
        assert "NUMERIC_FIELD_NON_FINITE" in state.blockers


def test_safety_recomputes_rr_from_actual_bracket_prices():
    state = _prepare_directional_state("LONG")
    apply_setup(state)
    apply_risk(state)
    state.trigger_confirmed = True
    state.trigger_direction = "LONG"
    state.entry, state.stop = 100.0, 99.0
    state.tp1, state.tp2, state.tp3 = 101.5, 102.0, 102.0
    state.rr1, state.rr2, state.rr3 = 1.5, 2.0, 2.5
    apply_safety(state)
    assert state.safety == "BLOCKED"
    assert "RR_GEOMETRY_MISMATCH" in state.blockers
    assert "RR_FAIL" in state.blockers


def test_rsi_wilder_rejects_fractional_boolean_and_nonfinite_periods():
    for period in (14.5, True, float("nan"), float("inf"), float("-inf"), "bad"):
        assert _rsi_wilder(list(range(20)), period) is None


def test_rsi_wilder_rejects_overflowing_close_changes_and_initial_averages():
    # Finite closes can still overflow when a difference is calculated.
    assert _rsi_wilder([-1e308, 1e308], period=1) is None

    # Each change is finite, but the sum of three positive changes overflows.
    assert _rsi_wilder([-1.4e308, -7e307, 0.0, 7e307], period=3) is None


def test_rsi_wilder_rejects_overflow_during_wilder_recursion():
    # Initial average gain is finite; adding the next gain overflows before division.
    assert _rsi_wilder([-1.6e308, -8e307, 0.0, 1e308], period=2) is None


def test_rsi_wilder_preserves_valid_period_and_reference_cases():
    assert _rsi_wilder(list(range(15)), period=14) == 100.0
    assert _rsi_wilder(list(range(15, 0, -1)), period=14) == 0.0
    assert _rsi_wilder([100.0] * 15, period=14) == 50.0
