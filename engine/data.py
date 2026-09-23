from dataclasses import dataclass, field, asdict
from typing import Optional, Any


# ============================================================
# SOYUZ GAGARIN v1.2
# SINGLE CANONICAL STATE
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
#   ↓
# GAGARIN
#
# UN SOLO STATO CANONICO.
#
# La v1.2 prepara lo stato per:
#
# - OHLC
# - serie storiche
# - swing structure
# - MTF
# - HH / HL / LH / LL
# - breakout
# - retest
#
# I dati vengono aggiunti progressivamente dai moduli
# DATA e STRUCTURE.
# ============================================================


@dataclass
class SoyuzState:

    # ========================================================
    # IDENTITÀ
    # ========================================================

    commodity: str
    symbol: str

    # ========================================================
    # DATA — CURRENT MARKET
    # ========================================================

    price: Optional[float] = None

    previous_price: Optional[float] = None

    atr: Optional[float] = None

    data_ok: bool = False

    live: bool = False

    data_age_seconds: Optional[float] = None

    data_source: str = ""

    # ========================================================
    # DATA — PRIMARY TIMEFRAME
    # ========================================================

    timeframe: str = "5min"

    # Serie OHLC ordinate dal passato verso il presente.
    #
    # Queste liste vengono alimentate dal Data Engine.
    # ========================================================

    opens: list = field(default_factory=list)

    highs: list = field(default_factory=list)

    lows: list = field(default_factory=list)

    closes: list = field(default_factory=list)

    timestamps: list = field(default_factory=list)

    # ========================================================
    # DATA — MULTI TIMEFRAME
    # ========================================================
    #
    # Preparazione per:
    #
    # M5
    # M15
    # M30
    # H1
    #
    # Ogni timeframe potrà contenere la propria serie OHLC.
    #
    # Esempio:
    #
    # {
    #     "5min": {...},
    #     "15min": {...},
    #     "30min": {...},
    #     "1h": {...}
    # }
    #
    # In questa fase viene inizializzato vuoto.
    # ========================================================

    mtf_data: dict = field(default_factory=dict)

    # ========================================================
    # REGIME
    # ========================================================

    regime: str = "UNKNOWN"

    # Intensità del movimento normalizzata rispetto all'ATR.
    #
    # Esempio:
    #
    # 0.20 = 0.20 ATR
    # 1.00 = 1 ATR
    # 1.80 = 1.8 ATR
    #
    normalized_move_atr: Optional[float] = None

    # ========================================================
    # MARKET STRUCTURE
    # ========================================================

    structure: str = "UNKNOWN"

    structure_direction: str = "NONE"

    # ========================================================
    # SWING STRUCTURE
    # ========================================================
    #
    # Preparazione per:
    #
    # HH = Higher High
    # HL = Higher Low
    # LH = Lower High
    # LL = Lower Low
    #
    # Non vengono ancora calcolati automaticamente.
    # ========================================================

    swing_highs: list = field(default_factory=list)

    swing_lows: list = field(default_factory=list)

    last_swing_high: Optional[float] = None

    last_swing_low: Optional[float] = None

    previous_swing_high: Optional[float] = None

    previous_swing_low: Optional[float] = None

    structure_pattern: str = "NONE"

    # Valori possibili futuri:
    #
    # HH_HL
    # LH_LL
    # MIXED
    # RANGE
    # NONE

    # ========================================================
    # BREAKOUT / RETEST
    # ========================================================

    breakout: bool = False

    breakout_direction: str = "NONE"

    breakout_level: Optional[float] = None

    retest: bool = False

    retest_direction: str = "NONE"

    retest_level: Optional[float] = None

    # ========================================================
    # MTF STRUCTURE
    # ========================================================

    mtf_structure: str = "UNCONFIRMED"

    mtf_direction: str = "NONE"

    mtf_alignment: float = 0.0

    # ========================================================
    # SETUP
    # ========================================================

    setup: str = "NONE"

    setup_direction: str = "NONE"

    setup_quality: float = 0.0

    # ========================================================
    # TRIGGER
    # ========================================================

    trigger: str = "NONE"

    trigger_direction: str = "NONE"

    trigger_confirmed: bool = False

    # ========================================================
    # RISK MANAGEMENT
    # ========================================================

    entry: Optional[float] = None

    stop: Optional[float] = None

    tp1: Optional[float] = None

    tp2: Optional[float] = None

    tp3: Optional[float] = None

    stop_atr: Optional[float] = None

    rr1: Optional[float] = None

    rr2: Optional[float] = None

    rr3: Optional[float] = None

    # ========================================================
    # QUALITY / CONFIDENCE
    # ========================================================

    probability: float = 0.0

    quality: float = 0.0

    confidence: float = 0.0

    # ========================================================
    # SAFETY
    # ========================================================

    safety: str = "BLOCKED"

    blockers: list = field(default_factory=list)

    # ========================================================
    # FINAL GAGARIN DECISION
    # ========================================================

    final_decision: str = "WAIT"

    # ========================================================
    # METADATA
    # ========================================================

    analysis_timestamp: Optional[str] = None

    engine_version: str = "SOYUZ-GAGARIN-1.2"

    # ========================================================
    # EXTRA INTERNAL DATA
    # ========================================================
    #
    # Spazio controllato per informazioni che potranno essere
    # introdotte dai nuovi adapter senza creare un secondo
    # stato.
    #
    # Non deve essere usato per prendere decisioni parallele.
    # ========================================================

    metadata: dict = field(default_factory=dict)

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Restituisce lo stato completo come dizionario.

        Utile per:
        - journal
        - debugging
        - Telegram
        - storico
        - backtest
        - API future
        """

        return asdict(self)