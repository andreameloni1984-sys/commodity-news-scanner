from engine.state import SoyuzState


# ============================================================
# SOYUZ GAGARIN v1.1
# REGIME ENGINE
# ============================================================
#
# DATA → REGIME
#
# Stati possibili:
#
# TREND_UP
# TREND_DOWN
# HIGH_VOLATILITY
# RANGE
# UNKNOWN
#
# PRINCIPIO:
#
# Un semplice tick positivo NON è un trend.
# Un semplice tick negativo NON è un trend.
#
# Il movimento viene normalizzato rispetto all'ATR.
#
# change / ATR = intensità relativa del movimento
#
# NON decide ENTRY.
# NON decide LONG/SHORT operativo.
# NON modifica SETUP, TRIGGER o SAFETY.
#
# Aggiorna esclusivamente lo SoyuzState ricevuto.
# ============================================================


# ------------------------------------------------------------
# SOGLIE REGIME
# ------------------------------------------------------------

# Movimento inferiore a questa frazione dell'ATR:
# considerato rumore/range.
MIN_TREND_MOVE_ATR = 0.20

# Sopra questa soglia il movimento viene considerato
# direzionale.
STRONG_TREND_MOVE_ATR = 0.35

# Movimento estremamente ampio rispetto all'ATR:
# HIGH_VOLATILITY.
HIGH_VOLATILITY_ATR = 1.80


def apply_regime(
    state: SoyuzState,
) -> SoyuzState:
    """
    Determina il regime corrente usando:

    - prezzo corrente
    - prezzo precedente
    - ATR

    Il regime NON è una previsione.

    È una classificazione del comportamento corrente
    del mercato.

    Nessun nuovo SoyuzState viene creato.
    """

    # ========================================================
    # 1. VALIDAZIONE DATI
    # ========================================================

    if (
        not state.data_ok
        or state.price is None
        or state.previous_price is None
        or state.atr is None
        or state.atr <= 0
    ):

        state.regime = "UNKNOWN"

        return state

    # ========================================================
    # 2. MOVIMENTO
    # ========================================================

    change = (
        state.price
        - state.previous_price
    )

    absolute_change = abs(change)

    # ========================================================
    # 3. MOVIMENTO NORMALIZZATO
    # ========================================================
    #
    # Esempio:
    #
    # change = 0.50
    # ATR    = 1.00
    #
    # normalized_move = 0.50 ATR
    #
    # Questo permette di confrontare movimenti di
    # diversa ampiezza tra commodity differenti.
    # ========================================================

    normalized_move = (
        absolute_change
        / state.atr
    )

    # ========================================================
    # 4. HIGH VOLATILITY
    # ========================================================

    if (
        normalized_move
        >= HIGH_VOLATILITY_ATR
    ):

        state.regime = "HIGH_VOLATILITY"

        return state

    # ========================================================
    # 5. RANGE / NOISE
    # ========================================================
    #
    # Una variazione piccola rispetto all'ATR non deve
    # essere trasformata automaticamente in trend.
    # ========================================================

    if (
        normalized_move
        < MIN_TREND_MOVE_ATR
    ):

        state.regime = "RANGE"

        return state

    # ========================================================
    # 6. TREND UP
    # ========================================================

    if (
        change > 0
        and normalized_move
        >= STRONG_TREND_MOVE_ATR
    ):

        state.regime = "TREND_UP"

        return state

    # ========================================================
    # 7. TREND DOWN
    # ========================================================

    if (
        change < 0
        and normalized_move
        >= STRONG_TREND_MOVE_ATR
    ):

        state.regime = "TREND_DOWN"

        return state

    # ========================================================
    # 8. MOVIMENTO INTERMEDIO
    # ========================================================
    #
    # Tra 0.20 e 0.35 ATR non abbiamo abbastanza evidenza
    # per chiamarlo trend.
    #
    # Meglio RANGE che inventare un segnale.
    # ========================================================

    state.regime = "RANGE"

    return state