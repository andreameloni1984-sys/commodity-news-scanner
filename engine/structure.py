from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.3
# MARKET STRUCTURE ENGINE
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#
# v1.3
# ------------------------------------------------------------
# Migliorie:
#
# - struttura M5 separata dalla conferma MTF
# - MTF calcolato senza perdere informazione parziale
# - direzione strutturale più robusta
# - diagnostica completa
# - swing recenti conservati
# - breakout / retest conservati
#
# NON autorizza ENTRY.
# NON modifica SAFETY.
# ============================================================


SWING_LEFT = 2
SWING_RIGHT = 2

BREAKOUT_ATR_BUFFER = 0.10
RETEST_ATR_TOLERANCE = 0.25

MIN_MTF_BARS = 5

MIN_MTF_ALIGNMENT = 50.0
STRONG_MTF_ALIGNMENT = 75.0


# ============================================================
# SWINGS
# ============================================================


def _find_swing_highs(candles) -> list:

    if len(candles) < (
        SWING_LEFT
        + SWING_RIGHT
        + 1
    ):
        return []

    swings = []

    for index in range(
        SWING_LEFT,
        len(candles) - SWING_RIGHT,
    ):

        current = candles[index]["high"]

        valid = True

        for offset in range(
            1,
            SWING_LEFT + 1,
        ):

            if current <= candles[
                index - offset
            ]["high"]:

                valid = False
                break

        if not valid:
            continue

        for offset in range(
            1,
            SWING_RIGHT + 1,
        ):

            if current <= candles[
                index + offset
            ]["high"]:

                valid = False
                break

        if valid:

            swings.append(
                {
                    "index": index,
                    "price": current,
                    "datetime": candles[
                        index
                    ].get("datetime"),
                }
            )

    return swings


def _find_swing_lows(candles) -> list:

    if len(candles) < (
        SWING_LEFT
        + SWING_RIGHT
        + 1
    ):
        return []

    swings = []

    for index in range(
        SWING_LEFT,
        len(candles) - SWING_RIGHT,
    ):

        current = candles[index]["low"]

        valid = True

        for offset in range(
            1,
            SWING_LEFT + 1,
        ):

            if current >= candles[
                index - offset
            ]["low"]:

                valid = False
                break

        if not valid:
            continue

        for offset in range(
            1,
            SWING_RIGHT + 1,
        ):

            if current >= candles[
                index + offset
            ]["low"]:

                valid = False
                break

        if valid:

            swings.append(
                {
                    "index": index,
                    "price": current,
                    "datetime": candles[
                        index
                    ].get("datetime"),
                }
            )

    return swings


# ============================================================
# STRUCTURE CLASSIFICATION
# ============================================================


def _classify_structure(
    swing_highs,
    swing_lows,
):

    if (
        len(swing_highs) < 2
        or len(swing_lows) < 2
    ):
        return "NONE"

    previous_high = swing_highs[-2]["price"]
    latest_high = swing_highs[-1]["price"]

    previous_low = swing_lows[-2]["price"]
    latest_low = swing_lows[-1]["price"]

    higher_high = latest_high > previous_high
    higher_low = latest_low > previous_low

    lower_high = latest_high < previous_high
    lower_low = latest_low < previous_low

    if higher_high and higher_low:
        return "HH_HL"

    if lower_high and lower_low:
        return "LH_LL"

    if (
        not higher_high
        and not lower_high
        and not higher_low
        and not lower_low
    ):
        return "RANGE"

    return "MIXED"


# ============================================================
# BREAKOUT
# ============================================================


def _detect_breakout(
    candles,
    swing_highs,
    swing_lows,
    direction,
    atr,
):

    if not candles:
        return False, "NONE", None

    if atr is None or atr <= 0:
        return False, "NONE", None

    current_close = candles[-1]["close"]

    buffer = atr * BREAKOUT_ATR_BUFFER

    if (
        direction == "LONG"
        and swing_highs
    ):

        level = swing_highs[-1]["price"]

        if current_close > level + buffer:

            return (
                True,
                "LONG",
                level,
            )

    if (
        direction == "SHORT"
        and swing_lows
    ):

        level = swing_lows[-1]["price"]

        if current_close < level - buffer:

            return (
                True,
                "SHORT",
                level,
            )

    return False, "NONE", None


# ============================================================
# RETEST
# ============================================================


def _detect_retest(
    candles,
    breakout,
    breakout_direction,
    breakout_level,
    atr,
):

    if not breakout:
        return False, "NONE", None

    if breakout_level is None:
        return False, "NONE", None

    if atr is None or atr <= 0:
        return False, "NONE", None

    if len(candles) < 2:
        return False, "NONE", None

    tolerance = atr * RETEST_ATR_TOLERANCE

    recent = candles[-3:]

    for candle in recent:

        close = candle["close"]
        high = candle["high"]
        low = candle["low"]

        if breakout_direction == "LONG":

            touched = (
                low <= breakout_level + tolerance
                and high >= breakout_level - tolerance
            )

            held = close > breakout_level

            if touched and held:

                return (
                    True,
                    "LONG",
                    breakout_level,
                )

        elif breakout_direction == "SHORT":

            touched = (
                high >= breakout_level - tolerance
                and low <= breakout_level + tolerance
            )

            held = close < breakout_level

            if touched and held:

                return (
                    True,
                    "SHORT",
                    breakout_level,
                )

    return False, "NONE", None


