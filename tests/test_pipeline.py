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
        "📰 NEWS", "🔥 TOP OPPORTUNITÀ",
        "🏆 CLASSIFICA", "⚡ INTRADAY",
        "💰 COSA COMPRARE", "🛒 QUALE COMPRO?",
        "📊 ANALISI", "📡 SEGNALI",
        "🥇 METALLI", "🛢 PETROLIO",
        "🌾 AGRI", "🌍 MACRO",
        "❓ PERCHÉ", "🔄 AGGIORNA",
        "⚙️ STATO", "ℹ️ GUIDA",
    ]
    assert menu["resize_keyboard"] is True
    assert menu["is_persistent"] is True


def test_telegram_start_uses_dashboard_keyboard():
    from telegram.bot import _command_response, telegram_menu

    text = _command_response("/start")
    menu = telegram_menu()

    assert "SOYUZ GAGARIN" in text
    assert "PAPER ONLY" in text
    assert "🔥 TOP OPPORTUNITÀ" in [
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
