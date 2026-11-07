"""
SOYUZ GAGARIN
Render Telegram Webhook Runner
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from telegram.bot import _api, _command_response, _reply, telegram_diagnostic, _run_analysis, telegram_menu, send_telegram
from telegram.news_monitor import news_monitor_loop
from soyuz_gagarin.adapter import evaluate_states
from engine.cloud_api_status import attach_runtime_decision_metadata
from config import TELEGRAM_CHAT_ID

DEFAULT_PORT = 10000
WEBHOOK_PATH = "/telegram/webhook"


def prepare_webhook() -> bool:
    external_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not external_url:
        print("Telegram WEBHOOK FAILED | RENDER_EXTERNAL_URL_MISSING", flush=True)
        return False

    webhook_url = external_url + WEBHOOK_PATH
    for attempt in range(1, 4):
        print(f"Telegram WEBHOOK | registering attempt={attempt}", flush=True)
        ok, data = _api("setWebhook", {
            "url": webhook_url,
            "allowed_updates": ["message"],
            "drop_pending_updates": False,
        })
        if not ok:
            print(f"Telegram WEBHOOK FAILED | {data.get('description', 'unknown error')}", flush=True)
            time.sleep(2)
            continue

        time.sleep(1)
        info_ok, info = _api("getWebhookInfo")
        result = info.get("result", {}) if info_ok else {}
        actual_url = (result.get("url") or "").rstrip("/")
        if info_ok and actual_url == webhook_url:
            print(f"Telegram WEBHOOK VERIFIED | {webhook_url} | attempt={attempt}", flush=True)
            return True

        print(
            "Telegram WEBHOOK VERIFY FAILED | "
            f"expected={webhook_url} | actual={actual_url or 'EMPTY'} | "
            f"attempt={attempt}",
            flush=True,
        )
        time.sleep(3)

    print("Telegram WEBHOOK FAILED | URL_NOT_PERSISTING", flush=True)
    return False


def run_directional_analysis():
    """Run the selected commodity analysis and attach the canonical Governor result."""
    states = _run_analysis(on_demand=False)
    if not states:
        return states
    decisions = evaluate_states(states)
    by_symbol = {decision.symbol: decision for decision in decisions}
    for state in states:
        decision = by_symbol.get(str(getattr(state, "symbol", "")).upper())
        attach_runtime_decision_metadata(state, decision)
    return states


def handle_update(update: dict) -> None:
    try:
        message = update.get("message") or {}
        chat = message.get("chat") or {}

        chat_id = chat.get("id")
        text = message.get("text", "")

        if chat_id is None or not text:
            return

        button_commands = {
            "📊 CLASSIFICA": "/classifica",
            "🛰 ANALISI": "/analisi",
            "📅 CALENDARIO": "/calendario",
        }
        original_text = text.strip()
        normalized = " ".join(original_text.upper().split())
        text = button_commands.get(normalized, original_text)

        if not text.startswith("/"):
            _reply(chat_id, "Comando non riconosciuto. Usa /classifica, /analisi, /calendario oppure /help.")
            return

        print(
            "Telegram webhook command | "
            f"chat_id={chat_id} | text={original_text} | routed={text}",
            flush=True,
        )

        command_name = text.strip().split("@", 1)[0].lower()

        heavy_commands = {"/analisi", "/classifica", "/calendario"}
        if command_name in heavy_commands:
            _reply(
                chat_id,
                "🛰 GAGARIN — RICHIESTA RICEVUTA\n"
                "Sto elaborando i dati di mercato. Ti invio il risultato appena termina l'analisi."
            )

        response = _command_response(text)

        if response:
            reply_markup = telegram_menu() if command_name in {"/start", "/help", "/menu"} else None
            delivered = _reply(chat_id, response, reply_markup=reply_markup)
            print(
                "Telegram delivery | "
                f"command={command_name} | delivered={'YES' if delivered else 'NO'}",
                flush=True,
            )

        elif text.lower().startswith("/id"):
            _reply(chat_id, f"🆔 CHAT ID: {chat_id}")

        else:
            print(f"Telegram webhook | unsupported command: {text}", flush=True)
            _reply(
                chat_id,
                "⚠️ Comando non disponibile. Usa /aggressivo212, /soft212, /analisi, /classifica oppure /help.",
            )

    except Exception as exc:
        print(
            "Telegram webhook handler error | "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        try:
            if chat_id is not None:
                _reply(
                    chat_id,
                    "❌ GAGARIN non ha completato la richiesta. "
                    f"Errore: {type(exc).__name__}. Riprova con /status o /analisi."
                )
        except Exception:
            pass


def dispatch_update(update: dict) -> None:
    threading.Thread(
        target=handle_update,
        args=(update,),
        name="telegram-update",
        daemon=True,
    ).start()


class HealthHandler(BaseHTTPRequestHandler):

    def _send_text(self, status: int, body: str) -> None:
        data = body.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            self._send_text(200, "OK")
        elif path == "/":
            self._send_text(200, "🚀 SOYUZ GAGARIN TELEGRAM ONLINE\nWebhook: ACTIVE\n")
        else:
            self._send_text(404, "NOT FOUND")

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        self.send_response(200 if path in {"/", "/health"} else 404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

    def do_POST(self) -> None:
        if urlparse(self.path).path != WEBHOOK_PATH:
            self._send_text(404, "NOT FOUND")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self._send_text(400, "EMPTY BODY")
                return

            raw = self.rfile.read(length)
            update = json.loads(raw.decode("utf-8"))

            if not isinstance(update, dict):
                self._send_text(400, "INVALID UPDATE")
                return

            print(f"Telegram webhook received | update_id={update.get('update_id')}", flush=True)
            dispatch_update(update)
            self._send_text(200, "OK")

        except Exception as exc:
            print(f"Telegram webhook POST error | {type(exc).__name__}: {exc}", flush=True)
            try:
                self._send_text(400, "BAD REQUEST")
            except Exception:
                pass

    def log_message(self, format, *args) -> None:
        return


def main() -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
    print("🚀 SOYUZ GAGARIN TELEGRAM", flush=True)
    print("🧪 PAPER ONLY", flush=True)
    print("📡 MODE: TELEGRAM WEBHOOK", flush=True)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    if not telegram_diagnostic():
        raise RuntimeError("Telegram configuration invalid")

    port = int(os.getenv("PORT", str(DEFAULT_PORT)))

    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🌐 HTTP server: 0.0.0.0:{port}", flush=True)
    print("🟢 Render HTTP: ONLINE", flush=True)

    if not prepare_webhook():
        server.server_close()
        raise RuntimeError("Telegram webhook registration failed")

    print("🟢 Telegram webhook: ACTIVE", flush=True)

    commands_ok, commands_data = _api("setMyCommands", {"commands": [
        {"command": "classifica", "description": "Direzione delle otto materie prime"},
        {"command": "analisi", "description": "Analisi generale o di una materia prima"},
        {"command": "calendario", "description": "Calendario economico macro"},
        {"command": "status", "description": "Stato del bot"},
        {"command": "help", "description": "Comandi disponibili"},
    ]})
    print(f"Telegram commands menu | configured={'YES' if commands_ok else 'NO'}", flush=True)

    threading.Thread(
        target=news_monitor_loop,
        args=(send_telegram, run_directional_analysis),
        name="gagarin-news-monitor",
        daemon=True,
    ).start()
    print("Gagarin NEWS monitor | interval=60s | PAPER/DEMO | event-triggered analysis", flush=True)


    if TELEGRAM_CHAT_ID:
        welcome_sent = _reply(
            TELEGRAM_CHAT_ID,
            "🚀 GAGARIN ONLINE\n🧪 ANALISI DIREZIONALE — PAPER ONLY.\n\nUsa CLASSIFICA, ANALISI o CALENDARIO.",
            reply_markup=telegram_menu(),
        )
        print(
            "Telegram startup welcome | "
            f"chat_configured=YES | delivered={'YES' if welcome_sent else 'NO'}",
            flush=True,
        )
    else:
        print("Telegram startup welcome | chat_configured=NO", flush=True)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
