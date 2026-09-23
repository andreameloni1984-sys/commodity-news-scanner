from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.2
# MARKET STRUCTURE ENGINE
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#
# Questa versione utilizza le candele realmente presenti
# nello SoyuzState.
#
# FUNZIONI:
#
# - swing high / swing low
# - HH / HL
# - LH / LL
# - breakout
# - retest
# - struttura MTF
# - allineamento M5 / M15 / M30 / H1
#
# NON decide ENTRY.
# NON decide LONG/SHORT operativo da solo.
# NON modifica SAFETY.
# ============================================================


# ============================================================
# PARAMETRI
# ============================================================

SWING_LEFT = 2
SWING_RIGHT = 2

BREAKOUT_ATR_BUFFER = 0.10
RETEST_ATR_TOLERANCE = 0.25

MIN_MTF_BARS = 5


# ============================================================
# GENERIC SWING DETECTION
# ============================================================


def _find_swing_highs(
    candles,
) -> list:
    """
    Individua swing high locali.

    Una candela è swing high se il suo massimo è superiore
    ai massimi delle candele vicine.
    """

    if len(candles) < (
        SWING_LEFT
        + SWING_RIGHT
        + 1
    ):
        return []

    swings = []

    start = SWING_LEFT

    end = (
        len(candles)
        - SWING_RIGHT
    )

    for index in range(
        start,
        end,
    ):

        current_high = candles[index][
            "high"
        ]

        is_swing = True

        for offset in range(
            1,
            SWING_LEFT + 1,
        ):

            if current_high <= candles[
                index - offset
            ]["high"]:

                is_swing = False

                break

        if not is_swing:
            continue

        for offset in range(
            1,
            SWING_RIGHT + 1,
        ):

            if current_high <= candles[
                index + offset
            ]["high"]:

                is_swing = False

                break

        if is_swing:

            swings.append(
                {
                    "index": index,
                    "price": current_high,
                    "datetime": candles[
                        index
                    ].get("datetime"),
                }
            )

    return swings


