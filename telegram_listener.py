#!/usr/bin/env python3
"""
SOYUZ GAGARIN - Telegram Listener v3

Telegram -> GitHub Actions -> commodity_bot.py

Il listener:
- verifica il bot Telegram;
- controlla webhook/getUpdates;
- elimina eventuali webhook che impediscono il polling;
- registra i comandi;
- riceve i messaggi Telegram;
- autorizza la chat configurata;
- traduce i comandi;
- avvia commodity_bot.py in modalità ON_DEMAND;
- restituisce la risposta su Telegram;
- mantiene l'offset degli update.

PAPER ONLY.
Nessun ordine reale viene eseguito.
"""

import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

STATE_FILE = Path(
    os.getenv(
        "TELEGRAM_LISTENER_STATE_FILE",
        "telegram_listener_state.json",
    )
)

POLL_TIMEOUT = int(
    os.getenv(
        "TELEGRAM_POLL_TIMEOUT",
        "15",
    )
)

MAX_RUNTIME = int(
    os.getenv(
        "TELEGRAM_LISTENER_MAX_SECONDS",
        "1140",
    )
)

ANALYSIS_TIMEOUT = int(
    os.getenv(
        "TELEGRAM_ANALYSIS_TIMEOUT",
        "900",
    )
)

BASE_URL = (
    f"https://api.telegram.org/bot{TOKEN}"
    if TOKEN
    else ""
)


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

COMMANDS = [
    {
        "command": "start",
        "description": "Avvia SOYUZ GAGARIN",
    },
    {
        "command": "help",
        "description": "Mostra i comandi",
    },
    {
        "command": "classifica",
        "description": "Classifica commodity",
    },
    {
        "command": "setup",
        "description": "Migliore setup",
    },
    {
        "command": "segnali",
        "description": "Segnali operativi",
    },
    {
        "command": "scalping",
        "description": "Scalping commodity",
    },
    {
        "command": "analisi",
        "description": "Analisi commodity",
    },
    {
        "command": "prezzo",
        "description": "Prezzo live commodity",
    },
    {
        "command": "oro",
        "description": "Analisi Oro",
    },
    {
        "command": "argento",
        "description": "Analisi Argento",
    },
    {
        "command": "rame",
        "description": "Analisi Rame",
    },
    {
        "command": "platino",
        "description": "Analisi Platino",
    },
    {
        "command": "palladio",
        "description": "Analisi Palladio",
    },
    {
        "command": "wti",
        "description": "Analisi WTI",
    },
    {
        "command": "brent",
        "description": "Analisi Brent",
    },
    {
        "command": "cacao",
        "description": "Analisi Cacao",
    },
    {
        "command": "caffe",
        "description": "Analisi Caffè",
    },
    {
        "command": "zucchero",
        "description": "Analisi Zucchero",
    },
    {
        "command": "riso",
        "description": "Analisi Riso",
    },
    {
        "command": "soia",
        "description": "Analisi Soia",
    },
]


# ============================================================
# COMMODITY ALIASES
# ============================================================

ALIASES = {
    "oro": "Oro",
    "gold": "Oro",
    "xau": "Oro",
    "xauusd": "Oro",

    "argento": "Argento",
    "silver": "Argento",
    "xag": "Argento",
    "xagusd": "Argento",

    "rame": "Rame",
    "copper": "Rame",
    "hg": "Rame",

    "platino": "Platino",
    "platinum": "Platino",
    "xpt": "Platino",

    "palladio": "Palladio",
    "palladium": "Palladio",
    "xpd": "Palladio",

    "wti": "Petrolio WTI",
    "petroliowti": "Petrolio WTI",
    "oilwti": "Petrolio WTI",

    "brent": "Petrolio Brent",
    "petroliobrent": "Petrolio Brent",

    "cacao": "Cacao",
    "cocoa": "Cacao",

    "caffe": "Caffè",
    "coffee": "Caffè",

    "zucchero": "Zucchero",
    "sugar": "Zucchero",

    "riso": "Riso",
    "rice": "Riso",

    "soia": "Soia",
    "soybean": "Soia",

    "mais": "Mais",
    "corn": "Mais",

    "grano": "Grano",
    "wheat": "Grano",

    "cotone": "Cotone",
    "cotton": "Cotone",

    "gasnaturale": "Gas Naturale",
    "naturalgas": "Gas Naturale",
    "natgas": "Gas Naturale",
}


COMMAND_ALIASES = {
    "classifica": "CLASSIFICA",
    "ranking": "CLASSIFICA",
    "rank": "CLASSIFICA",

    "setup": "SETUP",
    "miglioresetup": "SETUP",
    "best": "SETUP",

    "segnali": "SEGNALI",
    "signals": "SEGNALI",

    "scalping": "SCALPING",
    "scalp": "SCALPING",

    "analisi": "ANALISI",
    "analysis": "ANALISI",
    "commodity": "ANALISI",

    "prezzo": "PREZZO",
    "price": "PREZZO",
}


