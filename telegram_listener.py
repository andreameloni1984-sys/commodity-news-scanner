#!/usr/bin/env python3
"""
SOYUZ GAGARIN - Telegram Listener v2

Receives Telegram messages with long polling and translates natural-language
requests into the existing commodity_bot.py request interface.

Supported examples:
    Oro
    Analisi oro
    Prezzo oro
    Scalping oro
    Classifica
    Setup
    Segnali
    /oro
    /analisi oro
    /prezzo oro
    /scalping oro
    /classifica
    /setup
    /segnali
    /help

The listener does NOT change Gagarin entry gates. It only fixes the Telegram
input/transport layer and delegates real analysis to commodity_bot.py.
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


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
STATE_FILE = Path(os.getenv("TELEGRAM_LISTENER_STATE_FILE", "telegram_listener_state.json"))
POLL_TIMEOUT = int(os.getenv("TELEGRAM_POLL_TIMEOUT", "15"))
MAX_RUNTIME = int(os.getenv("TELEGRAM_LISTENER_MAX_SECONDS", "1140"))
ANALYSIS_TIMEOUT = int(os.getenv("TELEGRAM_ANALYSIS_TIMEOUT", "900"))
BASE_URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""

COMMANDS = [
    {"command": "start", "description": "Avvia SOYUZ GAGARIN"},
    {"command": "help", "description": "Mostra i comandi"},
    {"command": "classifica", "description": "Classifica commodity"},
    {"command": "setup", "description": "Migliore setup"},
    {"command": "segnali", "description": "Segnali operativi"},
    {"command": "scalping", "description": "Scalping di una commodity"},
    {"command": "analisi", "description": "Analisi commodity"},
    {"command": "prezzo", "description": "Prezzo live commodity"},
    {"command": "oro", "description": "Analisi Oro"},
    {"command": "argento", "description": "Analisi Argento"},
    {"command": "rame", "description": "Analisi Rame"},
    {"command": "platino", "description": "Analisi Platino"},
    {"command": "palladio", "description": "Analisi Palladio"},
    {"command": "wti", "description": "Analisi WTI"},
    {"command": "brent", "description": "Analisi Brent"},
    {"command": "cacao", "description": "Analisi Cacao"},
    {"command": "caffe", "description": "Analisi Caffè"},
    {"command": "zucchero", "description": "Analisi Zucchero"},
    {"command": "riso", "description": "Analisi Riso"},
    {"command": "soia", "description": "Analisi Soia"},
]

ALIASES = {
    "oro": "Oro", "gold": "Oro", "xau": "Oro", "xauusd": "Oro",
    "argento": "Argento", "silver": "Argento", "xag": "Argento",
    "rame": "Rame", "copper": "Rame", "hg": "Rame",
    "platino": "Platino", "platinum": "Platino", "xpt": "Platino",
    "palladio": "Palladio", "palladium": "Palladio", "xpd": "Palladio",
    "wti": "Petrolio WTI", "petroliowti": "Petrolio WTI", "oilwti": "Petrolio WTI",
    "brent": "Petrolio Brent", "petroliobrent": "Petrolio Brent",
    "cacao": "Cacao", "cocoa": "Cacao",
    "caffe": "Caffè", "coffee": "Caffè",
    "zucchero": "Zucchero", "sugar": "Zucchero",
    "riso": "Riso", "rice": "Riso",
    "soia": "Soia", "soybean": "Soia",
    "mais": "Mais", "corn": "Mais",
    "grano": "Grano", "wheat": "Grano",
    "cotone": "Cotone", "cotton": "Cotone",
    "gasnaturale": "Gas Naturale", "naturalgas": "Gas Naturale", "natgas": "Gas Naturale",
}

COMMAND_ALIASES = {
    "classifica": "CLASSIFICA", "ranking": "CLASSIFICA", "rank": "CLASSIFICA",
    "setup": "SETUP", "miglioresetup": "SETUP", "best": "SETUP",
    "segnali": "SEGNALI", "signals": "SEGNALI",
    "scalping": "SCALPING", "scalp": "SCALPING",
    "analisi": "ANALISI", "analysis": "ANALISI", "commodity": "ANALISI",
    "prezzo": "PREZZO", "price": "PREZZO",
}

HELP_TEXT = (
    "🤖 SOYUZ GAGARIN — COMANDI\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Puoi scrivere anche semplicemente il nome della commodity.\n\n"
    "📊 CLASSIFICA — ranking\n"
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
    "• /oro\n\n"
    "🧪 PAPER ONLY — nessun ordine reale."
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = re.sub(r"[@#]", "", value)
    value = re.sub(r"[/_-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize(value))


def telegram(method: str, payload=None, timeout=30):
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN mancante")
    response = requests.post(
        f"{BASE_URL}/{method}",
        json=payload or {},
        timeout=timeout,
    )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram {method} errore: {data.get('description', response.text)}"
        )
    return data.get("result")


def send_message(chat_id, text):
    text = str(text or "").strip() or "⚠️ Nessuna risposta generata."
    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [" "]
    for chunk in chunks:
        telegram(
            "sendMessage",
            {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
            timeout=30,
        )


def set_commands():
    telegram("setMyCommands", {"commands": COMMANDS}, timeout=30)


def read_offset():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return int(data.get("offset", 0))
    except Exception:
        return 0


def write_offset(offset):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"offset": int(offset)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(STATE_FILE)


def allowed_chat(chat_id):
    if not ALLOWED_CHAT_ID:
        return True
    return str(chat_id) == str(ALLOWED_CHAT_ID)


def find_commodity(text):
    c = compact(text)
    if c in ALIASES:
        return ALIASES[c]
    for alias, name in sorted(ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias and alias in c:
            return name
    return None


def parse_request(text):
    raw = (text or "").strip()
    n = normalize(raw)
    if not n:
        return None, None

    if n.startswith("/"):
        n = n[1:].strip()
        n = n.split("@", 1)[0].strip()

    c = compact(n)

    if c in {"start", "help", "aiuto", "menu", "comandi"}:
        return "HELP", None

    if c in COMMAND_ALIASES:
        return COMMAND_ALIASES[c], None

    commodity = find_commodity(n)

    # "Oro", "Brent", "Cacao", ...
    if commodity and c == compact(commodity):
        return "ANALISI", commodity

    # "Scalping Oro", "Analisi Oro", "Prezzo Oro", ...
    for alias, command in sorted(COMMAND_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if c.startswith(alias):
            remainder = c[len(alias):]
            if remainder:
                found = find_commodity(remainder)
                if found:
                    return command, found

    # "Oro Scalping", "Oro Analisi", "Oro Prezzo"
    if commodity:
        for alias, command in COMMAND_ALIASES.items():
            if c.endswith(alias) and c != alias:
                return command, commodity

    return None, None


def build_env(command, commodity, chat_id, original):
    env = os.environ.copy()
    env.update({
        "RUN_MODE": "ON_DEMAND",
        "REPORT_TYPE": "NONE",
        "REQUEST_TYPE": command,
        "REQUEST_COMMODITY": commodity or "",
        "ON_DEMAND_TELEGRAM_REQUEST": original,
        "ON_DEMAND_TELEGRAM_CHAT_ID": str(chat_id),
        "SILENT_INTERNAL_ANALYSIS": "1",
        "PAPER_TRADING_ONLY": "1",
        "DEMO_TRADING_ENABLED": "0",
    })
    return env


def run_analysis(command, commodity, chat_id, original):
    env = build_env(command, commodity, chat_id, original)

    if command == "SCALPING":
        intro = f"⚡ Analizzo lo scalping di {commodity or 'migliore commodity'}…"
    elif command == "ANALISI":
        intro = f"🔎 Analizzo {commodity or 'la commodity richiesta'}…"
    elif command == "PREZZO":
        intro = f"💰 Recupero il prezzo di {commodity or 'della commodity'}…"
    else:
        intro = "🧠 SOYUZ GAGARIN sta elaborando la richiesta…"

    send_message(chat_id, intro)

    try:
        completed = subprocess.run(
            [sys.executable, "commodity_bot.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=ANALYSIS_TIMEOUT,
        )

        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()
            tail = tail[-2500:] if tail else "errore senza dettagli"
            send_message(
                chat_id,
                "⚠️ Analisi non completata.\n"
                "Il motore non ha prodotto una risposta operativa.\n\n"
                f"Dettaglio tecnico: {tail}",
            )
    except subprocess.TimeoutExpired:
        send_message(
            chat_id,
            "⏱️ Analisi oltre il tempo massimo. "
            "Nessun ordine è stato eseguito: PAPER ONLY.",
        )
    except Exception as exc:
        send_message(chat_id, f"⚠️ Errore Telegram/SOYUZ: {exc}")


def process_update(update):
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text")

    if chat_id is None or not text:
        return

    if not allowed_chat(chat_id):
        send_message(chat_id, "⛔ Chat non autorizzata.")
        return

    command, commodity = parse_request(text)

    if command == "HELP":
        send_message(chat_id, HELP_TEXT)
        return

    if command is None:
        send_message(
            chat_id,
            "❓ Non ho capito la richiesta.\n\n"
            "Prova: Oro, Analisi Oro, Scalping Oro, "
            "Classifica, Setup o Segnali.\n\n"
            "Oppure /help.",
        )
        return

    run_analysis(command, commodity, chat_id, text)


def main():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN mancante.")
        return 2

    print("🤖 Telegram Listener v2 avviato")
    print(f"📌 Chat autorizzata: {ALLOWED_CHAT_ID or 'tutte'}")

    try:
        telegram("deleteWebhook", {"drop_pending_updates": False}, timeout=30)
        set_commands()
        print("✅ Telegram commands registrati")
    except Exception as exc:
        print(f"⚠️ Setup Telegram: {exc}")

    offset = read_offset()
    deadline = time.time() + MAX_RUNTIME

    while time.time() < deadline:
        try:
            updates = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "limit": 20,
                    "timeout": POLL_TIMEOUT,
                    "allowed_updates": ["message"],
                },
                timeout=POLL_TIMEOUT + 10,
            ) or []

            if not updates:
                continue

            for update in updates:
                update_id = int(update.get("update_id", 0))
                offset = max(offset, update_id + 1)

                try:
                    process_update(update)
                except Exception as exc:
                    message = update.get("message") or {}
                    chat_id = (message.get("chat") or {}).get("id")
                    if chat_id:
                        try:
                            send_message(chat_id, f"⚠️ Errore nella richiesta: {exc}")
                        except Exception:
                            pass
                    print(f"❌ Update {update_id}: {exc}")

                write_offset(offset)

        except requests.RequestException as exc:
            print(f"⚠️ Telegram network error: {exc}")
            time.sleep(3)
        except Exception as exc:
            print(f"⚠️ Telegram polling error: {exc}")
            time.sleep(3)

    write_offset(offset)
    print(f"🏁 Listener terminato. Prossimo offset: {offset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
