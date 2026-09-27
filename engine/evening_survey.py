"""
SOYUZ GAGARIN — EVENING SURVEY v1.0

Sondaggio serale delle commodity.

Scopo:
- fotografare la giornata;
- aggiornare il quadro settimanale/storico disponibile;
- preparare informazioni per i tre motori;
- NON generare ENTRY;
- NON bypassare Gagarin.

Flusso:

EVENING SURVEY
    ↓
DAILY
    ↓
WEEKLY / HISTORICAL
    ↓
FUNDAMENTAL / POLITICAL INPUT
    ↓
MOTOR 1 / MOTOR 2 / MOTOR 3
    ↓
GAGARIN decide autonomamente.

Il modulo lavora sui dati già presenti nello stato canonico.
Non esegue una seconda analisi intraday e non modifica SoyuzState.
"""

from __future__ import annotations

from typing import Any, Iterable


# ============================================================
# UTILITY
# ============================================================

def _pct(
    current: float | None,
    previous: float | None,
) -> float | None:
    """Calcola la variazione percentuale."""
    if current is None or previous in (None, 0):
        return None

    return (
        (float(current) - float(previous))
        / abs(float(previous))
    ) * 100.0


def _safe_float(value: Any) -> float | None:
    """Conversione sicura a float."""
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _window(
    values: list[float],
    size: int,
) -> list[float]:
    """Restituisce le ultime N osservazioni."""
    if size <= 0:
        return []

    return values[-size:]


def _trend(values: list[float]) -> str:
    """
    Determina il bias sulla finestra disponibile.

    Soglia:
        >= +1%  BULLISH
        <= -1%  BEARISH
        altro   NEUTRAL
    """

    if len(values) < 2:
        return "UNKNOWN"

    first = values[0]
    last = values[-1]

    if first == 0:
        return "UNKNOWN"

    move = (last - first) / abs(first)

    if move >= 0.01:
        return "BULLISH"

    if move <= -0.01:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# DIRECTION
# ============================================================

def _direction_from_state(state: Any) -> str:
    """
    Recupera la direzione già presente nello stato.

    Il sondaggio NON crea una nuova direzione operativa.
    """

    direction = getattr(
        state,
        "setup_direction",
        "NONE",
    )

    if direction in {"LONG", "SHORT"}:
        return direction

    direction = getattr(
        state,
        "structure_direction",
        "NONE",
    )

    if direction in {"LONG", "SHORT"}:
        return direction

    return "NONE"


# ============================================================
# FUNDAMENTAL / POLITICAL INPUT
# ============================================================

def _fundamental_bucket(
    metadata: dict[str, Any],
) -> str:
    """Normalizza il bias fondamentale."""

    value = str(
        metadata.get("fundamental_bias")
        or metadata.get("macro_bias")
        or "NEUTRAL"
    ).upper()

    if value in {
        "LONG",
        "BULLISH",
        "POSITIVE",
    }:
        return "BULLISH"

    if value in {
        "SHORT",
        "BEARISH",
        "NEGATIVE",
    }:
        return "BEARISH"

    return "NEUTRAL"


def _political_bucket(
    metadata: dict[str, Any],
) -> str:
    """Normalizza il bias politico/geopolitico."""

    value = str(
        metadata.get("political_bias")
        or metadata.get("geopolitical_bias")
        or "NEUTRAL"
    ).upper()

    if value in {
        "LONG",
        "BULLISH",
        "POSITIVE",
    }:
        return "BULLISH"

    if value in {
        "SHORT",
        "BEARISH",
        "NEGATIVE",
    }:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# THREE MOTOR INPUTS
# ============================================================

