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

from telegram.bot import _api, _command_response, _reply, telegram_diagnostic

DEFAULT_PORT = 10000
WEBHOOK_PATH = "/telegram/webhook"


def prepare_webhook() -> bool:
    external_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not external_url:
        print("Telegram WEBHOOK FAILED | RENDER_EXTERNAL_URL_MISSING")
        return False

    webhook_url = external_url + WEBHOOK_PATH
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
            f"{data.get('description', 'unknown error')}"
        )
        return False

    print(f"Telegram WEBHOOK OK | {webhook_url}")
    return True


def handle_update(update: dict) -> None:
    try:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = message.get("text", "")

        if chat_id is None or not text or not text.startswith("/"):
            return

        print(
            "Telegram webhook command | "
            f"chat_id={chat_id} | text={text}"
        )

        response = _command_response(text)

        if response:
            _reply(chat_id, response)
        elif text.lower().startswith("/id"):
            _reply(chat_id, f"🆔 CHAT ID: {chat_id}")
        else:
            print(f"Telegram webhook | unknown command: {text}")

    except Exception as exc:
        print(
            "Telegram webhook handler error | "
            f"{type(exc).__name__}: {exc}"
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
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            self._send_text(200, "OK")
        elif path == "/":
            self._send_text(
                200,
                "🚀 SOYUZ GAGARIN TELEGRAM ONLINE\nWebhook: ACTIVE\n",
            )
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

            print(
                "Telegram webhook received | "
                f"update_id={update.get('update_id')}"
            )

            dispatch_update(update)
            self._send_text(200, "OK")

        except Exception as exc:
            print(
                "Telegram webhook POST error | "
                f"{type(exc).__name__}: {exc}"
            )
            try:
                self._send_text(400, "BAD REQUEST")
            except Exception:
                pass

    def log_message(self, format, *args) -> None:
        return


def main() -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 SOYUZ GAGARIN TELEGRAM")
    print("🧪 PAPER ONLY")
    print("📡 MODE: TELEGRAM WEBHOOK")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if not telegram_diagnostic():
        raise RuntimeError("Telegram configuration invalid")

    port = int(os.getenv("PORT", str(DEFAULT_PORT)))

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthHandler,
    )

    print(f"🌐 HTTP server: 0.0.0.0:{port}")
    print("🟢 Render HTTP: ONLINE")

    if not prepare_webhook():
        server.server_close()
        raise RuntimeError("Telegram webhook registration failed")

    print("🟢 Telegram webhook: ACTIVE")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