# ============================================================
# HELP
# ============================================================

HELP_TEXT = (
    "🤖 SOYUZ GAGARIN — COMANDI\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Puoi scrivere anche semplicemente il nome della commodity.\n\n"

    "📊 CLASSIFICA — ranking commodity\n"
    "🎯 SETUP — migliore setup\n"
    "🚨 SEGNALI — segnali operativi\n"
    "⚡ SCALPING ORO — scalping Oro\n"
    "🔎 ANALISI ORO — analisi completa\n"
    "💰 PREZZO ORO — prezzo/live\n\n"

    "Esempi:\n"
    "• Oro\n"
    "• Brent\n"
    "• Cacao\n"
    "• Analisi Oro\n"
    "• Scalping Oro\n"
    "• /oro\n"
    "• /classifica\n"
    "• /segnali\n\n"

    "🧪 PAPER ONLY — nessun ordine reale."
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value or "",
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.lower().strip()

    value = re.sub(
        r"[@#]",
        "",
        value,
    )

    value = re.sub(
        r"[/_-]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def compact(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        normalize(value),
    )


# ============================================================
# TELEGRAM API
# ============================================================

def telegram(
    method: str,
    payload=None,
    timeout=30,
):
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN mancante"
        )

    response = requests.post(
        f"{BASE_URL}/{method}",
        json=payload or {},
        timeout=timeout,
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "ok": False,
            "description": response.text,
        }

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram {method} errore: "
            f"{data.get('description', response.text)}"
        )

    return data.get("result")


def get_me():
    return telegram(
        "getMe",
        {},
        timeout=30,
    )


def get_webhook_info():
    return telegram(
        "getWebhookInfo",
        {},
        timeout=30,
    )


def delete_webhook():
    return telegram(
        "deleteWebhook",
        {
            "drop_pending_updates": False,
        },
        timeout=30,
    )


def set_commands():
    return telegram(
        "setMyCommands",
        {
            "commands": COMMANDS,
        },
        timeout=30,
    )


# ============================================================
# TELEGRAM SEND
# ============================================================

def send_message(
    chat_id,
    text,
):
    text = str(text or "").strip()

    if not text:
        text = "⚠️ Nessuna risposta generata."

    chunks = []

    while text:
        if len(text) <= 3900:
            chunks.append(text)
            break

        cut = text.rfind(
            "\n",
            0,
            3900,
        )

        if cut < 1000:
            cut = 3900

        chunks.append(
            text[:cut]
        )

        text = text[cut:].lstrip("\n")

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        result = telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )

        message_id = None

        if isinstance(result, dict):
            message_id = result.get(
                "message_id"
            )

        print(
            "✅ TELEGRAM SEND OK | "
            f"chunk {index}/{len(chunks)} | "
            f"chat={chat_id} | "
            f"message_id={message_id}"
        )


# ============================================================
# OFFSET
# ============================================================

def read_offset():
    try:
        data = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        return int(
            data.get(
                "offset",
                0,
            )
        )

    except Exception:
        return 0


