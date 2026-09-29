"""
SOYUZ GAGARIN — Telegram interface v3.0

Comandi:
    /start
    /help
    /ping
    /status
    /id
    /classifica
    /setup
    /analisi
    /prezzo

PAPER ONLY:
nessun ordine reale viene eseguito.

NOTA:
Il polling Telegram deve essere eseguito da un processo sempre attivo.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

from engine.gagarin import analyze_universe
from commodities.universe import enabled_commodities


API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 30
POLL_TIMEOUT = 25


# ============================================================
# CACHE ULTIMA ANALISI
# ============================================================

_LAST_RESULTS = None
_LAST_ANALYSIS_TIME = None


def set_last_results(results):
    """
    Salva l'ultima analisi Gagarin in memoria.
    """

    global _LAST_RESULTS
    global _LAST_ANALYSIS_TIME

    _LAST_RESULTS = results
    _LAST_ANALYSIS_TIME = time.time()


def get_last_results():
    return _LAST_RESULTS


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
# FORMAT CLASSIFICA
# ============================================================

def _format_classifica(results):

    if not results:

        return (
            "📊 CLASSIFICA GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun risultato disponibile."
        )

    lines = [
        "🚀 SOYUZ GAGARIN",
        "📊 CLASSIFICA",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY",
        "",
    ]

    for index, state in enumerate(
        results,
        start=1,
    ):

        direction = (
            state.setup_direction
            if state.setup_direction
            in {"LONG", "SHORT"}
            else "—"
        )

        lines.append(
            f"{index}. {state.commodity} | "
            f"{direction} | "
            f"Prob {state.probability:.1f}% | "
            f"Q {state.quality:.1f} | "
            f"C {state.confidence:.1f} | "
            f"{state.final_decision}"
        )

    entries = [
        state
        for state in results
        if state.final_decision == "ENTRY"
    ]

    lines.extend([
        "",
        "🎯 OPERATIVITÀ",
    ])

    if not entries:

        lines.append(
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

    else:

        lines.append(
            f"🟢 {len(entries)} ENTRATA/E AUTORIZZATA/E"
        )

    return "\n".join(lines)


# ============================================================
# FORMAT SETUP
# ============================================================

def _format_setup(results):

    if not results:

        return (
            "🎯 SETUP\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun risultato disponibile."
        )

    lines = [
        "🎯 SETUP GAGARIN",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    found = False

    for state in results:

        if state.setup_direction not in {
            "LONG",
            "SHORT",
        }:

            continue

        found = True

        trigger = (
            "✅ CONFERMATO"
            if state.trigger_confirmed
            else "⏳ IN ATTESA"
        )

        lines.extend([
            f"• {state.commodity}",
            f"  Direzione: {state.setup_direction}",
            f"  Setup Q: {state.setup_quality:.1f}",
            f"  Trigger: {trigger}",
            f"  Prob: {state.probability:.1f}%",
            f"  Quality: {state.quality:.1f}",
            f"  Confidence: {state.confidence:.1f}",
            "",
        ])

    if not found:

        lines.append(
            "Nessun setup LONG/SHORT attivo."
        )

    return "\n".join(lines)


# ============================================================
# FORMAT PREZZI
# ============================================================

def _format_prezzi(results):

    if not results:

        return (
            "💰 PREZZI\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun dato disponibile."
        )

    lines = [
        "💰 PREZZI GAGARIN",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for state in results:

        if state.price is None:

            price = "N/D"

        else:

            price = f"{state.price:.6g}"

        status = state.metadata.get(
            "data_status",
            "UNKNOWN",
        )

        provider = (
            state.data_source
            if state.data_source
            else "N/D"
        )

        lines.append(
            f"{state.commodity}: "
            f"{price} | "
            f"{status} | "
            f"{provider}"
        )

    return "\n".join(lines)


# ============================================================
# ANALISI
# ============================================================

def _run_analysis():

    commodities = enabled_commodities()

    if not commodities:

        return None

    results = analyze_universe(
        commodities
    )

    set_last_results(
        results
    )

    return results


# ============================================================
# COMMAND RESPONSE
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

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if command in {
        "/start",
        "/help",
    }:

        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧪 PAPER ONLY\n\n"
            "/classifica — classifica Gagarin\n"
            "/setup — setup e trigger\n"
            "/analisi — nuova analisi\n"
            "/prezzo — prezzi e provider\n"
            "/status — stato bot\n"
            "/ping — verifica collegamento\n"
            "/id — mostra chat ID\n"
            "/help — comandi"
        )

    # --------------------------------------------------------
    # PING
    # --------------------------------------------------------

    if command == "/ping":

        return (
            "🟢 SOYUZ ONLINE\n"
            "Telegram OK\n"
            "Trading: PAPER ONLY"
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if command == "/status":

        results = get_last_results()

        if results:

            return (
                "🚀 SOYUZ GAGARIN\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🟢 Telegram: ONLINE\n"
                "🟢 Engine: DISPONIBILE\n"
                "🧪 Trading: PAPER ONLY\n"
                f"📊 Commodities: {len(results)}"
            )

        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 Telegram: ONLINE\n"
            "🟢 Engine: DISPONIBILE\n"
            "🧪 Trading: PAPER ONLY\n"
            "📊 Nessuna analisi in memoria"
        )

    # --------------------------------------------------------
    # CLASSIFICA
    # --------------------------------------------------------

    if command == "/classifica":

        results = get_last_results()

        if not results:

            try:

                results = _run_analysis()

            except Exception as exc:

                return (
                    "❌ ERRORE ANALISI\n"
                    f"{type(exc).__name__}: {exc}"
                )

        return _format_classifica(
            results
        )

    # --------------------------------------------------------
    # SETUP
    # --------------------------------------------------------

    if command == "/setup":

        results = get_last_results()

        if not results:

            try:

                results = _run_analysis()

            except Exception as exc:

                return (
                    "❌ ERRORE ANALISI\n"
                    f"{type(exc).__name__}: {exc}"
                )

        return _format_setup(
            results
        )

    # --------------------------------------------------------
    # PREZZO
    # --------------------------------------------------------

    if command == "/prezzo":

        results = get_last_results()

        if not results:

            try:

                results = _run_analysis()

            except Exception as exc:

                return (
                    "❌ ERRORE ANALISI\n"
                    f"{type(exc).__name__}: {exc}"
                )

        return _format_prezzi(
            results
        )

    # --------------------------------------------------------
    # ANALISI
    # --------------------------------------------------------

    if command == "/analisi":

        try:

            results = _run_analysis()

            if not results:

                return (
                    "⚠️ Nessuna commodity disponibile."
                )

            return (
                "🔄 NUOVA ANALISI COMPLETATA\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                + _format_classifica(
                    results
                )
            )

        except Exception as exc:

            return (
                "❌ GAGARIN ENGINE ERROR\n"
                f"{type(exc).__name__}: {exc}"
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

            response = _command_response(
                text
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
        "🚀 SOYUZ GAGARIN v3.0",
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

    lines.extend([
        "",
        "🎯 OPERATIVITÀ",
    ])

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