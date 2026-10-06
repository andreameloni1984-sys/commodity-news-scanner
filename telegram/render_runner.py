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
from soyuz_gagarin.adapter import evaluate_states
from soyuz_gagarin.mt5_bridge import build_demo_payloads

DEFAULT_PORT = 10000
WEBHOOK_PATH = "/telegram/webhook"


def prepare_webhook() -> bool:
    external_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")

    if not external_url:
        print(
            "Telegram WEBHOOK FAILED | RENDER_EXTERNAL_URL_MISSING",
            flush=True,
        )
        return False

    webhook_url = external_url + WEBHOOK_PATH

    print(
        "Telegram WEBHOOK | registering...",
        flush=True,
    )

    ok, data = _api(
        "setWebhook",
        {
            "url": webhook_url,
            "allowed_updates": ["message"],
            "drop_pending_updates": False,
        },
    )

    if not ok:
        print(
            "Telegram WEBHOOK FAILED | "
            f"{data.get('description', 'unknown error')}",
            flush=True,
        )
        return False

    print(
        f"Telegram WEBHOOK OK | {webhook_url}",
        flush=True,
    )

    # ---------------------------------------------------------
    # DIAGNOSTICA WEBHOOK
    # Non stampa mai il token Telegram.
    # ---------------------------------------------------------

    info_ok, info = _api("getWebhookInfo")

    if info_ok:
        result = info.get("result", {})

        safe_url = result.get("url", "")
        pending = result.get("pending_update_count", 0)

        last_error = result.get("last_error_message")
        last_error_date = result.get("last_error_date")

        print(
            "Telegram WEBHOOK INFO | "
            f"url={safe_url} | "
            f"pending={pending} | "
            f"last_error={last_error or 'NONE'} | "
            f"last_error_date={last_error_date or 'NONE'}",
            flush=True,
        )

        if result.get("ip_address"):
            print(
                "Telegram WEBHOOK INFO | "
                f"ip_address={result.get('ip_address')}",
                flush=True,
            )

        if result.get("max_connections"):
            print(
                "Telegram WEBHOOK INFO | "
                f"max_connections={result.get('max_connections')}",
                flush=True,
            )

    else:
        print(
            "Telegram WEBHOOK INFO FAILED | "
            f"{info.get('description', 'unknown error')}",
            flush=True,
        )

    return True


def handle_update(update: dict) -> None:
    try:
        message = update.get("message") or {}
        chat = message.get("chat") or {}

        chat_id = chat.get("id")
        text = message.get("text", "")

        if chat_id is None or not text:
            return

        print(
            "Telegram webhook command | "
            f"chat_id={chat_id} | text={text}",
            flush=True,
        )

        response = _command_response(text)

        if response:
            _reply(chat_id, response, reply_markup=telegram_menu())

        elif text.lower().startswith("/id"):
            _reply(
                chat_id,
                f"🆔 CHAT ID: {chat_id}",
                reply_markup=telegram_menu(),
            )

        else:
            print(
                f"Telegram webhook | unknown command: {text}",
                flush=True,
            )

    except Exception as exc:
        print(
            "Telegram webhook handler error | "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


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