def write_offset(offset):
    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = STATE_FILE.with_suffix(
        ".tmp"
    )

    tmp.write_text(
        json.dumps(
            {
                "offset": int(offset),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    tmp.replace(
        STATE_FILE
    )


# ============================================================
# CHAT SECURITY
# ============================================================

def allowed_chat(chat_id):
    if not ALLOWED_CHAT_ID:
        return True

    return str(chat_id) == str(
        ALLOWED_CHAT_ID
    )


# ============================================================
# COMMODITY DETECTION
# ============================================================

def find_commodity(text):
    value = compact(text)

    if value in ALIASES:
        return ALIASES[value]

    for alias, name in sorted(
        ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if alias and alias in value:
            return name

    return None


# ============================================================
# REQUEST PARSER
# ============================================================

def parse_request(text):
    raw = (text or "").strip()

    normalized = normalize(raw)

    if not normalized:
        return None, None

    if normalized.startswith("/"):
        normalized = normalized[1:].strip()

        normalized = normalized.split(
            "@",
            1,
        )[0].strip()

    compacted = compact(
        normalized
    )

    # ----------------------------------------
    # HELP
    # ----------------------------------------

    if compacted in {
        "start",
        "help",
        "aiuto",
        "menu",
        "comandi",
    }:
        return "HELP", None

    # ----------------------------------------
    # COMMAND ONLY
    # ----------------------------------------

    if compacted in COMMAND_ALIASES:
        return (
            COMMAND_ALIASES[
                compacted
            ],
            None,
        )

    commodity = find_commodity(
        normalized
    )

    # ----------------------------------------
    # SOLO COMMODITY
    # ----------------------------------------

    if commodity and (
        compacted
        == compact(commodity)
    ):
        return (
            "ANALISI",
            commodity,
        )

    # ----------------------------------------
    # COMMAND + COMMODITY
    # ----------------------------------------

    for alias, command in sorted(
        COMMAND_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if compacted.startswith(alias):
            remainder = compacted[
                len(alias):
            ]

            if remainder:
                found = find_commodity(
                    remainder
                )

                if found:
                    return (
                        command,
                        found,
                    )

    # ----------------------------------------
    # COMMODITY + COMMAND
    # ----------------------------------------

    if commodity:
        for alias, command in COMMAND_ALIASES.items():
            if (
                compacted.endswith(alias)
                and compacted != alias
            ):
                return (
                    command,
                    commodity,
                )

    return None, None


# ============================================================
# ENVIRONMENT FOR COMMODITY BOT
# ============================================================

def build_env(
    command,
    commodity,
    chat_id,
    original,
):
    env = os.environ.copy()

    env.update(
        {
            "RUN_MODE": "ON_DEMAND",
            "REPORT_TYPE": "NONE",

            "REQUEST_TYPE": command,
            "REQUEST_COMMODITY": (
                commodity or ""
            ),

            "ON_DEMAND_TELEGRAM_REQUEST": (
                original
            ),

            "ON_DEMAND_TELEGRAM_CHAT_ID": (
                str(chat_id)
            ),

            "SILENT_INTERNAL_ANALYSIS": "1",

            "PAPER_TRADING_ONLY": "1",
            "DEMO_TRADING_ENABLED": "0",
        }
    )

    return env


# ============================================================
# RUN COMMODITY BOT
# ============================================================

def run_analysis(
    command,
    commodity,
    chat_id,
    original,
):
    env = build_env(
        command,
        commodity,
        chat_id,
        original,
    )

    if command == "SCALPING":
        intro = (
            f"⚡ Analizzo lo scalping di "
            f"{commodity or 'migliore commodity'}…"
        )

    elif command == "ANALISI":
        intro = (
            f"🔎 Analizzo "
            f"{commodity or 'la commodity richiesta'}…"
        )

    elif command == "PREZZO":
        intro = (
            f"💰 Recupero il prezzo di "
            f"{commodity or 'della commodity'}…"
        )

    else:
        intro = (
            "🧠 SOYUZ GAGARIN sta elaborando "
            "la richiesta…"
        )

    send_message(
        chat_id,
        intro,
    )

    try:
        completed = subprocess.run(
            [
                sys.executable,
                "commodity_bot.py",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=ANALYSIS_TIMEOUT,
        )

        print(
            "🧠 commodity_bot.py "
            f"returncode={completed.returncode}"
        )

        if completed.stdout:
            print(
                "----- BOT STDOUT -----"
            )
            print(
                completed.stdout[
                    -12000:
                ]
            )

        if completed.stderr:
            print(
                "----- BOT STDERR -----"
            )
            print(
                completed.stderr[
                    -12000:
                ]
            )

        if completed.returncode != 0:
            tail = (
                completed.stderr
                or completed.stdout
                or ""
            ).strip()

            if not tail:
                tail = (
                    "errore senza dettagli"
                )

            tail = tail[-2500:]

            send_message(
                chat_id,
                "⚠️ Analisi non completata.\n"
                "Il motore non ha prodotto "
                "una risposta operativa.\n\n"
                f"Dettaglio tecnico:\n{tail}",
            )

    except subprocess.TimeoutExpired:
        send_message(
            chat_id,
            "⏱️ Analisi oltre il tempo massimo.\n"
            "Nessun ordine è stato eseguito: "
            "PAPER ONLY.",
        )

    except Exception as exc:
        send_message(
            chat_id,
            "⚠️ Errore Telegram/SOYUZ:\n"
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# PROCESS TELEGRAM UPDATE
# ============================================================

def process_update(update):
    update_id = update.get(
        "update_id"
    )

    print(
        f"📥 Telegram update "
        f"{update_id} ricevuto"
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
        "text"
    )

    if chat_id is None:
        print(
            "⚠️ Update senza chat_id"
        )
        return

    if not text:
        print(
            "ℹ️ Update senza testo"
        )
        return

    print(
        f"💬 Telegram message | "
        f"chat={chat_id} | "
        f"text={text!r}"
    )

    if not allowed_chat(
        chat_id
    ):
        print(
            f"⛔ Chat non autorizzata: "
            f"{chat_id}"
        )

        send_message(
            chat_id,
            "⛔ Chat non autorizzata.",
        )

        return

    command, commodity = parse_request(
        text
    )

    print(
        f"🔎 Parsed command={command!r} "
        f"commodity={commodity!r}"
    )

    if command == "HELP":
        send_message(
            chat_id,
            HELP_TEXT,
        )

        return

    if command is None:
        send_message(
            chat_id,
            "❓ Non ho capito la richiesta.\n\n"
            "Prova:\n"
            "• Oro\n"
            "• Analisi Oro\n"
            "• Scalping Oro\n"
            "• Classifica\n"
            "• Setup\n"
            "• Segnali\n\n"
            "Oppure /help.",
        )

        return

    run_analysis(
        command,
        commodity,
        chat_id,
        text,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    if not TOKEN:
        print(
            "❌ TELEGRAM_BOT_TOKEN mancante."
        )

        return 2

    print(
        "🤖 SOYUZ TELEGRAM LISTENER v3"
    )

    print(
        f"📌 Chat autorizzata: "
        f"{ALLOWED_CHAT_ID or 'TUTTE'}"
    )

    # ----------------------------------------
    # VERIFY BOT
    # ----------------------------------------

    try:
        me = get_me()

        print(
            "✅ Telegram getMe OK | "
            f"id={me.get('id')} | "
            f"username=@{me.get('username')}"
        )

    except Exception as exc:
        print(
            "❌ Telegram getMe FAILED | "
            f"{exc}"
        )

        return 1

    # ----------------------------------------
    # WEBHOOK CHECK
    # ----------------------------------------

    try:
        webhook = get_webhook_info()

        webhook_url = (
            webhook.get("url")
            if isinstance(
                webhook,
                dict,
            )
            else None
        )

        pending = (
            webhook.get(
                "pending_update_count",
                0,
            )
            if isinstance(
                webhook,
                dict,
            )
            else 0
        )

        print(
            "🔎 Telegram webhook | "
            f"url={webhook_url or 'NONE'} | "
            f"pending={pending}"
        )

        if webhook_url:
            print(
                "⚠️ Webhook presente. "
                "Lo elimino per usare getUpdates..."
            )

            delete_webhook()

            print(
                "✅ Webhook eliminato"
            )

    except Exception as exc:
        print(
            "⚠️ Webhook check failed | "
            f"{exc}"
        )

    # ----------------------------------------
    # COMMANDS
    # ----------------------------------------

    try:
        set_commands()

        print(
            "✅ Telegram commands registrati"
        )

    except Exception as exc:
        print(
            "⚠️ setMyCommands failed | "
            f"{exc}"
        )

    # ----------------------------------------
    # OFFSET
    # ----------------------------------------

    offset = read_offset()

    print(
        f"📌 Starting Telegram offset: "
        f"{offset}"
    )

    deadline = (
        time.time()
        + MAX_RUNTIME
    )

    print(
        f"⏱️ Listener runtime: "
        f"{MAX_RUNTIME}s"
    )

    # ----------------------------------------
    # LONG POLLING
    # ----------------------------------------

    while time.time() < deadline:

        try:
            updates = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "limit": 20,
                    "timeout": POLL_TIMEOUT,
                    "allowed_updates": [
                        "message"
                    ],
                },
                timeout=POLL_TIMEOUT + 10,
            ) or []

            if not updates:
                continue

            print(
                f"📦 Ricevuti "
                f"{len(updates)} update"
            )

            for update in updates:

                update_id = int(
                    update.get(
                        "update_id",
                        0,
                    )
                )

                offset = max(
                    offset,
                    update_id + 1,
                )

                try:
                    process_update(
                        update
                    )

                except Exception as exc:

                    print(
                        f"❌ Update "
                        f"{update_id} error: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

                    message = (
                        update.get(
                            "message"
                        )
                        or {}
                    )

                    chat_id = (
                        (
                            message.get(
                                "chat"
                            )
                            or {}
                        ).get(
                            "id"
                        )
                    )

                    if chat_id:
                        try:
                            send_message(
                                chat_id,
                                "⚠️ Errore nella "
                                "gestione della richiesta:\n"
                                f"{exc}",
                            )

                        except Exception as send_exc:
                            print(
                                "❌ Error sending "
                                f"error message: "
                                f"{send_exc}"
                            )

                finally:
                    write_offset(
                        offset
                    )

                    print(
                        f"💾 Offset salvato: "
                        f"{offset}"
                    )

        except requests.RequestException as exc:

            print(
                "⚠️ Telegram network error | "
                f"{exc}"
            )

            time.sleep(3)

        except Exception as exc:

            print(
                "⚠️ Telegram polling error | "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            time.sleep(3)

    write_offset(
        offset
    )

    print(
        "🏁 Listener terminato | "
        f"Prossimo offset: {offset}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )