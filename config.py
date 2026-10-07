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
# EXECUTION LAYER
# ------------------------------------------------------------
# Default: completely disabled. When enabled, only canonical Gagarin
# PAPER_SIGNAL decisions may reach the configured adapter.
EXECUTION_ENABLED = os.getenv("EXECUTION_ENABLED", "0") == "1"
EXECUTION_BROKER = os.getenv("EXECUTION_BROKER", "paper").strip().lower()
EXECUTION_DEFAULT_QUANTITY = float(os.getenv("EXECUTION_DEFAULT_QUANTITY", "1"))
IBKR_GATEWAY_URL = os.getenv("IBKR_GATEWAY_URL", "https://localhost:5000/v1/api").strip()
IBKR_VERIFY_TLS = os.getenv("IBKR_VERIFY_TLS", "0") == "1"

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