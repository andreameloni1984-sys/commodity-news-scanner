import os


# ============================================================
# SOYUZ GAGARIN v1.0
# CONFIGURAZIONE CENTRALE
# ============================================================

# ------------------------------------------------------------
# MODALITÀ OPERATIVA
# ------------------------------------------------------------

# V1.0 è esclusivamente PAPER.
# Nessun ordine reale viene eseguito.
PAPER_TRADING_ONLY = True


# ------------------------------------------------------------
# TELEGRAM
# ------------------------------------------------------------

TELEGRAM_ENABLED = (
    os.getenv("TELEGRAM_ENABLED", "0") == "1"
)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()


# ------------------------------------------------------------
# MARKET DATA
# ------------------------------------------------------------

TWELVE_DATA_API_KEY = os.getenv(
    "TWELVE_DATA_API_KEY",
    ""
).strip()


# ------------------------------------------------------------
# GAGARIN — OPERATIONAL GATES
# ------------------------------------------------------------

MIN_PROBABILITY = float(
    os.getenv("MIN_ENTRY_PROBABILITY", "62")
)

MIN_QUALITY = float(
    os.getenv("MIN_ENTRY_QUALITY", "55")
)

MIN_CONFIDENCE = float(
    os.getenv("MIN_ENTRY_CONFIDENCE", "60")
)

MIN_RR = float(
    os.getenv("MIN_ENTRY_RR", "2.5")
)

MAX_STOP_ATR = float(
    os.getenv("MAX_ENTRY_STOP_ATR", "2.5")
)


# ------------------------------------------------------------
# DATA SETTINGS
# ------------------------------------------------------------

TIMEOUT_SECONDS = int(
    os.getenv("DATA_TIMEOUT_SECONDS", "10")
)

LIVE_MAX_AGE_SECONDS = int(
    os.getenv("LIVE_MAX_AGE_SECONDS", "60")
)

LOOKBACK = int(
    os.getenv("DATA_LOOKBACK", "120")
)