def _build_motor_inputs(
    state: Any,
    daily_bias: str,
    weekly_bias: str,
    historical_bias: str,
) -> dict[str, Any]:
    """
    Costruisce il pacchetto informativo destinato
    ai tre motori.

    IMPORTANTE:
    nessun campo qui autorizza un trade.
    """

    metadata = getattr(
        state,
        "metadata",
        {},
    ) or {}

    return {

        # ====================================================
        # MOTOR 1
        # MACRO / FUNDAMENTAL
        # ====================================================

        "motor_1_macro_fundamental": {

            "commodity": state.commodity,

            "daily_bias": daily_bias,

            "weekly_bias": weekly_bias,

            "historical_bias": historical_bias,

            "fundamental_bias": (
                _fundamental_bucket(metadata)
            ),

            "events": metadata.get(
                "fundamental_events",
                [],
            ),

            "macro_factors": metadata.get(
                "macro_factors",
                [],
            ),

            "weather_factors": metadata.get(
                "weather_factors",
                [],
            ),

            "supply_demand_factors": metadata.get(
                "supply_demand_factors",
                [],
            ),
        },

        # ====================================================
        # MOTOR 2
        # MARKET INTELLIGENCE / POLITICAL
        # ====================================================

        "motor_2_market_intelligence": {

            "commodity": state.commodity,

            "political_bias": (
                _political_bucket(metadata)
            ),

            "geopolitical_events": metadata.get(
                "geopolitical_events",
                [],
            ),

            "political_events": metadata.get(
                "political_events",
                [],
            ),

            "policy_factors": metadata.get(
                "policy_factors",
                [],
            ),

            "shock_flag": bool(
                metadata.get(
                    "shock_flag",
                    False,
                )
            ),

            "event_risk": metadata.get(
                "event_risk",
                "UNKNOWN",
            ),
        },

        # ====================================================
        # MOTOR 3
        # GAGARIN OPERATIONAL
        # ====================================================

        "motor_3_gagarin": {

            "commodity": state.commodity,

            "data_ok": bool(
                getattr(
                    state,
                    "data_ok",
                    False,
                )
            ),

            "live": bool(
                getattr(
                    state,
                    "live",
                    False,
                )
            ),

            "data_age_seconds": getattr(
                state,
                "data_age_seconds",
                None,
            ),

            "daily_bias": daily_bias,

            "weekly_bias": weekly_bias,

            "historical_bias": historical_bias,

            "regime": getattr(
                state,
                "regime",
                "UNKNOWN",
            ),

            "structure": getattr(
                state,
                "structure",
                "UNKNOWN",
            ),

            "setup_direction": (
                _direction_from_state(state)
            ),

            "trigger_confirmed": bool(
                getattr(
                    state,
                    "trigger_confirmed",
                    False,
                )
            ),

            "instruction": (
                "INFORMATIONAL_ONLY: "
                "il sondaggio non autorizza ENTRY. "
                "Gagarin deve rieseguire tutti "
                "i gate DATA->SAFETY."
            ),
        },
    }


# ============================================================
# SINGLE COMMODITY
# ============================================================

def analyze_state(
    state: Any,
) -> dict[str, Any]:
    """
    Costruisce il sondaggio serale per una commodity.

    NON modifica state.
    """

    # --------------------------------------------------------
    # CLOSES
    # --------------------------------------------------------

    closes = [
        value
        for value in (
            _safe_float(x)
            for x in getattr(
                state,
                "closes",
                [],
            )
        )
        if value is not None
    ]

    price = _safe_float(
        getattr(
            state,
            "price",
            None,
        )
    )

    previous_price = _safe_float(
        getattr(
            state,
            "previous_price",
            None,
        )
    )

    # --------------------------------------------------------
    # DAILY
    # --------------------------------------------------------

    daily_change = _pct(
        price,
        previous_price,
    )

    # --------------------------------------------------------
    # TIME WINDOWS
    #
    # Con timeframe 5m:
    #
    # 12 barre  = 1 ora
    # 288 barre = 1 giorno
    # 2016 barre = 7 giorni
    #
    # Se la serie è più corta utilizziamo
    # ciò che realmente abbiamo.
    # --------------------------------------------------------

    day_values = _window(
        closes,
        288,
    )

    week_values = _window(
        closes,
        7 * 288,
    )

    # --------------------------------------------------------
    # BIASES
    # --------------------------------------------------------

    daily_bias = _trend(
        day_values,
    )

    weekly_bias = _trend(
        week_values,
    )

    historical_bias = _trend(
        closes,
    )

    # --------------------------------------------------------
    # DAILY OVERRIDE
    #
    # Se abbiamo una variazione giornaliera
    # significativa, la usiamo per rafforzare
    # il quadro giornaliero.
    # --------------------------------------------------------

    if daily_change is not None:

        if daily_change >= 0.5:
            daily_bias = "BULLISH"

        elif daily_change <= -0.5:
            daily_bias = "BEARISH"

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    result = {

        "commodity": state.commodity,

        "symbol": state.symbol,

        "timestamp": getattr(
            state,
            "analysis_timestamp",
            None,
        ),

        # ====================================================
        # DATA
        # ====================================================

        "data": {

            "price": price,

            "previous_price": previous_price,

            "daily_change_pct": daily_change,

            "data_ok": bool(
                getattr(
                    state,
                    "data_ok",
                    False,
                )
            ),

            "live": bool(
                getattr(
                    state,
                    "live",
                    False,
                )
            ),

            "age_seconds": getattr(
                state,
                "data_age_seconds",
                None,
            ),

            "provider": getattr(
                state,
                "data_source",
                "",
            ),
        },

        # ====================================================
        # SCENARIO
        # ====================================================

        "scenario": {

            "daily_bias": daily_bias,

            "weekly_bias": weekly_bias,

            "historical_bias": historical_bias,

            "regime": getattr(
                state,
                "regime",
                "UNKNOWN",
            ),

            "structure": getattr(
                state,
                "structure",
                "UNKNOWN",
            ),
        },

        # ====================================================
        # HISTORICAL / WEEKLY
        # ====================================================

        "historical_weekly": {

            "available_bars": len(
                closes
            ),

            "daily_bars_used": len(
                day_values
            ),

            "weekly_bars_used": len(
                week_values
            ),

            "historical_bars_used": len(
                closes
            ),
        },
    }

    # ========================================================
    # THREE MOTORS
    # ========================================================

    result["motors"] = _build_motor_inputs(
        state,
        daily_bias,
        weekly_bias,
        historical_bias,
    )

    return result


