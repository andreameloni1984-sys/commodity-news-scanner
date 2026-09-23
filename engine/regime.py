from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.0
# REGIME ENGINE
# ============================================================
#
# Responsabilità:
#
# DATA → REGIME
#
# Il modulo identifica il regime di mercato di base.
#
# Possibili stati:
#
# TREND_UP
# TREND_DOWN
# HIGH_VOLATILITY
# RANGE
# UNKNOWN
#
# NON decide ENTRY.
# NON decide LONG/SHORT operativo.
# NON modifica SETUP, TRIGGER o SAFETY.
#
# Aggiorna esclusivamente lo SoyuzState ricevuto.
# ============================================================


def apply_regime(state: SoyuzState) -> SoyuzState:
    """
    Determina il regime corrente utilizzando i dati
    già presenti nello stato canonico.

    Nessun nuovo SoyuzState viene creato.
    """

    # --------------------------------------------------------
    # VALIDAZIONE DATI
    # --------------------------------------------------------

    if (
        not state.data_ok
        or state.price is None
        or state.previous_price is None
    ):

        state.regime = "UNKNOWN"

        return state

    # --------------------------------------------------------
    # MOVIMENTO CORRENTE
    # --------------------------------------------------------

    change = (
        state.price
        - state.previous_price
    )

    # --------------------------------------------------------
    # HIGH VOLATILITY
    # --------------------------------------------------------

    if (
        state.atr is not None
        and state.atr > 0
        and abs(change)
        > state.atr * 1.8
    ):

        state.regime = "HIGH_VOLATILITY"

        return state

    # --------------------------------------------------------
    # TREND UP
    # --------------------------------------------------------

    if change > 0:

        state.regime = "TREND_UP"

        return state

    # --------------------------------------------------------
    # TREND DOWN
    # --------------------------------------------------------

    if change < 0:

        state.regime = "TREND_DOWN"

        return state

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    state.regime = "RANGE"

    return state