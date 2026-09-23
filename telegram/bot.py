import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)


# ============================================================
# SOYUZ GAGARIN v1.0
# TELEGRAM OUTPUT
# ============================================================
#
# Questo modulo gestisce esclusivamente:
#
#   SOYUZ → TELEGRAM
#
# Non analizza il mercato.
# Non modifica SoyuzState.
# Non decide ENTRY.
#
# La decisione viene presa dal motore Gagarin.
#
# Telegram riceve solamente il risultato finale.
# ============================================================


def send_telegram(message: str) -> bool:
    """
    Invia un messaggio Telegram.

    Restituisce:

        True  → Telegram ha confermato la consegna
        False → invio fallito/non configurato
    """

    # --------------------------------------------------------
    # CONTROLLO CONFIGURAZIONE
    # --------------------------------------------------------

    if (
        not TELEGRAM_BOT_TOKEN
        or not TELEGRAM_CHAT_ID
    ):
        print(
            "Telegram disabled/not configured."
        )

        return False

    # --------------------------------------------------------
    # TELEGRAM API
    # --------------------------------------------------------

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": str(message),
        "disable_web_page_preview": True,
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )

        # ----------------------------------------------------
        # RISPOSTA API
        # ----------------------------------------------------

        try:
            data = response.json()

        except ValueError:

            data = {}

        api_ok = bool(
            data.get("ok")
        )

        http_ok = (
            response.status_code == 200
        )

        delivered = (
            http_ok
            and api_ok
        )

        if delivered:

            print(
                "Telegram API: OK"
            )

        else:

            description = data.get(
                "description",
                "unknown error",
            )

            print(
                "Telegram API: FAILED | "
                f"HTTP={response.status_code} | "
                f"{description}"
            )

        return delivered

    except requests.RequestException as exc:

        print(
            "Telegram network error:",
            exc,
        )

        return False

    except Exception as exc:

        print(
            "Telegram unexpected error:",
            exc,
        )

        return False


def format_report(results):
    """
    Costruisce il report Telegram a partire
    esclusivamente dagli SoyuzState prodotti
    dal Gagarin.

    Nessuna nuova analisi viene effettuata qui.
    """

    # ========================================================
    # HEADER
    # ========================================================

    lines = [
        "🚀 SOYUZ GAGARIN v1.0",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY",
        "",
        "📊 CLASSIFICA",
    ]

    # ========================================================
    # RANKING
    # ========================================================

    for index, state in enumerate(
        results,
        start=1,
    ):

        if state.setup_direction in {
            "LONG",
            "SHORT",
        }:

            direction = (
                state.setup_direction
            )

        else:

            direction = "—"

        lines.append(
            f"{index}. "
            f"{state.commodity} | "
            f"{direction} | "
            f"Prob {state.probability:.1f}% | "
            f"Q {state.quality:.1f} | "
            f"{state.final_decision}"
        )

    # ========================================================
    # ENTRIES
    # ========================================================

    entries = [
        state
        for state in results
        if state.final_decision == "ENTRY"
    ]

    lines.extend(
        [
            "",
            "🎯 OPERATIVITÀ",
        ]
    )

    # --------------------------------------------------------
    # NESSUNA ENTRY
    # --------------------------------------------------------

    if not entries:

        lines.append(
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

    # --------------------------------------------------------
    # ENTRY
    # --------------------------------------------------------

    else:

        for state in entries[:3]:

            lines.extend(
                [
                    "",
                    (
                        f"🟢 "
                        f"{state.commodity} "
                        f"{state.setup_direction}"
                    ),
                    (
                        f"Entry: "
                        f"{state.entry:.6g}"
                    ),
                    (
                        f"SL: "
                        f"{state.stop:.6g}"
                    ),
                    (
                        f"TP1: "
                        f"{state.tp1:.6g}"
                    ),
                    (
                        f"TP2: "
                        f"{state.tp2:.6g}"
                    ),
                    (
                        f"TP3: "
                        f"{state.tp3:.6g}"
                    ),
                ]
            )

    # ========================================================
    # REPORT FINALE
    # ========================================================

    return "\n".join(
        lines
    )