def _find_swing_lows(
    candles,
) -> list:
    """
    Individua swing low locali.
    """

    if len(candles) < (
        SWING_LEFT
        + SWING_RIGHT
        + 1
    ):
        return []

    swings = []

    start = SWING_LEFT

    end = (
        len(candles)
        - SWING_RIGHT
    )

    for index in range(
        start,
        end,
    ):

        current_low = candles[index][
            "low"
        ]

        is_swing = True

        for offset in range(
            1,
            SWING_LEFT + 1,
        ):

            if current_low >= candles[
                index - offset
            ]["low"]:

                is_swing = False

                break

        if not is_swing:
            continue

        for offset in range(
            1,
            SWING_RIGHT + 1,
        ):

            if current_low >= candles[
                index + offset
            ]["low"]:

                is_swing = False

                break

        if is_swing:

            swings.append(
                {
                    "index": index,
                    "price": current_low,
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
    """
    Classifica la struttura usando gli ultimi due swing
    dello stesso tipo.

    Possibili risultati:

        HH_HL
        LH_LL
        MIXED
        RANGE
        NONE
    """

    if (
        len(swing_highs) < 2
        or len(swing_lows) < 2
    ):
        return "NONE"

    previous_high = swing_highs[-2][
        "price"
    ]

    latest_high = swing_highs[-1][
        "price"
    ]

    previous_low = swing_lows[-2][
        "price"
    ]

    latest_low = swing_lows[-1][
        "price"
    ]

    higher_high = (
        latest_high
        > previous_high
    )

    higher_low = (
        latest_low
        > previous_low
    )

    lower_high = (
        latest_high
        < previous_high
    )

    lower_low = (
        latest_low
        < previous_low
    )

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
    """
    Determina se il prezzo corrente ha superato
    l'ultimo swing rilevante.

    Richiede un piccolo buffer ATR per evitare che
    un semplice tocco venga classificato come breakout.
    """

    if not candles:
        return False, "NONE", None

    if atr is None or atr <= 0:
        return False, "NONE", None

    current_close = candles[-1][
        "close"
    ]

    buffer = (
        atr
        * BREAKOUT_ATR_BUFFER
    )

    if (
        direction == "LONG"
        and swing_highs
    ):

        level = swing_highs[-1][
            "price"
        ]

        if current_close > (
            level + buffer
        ):

            return (
                True,
                "LONG",
                level,
            )

    if (
        direction == "SHORT"
        and swing_lows
    ):

        level = swing_lows[-1][
            "price"
        ]

        if current_close < (
            level - buffer
        ):

            return (
                True,
                "SHORT",
                level,
            )

    return (
        False,
        "NONE",
        None,
    )


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
    """
    Cerca un retest del livello di breakout.

    Il retest viene considerato valido quando una delle
    ultime candele torna entro una tolleranza ATR dal livello
    e chiude nuovamente nella direzione del breakout.
    """

    if not breakout:
        return False, "NONE", None

    if breakout_level is None:
        return False, "NONE", None

    if atr is None or atr <= 0:
        return False, "NONE", None

    if len(candles) < 2:
        return False, "NONE", None

    tolerance = (
        atr
        * RETEST_ATR_TOLERANCE
    )

    recent = candles[-3:]

    for candle in recent:

        close = candle["close"]

        high = candle["high"]

        low = candle["low"]

        if breakout_direction == "LONG":

            touched = (
                low
                <= breakout_level
                + tolerance
                and high
                >= breakout_level
                - tolerance
            )

            held = (
                close
                > breakout_level
            )

            if touched and held:

                return (
                    True,
                    "LONG",
                    breakout_level,
                )

        if breakout_direction == "SHORT":

            touched = (
                high
                >= breakout_level
                - tolerance
                and low
                <= breakout_level
                + tolerance
            )

            held = (
                close
                < breakout_level
            )

            if touched and held:

                return (
                    True,
                    "SHORT",
                    breakout_level,
                )

    return (
        False,
        "NONE",
        None,
    )


# ============================================================
# SINGLE TIMEFRAME ANALYSIS
# ============================================================


def _analyze_timeframe(
    candles,
    atr,
):
    """
    Analizza un singolo timeframe.
    """

    if (
        not candles
        or len(candles) < MIN_MTF_BARS
    ):

        return {
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

    swing_highs = _find_swing_highs(
        candles
    )

    swing_lows = _find_swing_lows(
        candles
    )

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
    """
    Calcola l'allineamento tra:

        M5
        M15
        M30
        H1

    Restituisce:

        direction
        score
    """

    directions = []

    for timeframe in (
        "5min",
        "15min",
        "30min",
        "1h",
    ):

        analysis = analyses.get(
            timeframe
        )

        if not analysis:
            continue

        direction = analysis.get(
            "direction",
            "NONE",
        )

        if direction in {
            "LONG",
            "SHORT",
        }:

            directions.append(
                direction
            )

    if not directions:

        return (
            "NONE",
            0.0,
        )

    long_count = directions.count(
        "LONG"
    )

    short_count = directions.count(
        "SHORT"
    )

    total = len(directions)

    if long_count > short_count:

        return (
            "LONG",
            (
                long_count
                / total
            )
            * 100.0,
        )

    if short_count > long_count:

        return (
            "SHORT",
            (
                short_count
                / total
            )
            * 100.0,
        )

    return (
        "NONE",
        0.0,
    )


# ============================================================
# MAIN STRUCTURE ENGINE
# ============================================================


def apply_structure(
    state: SoyuzState,
) -> SoyuzState:
    """
    Costruisce la struttura reale usando le candele
    disponibili nello SoyuzState.

    Non crea un secondo stato.
    """

    # ========================================================
    # RESET
    # ========================================================

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

    # ========================================================
    # DATA VALIDATION
    # ========================================================

    if not state.data_ok:

        return state

    if not state.mtf_data:

        return state

    # ========================================================
    # ANALYZE ALL TIMEFRAMES
    # ========================================================

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

    # ========================================================
    # PRIMARY M5 STRUCTURE
    # ========================================================

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
            state.swing_highs[-1][
                "price"
            ]
        )

        if len(
            state.swing_highs
        ) >= 2:

            state.previous_swing_high = (
                state.swing_highs[-2][
                    "price"
                ]
            )

    if state.swing_lows:

        state.last_swing_low = (
            state.swing_lows[-1][
                "price"
            ]
        )

        if len(
            state.swing_lows
        ) >= 2:

            state.previous_swing_low = (
                state.swing_lows[-2][
                    "price"
                ]
            )

    # ========================================================
    # PRIMARY DIRECTION
    # ========================================================

    primary_direction = primary.get(
        "direction",
        "NONE",
    )

    # ========================================================
    # MTF ALIGNMENT
    # ========================================================

    (
        mtf_direction,
        mtf_alignment,
    ) = _calculate_mtf_alignment(
        analyses
    )

    state.mtf_direction = (
        mtf_direction
    )

    state.mtf_alignment = (
        mtf_alignment
    )

    # ========================================================
    # MTF STRUCTURE
    # ========================================================

    if mtf_alignment >= 75.0:

        if mtf_direction == "LONG":

            state.mtf_structure = (
                "BULLISH"
            )

        elif mtf_direction == "SHORT":

            state.mtf_structure = (
                "BEARISH"
            )

    elif mtf_alignment >= 50.0:

        state.mtf_structure = (
            "PARTIAL"
        )

    else:

        state.mtf_structure = (
            "UNCONFIRMED"
        )

    # ========================================================
    # FINAL STRUCTURE DIRECTION
    # ========================================================
    #
    # La direzione non viene assegnata soltanto perché M5
    # è positivo/negativo.
    #
    # Richiediamo coerenza tra regime, struttura primaria
    # e almeno una conferma MTF.
    # ========================================================

    if (
        state.regime == "TREND_UP"
        and primary_direction == "LONG"
        and mtf_direction == "LONG"
        and mtf_alignment >= 50.0
    ):

        state.structure = "BULLISH"

        state.structure_direction = "LONG"

    elif (
        state.regime == "TREND_DOWN"
        and primary_direction == "SHORT"
        and mtf_direction == "SHORT"
        and mtf_alignment >= 50.0
    ):

        state.structure = "BEARISH"

        state.structure_direction = "SHORT"

    elif (
        state.structure_pattern
        == "HH_HL"
    ):

        state.structure = "BULLISH"

        state.structure_direction = "LONG"

    elif (
        state.structure_pattern
        == "LH_LL"
    ):

        state.structure = "BEARISH"

        state.structure_direction = "SHORT"

    elif (
        state.structure_pattern
        == "RANGE"
    ):

        state.structure = "RANGE"

        state.structure_direction = "NONE"

    else:

        state.structure = (
            "UNCONFIRMED"
        )

        state.structure_direction = (
            "NONE"
        )

    # ========================================================
    # BREAKOUT / RETEST
    # ========================================================

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
            "breakout_level"
        )
    )

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
            "retest_level"
        )
    )

    return state