# ============================================================
# TIMEFRAME ANALYSIS
# ============================================================


def _analyze_timeframe(
    candles,
    atr,
):

    empty = {
        "structure": "NONE",
        "direction": "NONE",
        "swing_highs": [],
        "swing_lows": [],
        "breakout": False,
        "breakout_direction": "NONE",
        "breakout_level": None,
        "retest": False,
        "retest_direction": "NONE",
        "retest_level": None,
    }

    if (
        not candles
        or len(candles) < MIN_MTF_BARS
    ):
        return empty

    try:

        swing_highs = _find_swing_highs(
            candles
        )

        swing_lows = _find_swing_lows(
            candles
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return empty

    pattern = _classify_structure(
        swing_highs,
        swing_lows,
    )

    if pattern == "HH_HL":

        direction = "LONG"

    elif pattern == "LH_LL":

        direction = "SHORT"

    else:

        direction = "NONE"

    (
        breakout,
        breakout_direction,
        breakout_level,
    ) = _detect_breakout(
        candles,
        swing_highs,
        swing_lows,
        direction,
        atr,
    )

    (
        retest,
        retest_direction,
        retest_level,
    ) = _detect_retest(
        candles,
        breakout,
        breakout_direction,
        breakout_level,
        atr,
    )

    return {
        "structure": pattern,
        "direction": direction,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "breakout": breakout,
        "breakout_direction": breakout_direction,
        "breakout_level": breakout_level,
        "retest": retest,
        "retest_direction": retest_direction,
        "retest_level": retest_level,
    }


# ============================================================
# MTF ALIGNMENT
# ============================================================


def _calculate_mtf_alignment(
    analyses,
):

    directions = []

    for timeframe in (
        "5min",
        "15min",
        "30min",
        "1h",
    ):

        analysis = analyses.get(
            timeframe,
            {},
        )

        direction = analysis.get(
            "direction",
            "NONE",
        )

        if direction in {
            "LONG",
            "SHORT",
        }:

            directions.append(direction)

    if not directions:

        return "NONE", 0.0

    long_count = directions.count("LONG")
    short_count = directions.count("SHORT")

    total = len(directions)

    if long_count > short_count:

        return (
            "LONG",
            long_count / total * 100.0,
        )

    if short_count > long_count:

        return (
            "SHORT",
            short_count / total * 100.0,
        )

    return "NONE", 0.0


# ============================================================
# MAIN
# ============================================================


def apply_structure(
    state: SoyuzState,
) -> SoyuzState:

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    state.structure = "UNCONFIRMED"
    state.structure_direction = "NONE"
    state.structure_pattern = "NONE"

    state.swing_highs = []
    state.swing_lows = []

    state.last_swing_high = None
    state.last_swing_low = None

    state.previous_swing_high = None
    state.previous_swing_low = None

    state.breakout = False
    state.breakout_direction = "NONE"
    state.breakout_level = None

    state.retest = False
    state.retest_direction = "NONE"
    state.retest_level = None

    state.mtf_structure = "UNCONFIRMED"
    state.mtf_direction = "NONE"
    state.mtf_alignment = 0.0

    state.metadata.pop(
        "structure_diagnostics",
        None,
    )

    # --------------------------------------------------------
    # DATA GATE
    # --------------------------------------------------------

    if not state.data_ok:

        return state

    if not state.mtf_data:

        return state

    # --------------------------------------------------------
    # ANALISI MTF
    # --------------------------------------------------------

    analyses = {}

    for timeframe in (
        "5min",
        "15min",
        "30min",
        "1h",
    ):

        candles = state.mtf_data.get(
            timeframe,
            [],
        )

        analyses[timeframe] = (
            _analyze_timeframe(
                candles,
                state.atr,
            )
        )

    # --------------------------------------------------------
    # M5 PRIMARY
    # --------------------------------------------------------

    primary = analyses.get(
        "5min",
        {},
    )

    state.structure_pattern = (
        primary.get(
            "structure",
            "NONE",
        )
    )

    state.swing_highs = primary.get(
        "swing_highs",
        [],
    )

    state.swing_lows = primary.get(
        "swing_lows",
        [],
    )

    if state.swing_highs:

        state.last_swing_high = (
            state.swing_highs[-1]["price"]
        )

        if len(state.swing_highs) >= 2:

            state.previous_swing_high = (
                state.swing_highs[-2]["price"]
            )

    if state.swing_lows:

        state.last_swing_low = (
            state.swing_lows[-1]["price"]
        )

        if len(state.swing_lows) >= 2:

            state.previous_swing_low = (
                state.swing_lows[-2]["price"]
            )

    primary_direction = primary.get(
        "direction",
        "NONE",
    )

    # --------------------------------------------------------
    # MTF
    # --------------------------------------------------------

    (
        mtf_direction,
        mtf_alignment,
    ) = _calculate_mtf_alignment(
        analyses
    )

    state.mtf_direction = mtf_direction
    state.mtf_alignment = mtf_alignment

    if mtf_alignment >= STRONG_MTF_ALIGNMENT:

        if mtf_direction == "LONG":
            state.mtf_structure = "BULLISH"

        elif mtf_direction == "SHORT":
            state.mtf_structure = "BEARISH"

    elif mtf_alignment >= MIN_MTF_ALIGNMENT:

        state.mtf_structure = "PARTIAL"

    else:

        state.mtf_structure = "UNCONFIRMED"

    # --------------------------------------------------------
    # STRUTTURA PRIMARIA
    # --------------------------------------------------------

    if primary_direction == "LONG":

        state.structure = "BULLISH"

    elif primary_direction == "SHORT":

        state.structure = "BEARISH"

    elif state.structure_pattern == "RANGE":

        state.structure = "RANGE"

    else:

        state.structure = "UNCONFIRMED"

    # --------------------------------------------------------
    # DIREZIONE OPERATIVA STRUTTURALE
    # --------------------------------------------------------
    #
    # Qui NON richiediamo più che il regime sia perfettamente
    # sincronizzato con M5 nello stesso istante.
    #
    # La direzione nasce dalla struttura M5 + conferma MTF.
    # Il SETUP continuerà comunque a richiedere il regime.
    #
    # Questo evita che un singolo cambio di regime cancelli
    # una struttura reale appena formata.
    # --------------------------------------------------------

    if (
        primary_direction == "LONG"
        and (
            mtf_direction == "LONG"
            or mtf_alignment >= 50.0
        )
    ):

        state.structure_direction = "LONG"

    elif (
        primary_direction == "SHORT"
        and (
            mtf_direction == "SHORT"
            or mtf_alignment >= 50.0
        )
    ):

        state.structure_direction = "SHORT"

    elif (
        primary_direction == "LONG"
        and state.regime == "TREND_UP"
    ):

        state.structure_direction = "LONG"

    elif (
        primary_direction == "SHORT"
        and state.regime == "TREND_DOWN"
    ):

        state.structure_direction = "SHORT"

    else:

        state.structure_direction = "NONE"

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    state.breakout = primary.get(
        "breakout",
        False,
    )

    state.breakout_direction = (
        primary.get(
            "breakout_direction",
            "NONE",
        )
    )

    state.breakout_level = (
        primary.get(
            "breakout_level",
            None,
        )
    )

    # --------------------------------------------------------
    # RETEST
    # --------------------------------------------------------

    state.retest = primary.get(
        "retest",
        False,
    )

    state.retest_direction = (
        primary.get(
            "retest_direction",
            "NONE",
        )
    )

    state.retest_level = (
        primary.get(
            "retest_level",
            None,
        )
    )

    # --------------------------------------------------------
    # DIAGNOSTICA
    # --------------------------------------------------------

    state.metadata[
        "structure_diagnostics"
    ] = {

        "primary_timeframe": "5min",

        "primary_structure": (
            state.structure_pattern
        ),

        "primary_direction": (
            primary_direction
        ),

        "structure": (
            state.structure
        ),

        "structure_direction": (
            state.structure_direction
        ),

        "regime": (
            state.regime
        ),

        "mtf_direction": (
            state.mtf_direction
        ),

        "mtf_alignment": (
            state.mtf_alignment
        ),

        "mtf_structure": (
            state.mtf_structure
        ),

        "m5_swing_highs": len(
            state.swing_highs
        ),

        "m5_swing_lows": len(
            state.swing_lows
        ),

        "last_swing_high": (
            state.last_swing_high
        ),

        "last_swing_low": (
            state.last_swing_low
        ),

        "breakout": (
            state.breakout
        ),

        "breakout_direction": (
            state.breakout_direction
        ),

        "breakout_level": (
            state.breakout_level
        ),

        "retest": (
            state.retest
        ),

        "retest_direction": (
            state.retest_direction
        ),

        "retest_level": (
            state.retest_level
        ),

        "timeframes": {

            timeframe: {

                "structure": analysis.get(
                    "structure",
                    "NONE",
                ),

                "direction": analysis.get(
                    "direction",
                    "NONE",
                ),

                "swing_highs": len(
                    analysis.get(
                        "swing_highs",
                        [],
                    )
                ),

                "swing_lows": len(
                    analysis.get(
                        "swing_lows",
                        [],
                    )
                ),

            }

            for timeframe, analysis
            in analyses.items()
        },
    }

    return state