# ============================================================
# UNIVERSE
# ============================================================

def analyze_universe(
    states: Iterable[Any],
) -> list[dict[str, Any]]:
    """
    Crea il sondaggio serale per tutto l'universo Gagarin.
    """

    results = [
        analyze_state(state)
        for state in states
    ]

    def rank(
        item: dict[str, Any],
    ) -> tuple:

        scenario = item["scenario"]

        live = item["data"]["live"]

        daily = (
            scenario["daily_bias"]
            != "UNKNOWN"
        )

        weekly = (
            scenario["weekly_bias"]
            != "UNKNOWN"
        )

        return (
            live,
            weekly,
            daily,
        )

    return sorted(
        results,
        key=rank,
        reverse=True,
    )


# ============================================================
# THREE-MOTOR PACKET
# ============================================================

def build_three_motor_packet(
    states: Iterable[Any],
) -> dict[str, Any]:
    """
    Pacchetto unico da consegnare ai tre motori.

    Nessun campo autorizza un trade.
    """

    surveys = analyze_universe(
        states
    )

    return {

        "version": (
            "SOYUZ-EVENING-SURVEY-1.0"
        ),

        "type": "EVENING_SURVEY",

        "informational_only": True,

        "surveys": surveys,

        "three_motors": {

            "motor_1": (
                "MACRO_FUNDAMENTAL"
            ),

            "motor_2": (
                "MARKET_INTELLIGENCE_POLITICAL"
            ),

            "motor_3": (
                "GAGARIN_OPERATIONAL"
            ),
        },

        "final_rule": (
            "Il sondaggio serale alimenta "
            "i motori ma non genera ENTRY. "
            "Ogni eventuale operazione deve "
            "superare DATA -> REGIME -> "
            "STRUCTURE -> SETUP -> TRIGGER "
            "-> RISK -> SAFETY."
        ),
    }


# ============================================================
# COMPACT OUTPUT
# ============================================================

def to_compact_row(
    survey: dict[str, Any],
) -> dict[str, Any]:
    """
    Riga compatta utile per:
    - Telegram
    - CSV
    - report serale
    """

    scenario = survey["scenario"]

    data = survey["data"]

    return {

        "commodity": survey[
            "commodity"
        ],

        "symbol": survey[
            "symbol"
        ],

        "daily": scenario[
            "daily_bias"
        ],

        "weekly": scenario[
            "weekly_bias"
        ],

        "historical": scenario[
            "historical_bias"
        ],

        "regime": scenario[
            "regime"
        ],

        "structure": scenario[
            "structure"
        ],

        "live": data[
            "live"
        ],

        "provider": data[
            "provider"
        ],

        "age_seconds": data[
            "age_seconds"
        ],
    }