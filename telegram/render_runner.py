"""
SOYUZ GAGARIN
Render Telegram Webhook Runner
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from telegram.bot import _api, _command_response, _reply, telegram_diagnostic, _run_analysis, get_last_results, telegram_menu
from config import TELEGRAM_CHAT_ID
from soyuz_gagarin.adapter import evaluate_states
from soyuz_gagarin.mt5_bridge import build_demo_payloads

DEFAULT_PORT = 10000
WEBHOOK_PATH = "/telegram/webhook"


def prepare_webhook() -> bool:
    import time

    external_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not external_url:
        print("Telegram WEBHOOK FAILED | RENDER_EXTERNAL_URL_MISSING", flush=True)
        return False

    webhook_url = external_url + WEBHOOK_PATH
    # Telegram permits only one delivery mode per bot. Register, then verify the
    # actual URL; an API success alone is not proof that the webhook stayed set.
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
            print(
                "Telegram WEBHOOK INFO | "
                f"pending={result.get('pending_update_count', 0)} | "
                f"last_error={result.get('last_error_message') or 'NONE'} | "
                f"last_error_date={result.get('last_error_date') or 'NONE'}",
                flush=True,
            )
            return True

        print(
            "Telegram WEBHOOK VERIFY FAILED | "
            f"expected={webhook_url} | actual={actual_url or 'EMPTY'} | "
            f"attempt={attempt} | "
            f"detail={info.get('description', 'URL mismatch')}",
            flush=True,
        )
        time.sleep(3)

    print("Telegram WEBHOOK FAILED | URL_NOT_PERSISTING; another process may be changing this bot's webhook", flush=True)
    return False


def handle_update(update: dict) -> None:
    try:
        message = update.get("message") or {}
        chat = message.get("chat") or {}

        chat_id = chat.get("id")
        text = message.get("text", "")

        if chat_id is None or not text:
            return

        # Reply-keyboard buttons send plain text, not slash commands.
        button_commands = {
            # Match the exact labels currently shown by telegram_menu().
            "🚀 AGGRESSIVE TRADING 2-1-2": "/aggressivo212",
            "🛡 SOFT TRADING 2-1-2": "/soft212",
            # Keep compatibility with older button labels.
            "🚀 TRADING 2-1-2 AGGRESSIVE": "/aggressivo212",
            "🛡 TRADING 2-1-2 SOFT": "/soft212",
            "🚀 AGGRESSIVO": "/aggressivo",
            "🛡 SOFT": "/soft",
            "🏆 CLASSIFICA": "/classifica",
            "🔄 AGGIORNA": "/analisi",
        }
        original_text = text.strip()
        normalized = " ".join(original_text.upper().split())
        text = button_commands.get(normalized, original_text)

        # Be tolerant of legacy button labels with extra strategy wording.
        if text == original_text:
            if normalized.startswith("🚀 AGGRESSIVO"):
                text = "/aggressivo"
            elif normalized.startswith("🛡 SOFT"):
                text = "/soft"
            elif normalized.startswith("🏆 CLASSIFICA"):
                text = "/classifica"
            elif normalized.startswith("🔄 AGGIORNA"):
                text = "/analisi"

        if not text.startswith("/"):
            _reply(chat_id, "Scegli una voce dal menu GAGARIN oppure usa /start.", reply_markup=telegram_menu())
            return

        print(
            "Telegram webhook command | "
            f"chat_id={chat_id} | text={original_text} | routed={text}",
            flush=True,
        )

        command_name = text.strip().split("@", 1)[0].lower()

        # Acknowledge slow commands before calling market-data providers.
        heavy_commands = {
            "/aggressivo", "/aggressive", "/aggressivo212", "/soft212", "/analisi", "/top", "/classifica",
            "/setup", "/intraday", "/comprare", "/compra", "/cosa",
            "/cosacomprare", "/qualeccompro", "/quale", "/compro",
            "/segnali", "/perche", "/perché", "/prezzo", "/metalli",
            "/petrolio", "/agri", "/macro",
        }
        if command_name in heavy_commands:
            _reply(
                chat_id,
                "🛰️ GAGARIN — RICHIESTA RICEVUTA\n"
                "Sto elaborando i dati di mercato. Ti invio il risultato appena termina l'analisi."
            )

        print(
            "Telegram command processing | "
            f"command={command_name} | phase=START",
            flush=True,
        )
        response = _command_response(text)
        print(
            "Telegram command processing | "
            f"command={command_name} | phase=END | "
            f"response={'YES' if response else 'NO'}",
            flush=True,
        )

        if response:
            # This Render service uses the webhook runner, not run_polling.
            # Attach the persistent keyboard to /start and log Telegram's API result.
            markup = telegram_menu()
            delivered = _reply(chat_id, response, reply_markup=markup)
            print(
                "Telegram delivery | "
                f"command={command_name} | delivered={'YES' if delivered else 'NO'}",
                flush=True,
            )

        elif text.lower().startswith("/id"):
            _reply(
                chat_id,
                f"🆔 CHAT ID: {chat_id}",
            )

        else:
            print(
                f"Telegram webhook | unsupported command: {text}",
                flush=True,
            )
            _reply(
                chat_id,
                "⚠️ Comando non disponibile. Usa i pulsanti Trading 2-1-2 qui sotto oppure /start.",
                reply_markup=telegram_menu(),
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
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(data)),
        )
        self.end_headers()

        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/mt5/paper":
            try:
                results = get_last_results() or _run_analysis()
                if not results:
                    self._send_text(
                        200,
                        json.dumps({
                            "paper_only": True,
                            "execution": "DISABLED",
                            "signal": False,
                            "reason": "NO_RESULTS",
                        }),
                    )
                    return

                decisions = evaluate_states(results)
                payloads = build_demo_payloads(decisions)

                if not payloads:
                    self._send_text(
                        200,
                        json.dumps({
                            "paper_only": True,
                            "execution": "DISABLED",
                            "signal": False,
                            "reason": "NO_PAPER_SIGNAL",
                        }),
                    )
                    return

                self._send_text(200, json.dumps(payloads[0]))
            except Exception as exc:
                print(
                    "MT5 bridge error | "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
                self._send_text(
                    500,
                    json.dumps({
                        "paper_only": True,
                        "execution": "DISABLED",
                        "signal": False,
                        "reason": "BRIDGE_ERROR",
                    }),
                )
            return

        if path == "/health":
            self._send_text(
                200,
                "OK",
            )

        elif path == "/":
            self._send_text(
                200,
                "🚀 SOYUZ GAGARIN TELEGRAM ONLINE\n"
                "Webhook: ACTIVE\n",
            )

        else:
            self._send_text(
                404,
                "NOT FOUND",
            )

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path

        self.send_response(
            200 if path in {"/", "/health"} else 404
        )

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.end_headers()

    def do_POST(self) -> None:

        if urlparse(self.path).path != WEBHOOK_PATH:
            self._send_text(
                404,
                "NOT FOUND",
            )
            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            if length <= 0:
                self._send_text(
                    400,
                    "EMPTY BODY",
                )
                return

            raw = self.rfile.read(length)

            update = json.loads(
                raw.decode("utf-8")
            )

            if not isinstance(update, dict):
                self._send_text(
                    400,
                    "INVALID UPDATE",
                )
                return

            print(
                "Telegram webhook received | "
                f"update_id={update.get('update_id')}",
                flush=True,
            )

            dispatch_update(update)

            self._send_text(
                200,
                "OK",
            )

        except Exception as exc:

            print(
                "Telegram webhook POST error | "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

            try:
                self._send_text(
                    400,
                    "BAD REQUEST",
                )
            except Exception:
                pass

    def log_message(self, format, *args) -> None:
        return


def main() -> None:

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        flush=True,
    )

    print(
        "🚀 SOYUZ GAGARIN TELEGRAM",
        flush=True,
    )

    print(
        "🧪 PAPER ONLY",
        flush=True,
    )

    print(
        "📡 MODE: TELEGRAM WEBHOOK",
        flush=True,
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        flush=True,
    )

    # ---------------------------------------------------------
    # TELEGRAM DIAGNOSTIC
    # ---------------------------------------------------------

    if not telegram_diagnostic():
        raise RuntimeError(
            "Telegram configuration invalid"
        )

    port = int(
        os.getenv(
            "PORT",
            str(DEFAULT_PORT),
        )
    )

    # ---------------------------------------------------------
    # HTTP SERVER
    # ---------------------------------------------------------

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthHandler,
    )

    print(
        f"🌐 HTTP server: 0.0.0.0:{port}",
        flush=True,
    )

    print(
        "🟢 Render HTTP: ONLINE",
        flush=True,
    )

    # ---------------------------------------------------------
    # TELEGRAM WEBHOOK
    # ---------------------------------------------------------

    if not prepare_webhook():

        server.server_close()

        raise RuntimeError(
            "Telegram webhook registration failed"
        )

    print(
        "🟢 Telegram webhook: ACTIVE",
        flush=True,
    )

    # setChatMenuButton configures the commands menu, not the reply keyboard.
    # Send the actual persistent keyboard to the configured chat on startup.
    if TELEGRAM_CHAT_ID:
        keyboard_sent = _reply(
            TELEGRAM_CHAT_ID,
            "🚀 GAGARIN ONLINE — scegli dal menu qui sotto.\n🧪 PAPER ONLY.",
            reply_markup=telegram_menu(),
        )
        print(
            "Telegram startup keyboard | "
            f"chat_configured=YES | delivered={'YES' if keyboard_sent else 'NO'}",
            flush=True,
        )
    else:
        print("Telegram startup keyboard | chat_configured=NO", flush=True)

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        flush=True,
    )

    try:
        server.serve_forever()

    finally:
        server.server_close()


if __name__ == "__main__":
    main()