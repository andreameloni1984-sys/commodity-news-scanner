# ============================================================
# SOYUZ GAGARIN v1.2
# PIPELINE TESTS
# ============================================================
#
# Test della catena:
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
# I test sono deterministici:
# NON usano API esterne.
# NON usano Twelve Data.
# NON usano Telegram.
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


def _make_candles(
    direction="LONG",
    count=80,
):
    """
    Crea una serie OHLC deterministica.

    Serve solamente per testare la pipeline.
    Non rappresenta dati reali di mercato.
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