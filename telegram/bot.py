"""
SOYUZ GAGARIN — Telegram interface v2.0

Gestisce:
- invio report
- diagnostica Bot API
- ricezione comandi via long polling
- risposta a /start, /help, /ping, /status, /id

IMPORTANTE:
GitHub Actions può eseguire il motore periodicamente, ma non è un
processo Telegram permanente. Per risposte in tempo reale bisogna
eseguire run_polling() su un processo sempre attivo.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)


API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 30
POLL_TIMEOUT = 25


# ============================================================
# TELEGRAM API
# ============================================================

def _api(
    method: str,
    payload: Optional[dict] = None,
) -> tuple[bool, dict]:

    if not TELEGRAM_BOT_TOKEN:

        return (
            False,
            {
                "description":
                "TELEGRAM_BOT_TOKEN_MISSING"
            },
        )

    url = (
        f"{API_BASE}/bot"
        f"{TELEGRAM_BOT_TOKEN}/"
        f"{method}"
    )

    try:

        response = requests.post(
            url,
            json=payload or {},
            timeout=REQUEST_TIMEOUT,
        )

        try:

            data = response.json()

        except ValueError:

            data = {
                "description":
                response.text[:500]
            }

        return (
            response.status_code == 200
            and bool(data.get("ok")),
            data,
        )

    except requests.RequestException as exc:

        return (
            False,
            {
                "description":
                f"NETWORK_ERROR: {exc}"
            },
        )


# ============================================================
# DIAGNOSTICA
# ============================================================

def telegram_diagnostic() -> bool:
    """
    Verifica token e configurazione.
    Non stampa mai il token.
    """

    ok, data = _api("getMe")

    if not ok:

        print(
            "Telegram DIAGNOSTIC FAILED | "
            f"{data.get('description', 'unknown error')}"
        )

        return False

    result = data.get(
        "result",
        {},
    )

    print(
        "Telegram DIAGNOSTIC OK | "
        f"bot=@{result.get('username', 'unknown')} | "
        f"id={result.get('id', 'unknown')}"
    )

    if not TELEGRAM_CHAT_ID:

        print(
            "Telegram CHAT ID: MISSING"
        )

    else:

        print(
            "Telegram CHAT ID: PRESENT"
        )

    return True


# ============================================================
# WEBHOOK RESET
# ============================================================

def prepare_long_polling() -> bool:
    """
    Rimuove un eventuale webhook.

    getUpdates non funziona mentre è attivo
    un outgoing webhook.
    """

    ok, data = _api(
        "deleteWebhook",
        {
            "drop_pending_updates": False
        },
    )

    if not ok:

        print(
            "Telegram WEBHOOK RESET FAILED | "
            f"{data.get('description', 'unknown error')}"
        )

        return False

    print(
        "Telegram WEBHOOK RESET OK"
    )

    return True


# ============================================================
# SEND MESSAGE
# ============================================================

def send_telegram(
    message: str,
) -> bool:
    """
    Invia un messaggio Telegram.

    Telegram limita sendMessage a 4096 caratteri.
    Il report viene quindi spezzato automaticamente.
    """

    if (
        not TELEGRAM_BOT_TOKEN
        or not TELEGRAM_CHAT_ID
    ):

        print(
            "Telegram disabled/not configured."
        )

        return False

    text = str(message)

    chunks = [
        text[i:i + 4000]
        for i in range(
            0,
            len(text),
            4000,
        )
    ]

    if not chunks:

        chunks = [""]

    for chunk in chunks:

        ok, data = _api(
            "sendMessage",
            {
                "chat_id":
                TELEGRAM_CHAT_ID,

                "text":
                chunk,

                "disable_web_page_preview":
                True,
            },
        )

        if not ok:

            print(
                "Telegram API: FAILED | "
                f"{data.get('description', 'unknown error')}"
            )

            return False

    print(
        "Telegram API: OK"
    )

    return True


# ============================================================
# REPLY
# ============================================================

def _reply(
    chat_id: int | str,
    text: str,
) -> bool:

    ok, data = _api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
    )

    if not ok:

        print(
            "Telegram reply failed | "
            f"{data.get('description', 'unknown error')}"
        )

    return ok


# ============================================================
# COMMANDS
# ============================================================

def _command_response(
    command: str,
) -> Optional[str]:

    command = (
        command
        .strip()
        .split()[0]
        .lower()
    )

    if "@" in command:

        command = command.split(
            "@",
            1,
        )[0]

    if command in {
        "/start",
        "/help",
    }:

        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧪 PAPER ONLY\n\n"
            "/ping — verifica collegamento\n"
            "/status — stato bot\n"
            "/id — mostra chat ID\n"
            "/help — comandi"
        )

    if command == "/ping":

        return (
            "🟢 SOYUZ ONLINE\n"
            "Telegram OK"
        )

    if command == "/status":

        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 Telegram: ONLINE\n"
            "🧪 Trading: PAPER ONLY"
        )

    return None


# ============================================================
# POLL ONCE
# ============================================================

def poll_once(
    offset: Optional[int] = None,
    handler: Optional[
        Callable[[dict], None]
    ] = None,
) -> Optional[int]:
    """
    Legge gli aggiornamenti Telegram una volta.

    Restituisce il prossimo offset.
    """

    payload = {
        "timeout":
        POLL_TIMEOUT,

        "allowed_updates":
        ["message"],
    }

    if offset is not None:

        payload["offset"] = offset

    ok, data = _api(
        "getUpdates",
        payload,
    )

    if not ok:

        print(
            "Telegram getUpdates FAILED | "
            f"{data.get('description', 'unknown error')}"
        )

        time.sleep(3)

        return offset

    updates = data.get(
        "result",
        [],
    )

    next_offset = offset

    for update in updates:

        update_id = update.get(
            "update_id"
        )

        if isinstance(
            update_id,
            int,
        ):

            next_offset = (
                update_id + 1
            )

        message = (
            update.get("message")
            or {}
        )

        chat = (
            message.get("chat")
            or {}
        )

        chat_id = chat.get(
            "id"
        )

        text = message.get(
            "text",
            "",
        )

        if chat_id is None:

            continue

        # ----------------------------------------------------
        # CUSTOM HANDLER
        # ----------------------------------------------------

        if handler is not None:

            try:

                handler(update)

            except Exception as exc:

                print(
                    "Telegram custom handler error | "
                    f"{type(exc).__name__}: {exc}"
                )

            continue

        # ----------------------------------------------------
        # COMMAND
        # ----------------------------------------------------

        if text.startswith("/"):

            response = (
                _command_response(
                    text
                )
            )

            if response:

                _reply(
                    chat_id,
                    response,
                )

            elif text.lower().startswith(
                "/id"
            ):

                _reply(
                    chat_id,
                    f"🆔 CHAT ID: {chat_id}",
                )

    return next_offset


# ============================================================
# PERMANENT LISTENER
# ============================================================

def run_polling(
    handler: Optional[
        Callable[[dict], None]
    ] = None,
) -> None:
    """
    Listener Telegram permanente.

    Deve essere eseguito su un processo sempre attivo.
    """

    if not telegram_diagnostic():

        raise RuntimeError(
            "Telegram configuration invalid"
        )

    if not prepare_long_polling():

        raise RuntimeError(
            "Telegram webhook reset failed"
        )

    offset = None

    print(
        "Telegram polling started."
    )

    while True:

        offset = poll_once(
            offset=offset,
            handler=handler,
        )


# ============================================================
# REPORT FORMAT
# ============================================================

def format_report(
    results,
):

    lines = [
        "🚀 SOYUZ GAGARIN v2.0",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY",
        "",
        "📊 CLASSIFICA",
    ]

    for index, state in enumerate(
        results,
        start=1,
    ):

        direction = (
            state.setup_direction
            if state.setup_direction
            in {
                "LONG",
                "SHORT",
            }
            else "—"
        )

        lines.append(
            f"{index}. "
            f"{state.commodity} | "
            f"{direction} | "
            f"Prob {state.probability:.1f}% | "
            f"Q {state.quality:.1f} | "
            f"C {state.confidence:.1f} | "
            f"{state.final_decision}"
        )

    entries = [
        state
        for state in results
        if state.final_decision
        == "ENTRY"
    ]

    lines.extend(
        [
            "",
            "🎯 OPERATIVITÀ",
        ]
    )

    if not entries:

        lines.append(
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

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

    return "\n".join(
        lines
    )