from dataclasses import dataclass, field, asdict
from typing import Optional


# ============================================================
# SOYUZ GAGARIN v1.0
# SINGLE CANONICAL STATE
# ============================================================
#
# Questo oggetto rappresenta lo STATO UNICO della commodity.
#
# Pipeline:
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
# Nessun motore deve creare una seconda versione dello stato.
# Tutti i moduli lavorano sullo stesso SoyuzState.
# ============================================================


@dataclass
class SoyuzState:

    # ========================================================
    # IDENTITÀ
    # ========================================================

    commodity: str
    symbol: str

    # ========================================================
    # DATA
    # ========================================================

    price: Optional[float] = None

    previous_price: Optional[float] = None

    atr: Optional[float] = None

    data_ok: bool = False

    live: bool = False

    data_age_seconds: Optional[float] = None

    data_source: str = ""

    # ========================================================
    # REGIME
    # ========================================================

    regime: str = "UNKNOWN"

    # ========================================================
    # MARKET STRUCTURE
    # ========================================================

    structure: str = "UNKNOWN"

    structure_direction: str = "NONE"

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
    # SERIALIZATION
    # ========================================================

    def to_dict(self):
        """
        Restituisce lo stato completo come dizionario.

        Utile per:
        - journal
        - debugging
        - Telegram
        - storico
        - future API
        """

        return asdict(self)