"""
SOYUZ GAGARIN
Render Telegram Runner

Avvia contemporaneamente:

1. Un piccolo HTTP server sulla porta PORT
   richiesta da Render Web Service.

2. Il listener Telegram permanente tramite
   telegram.bot.run_polling().

Uso:
    python telegram/render_runner.py
"""

from __future__ import annotations

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram.bot import run_polling


# ============================================================
# CONFIG
# ============================================================

DEFAULT_PORT = 10000


# ============================================================
# HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    """
    Endpoint HTTP minimale per mantenere il Web Service
    compatibile con Render.
    """

    def do_GET(self) -> None:
        body = (
            "🚀 SOYUZ GAGARIN TELEGRAM ONLINE\n"
            "Telegram listener: ACTIVE\n"
        ).encode("utf-8")

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.end_headers()

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        """
        Evita di riempire i log di Render con richieste HTTP
        normali.
        """

        return


# ============================================================
# START HEALTH SERVER
# ============================================================

def run_health_server() -> None:
    """
    Avvia il server HTTP richiesto da Render.
    """

    port = int(
        os.getenv(
            "PORT",
            str(DEFAULT_PORT),
        )
    )

    server = HTTPServer(
        (
            "0.0.0.0",
            port,
        ),
        HealthHandler,
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "🚀 SOYUZ GAGARIN"
    )

    print(
        f"🌐 Health server: 0.0.0.0:{port}"
    )

    print(
        "🟢 Render HTTP: ONLINE"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    server.serve_forever()


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Avvia il server HTTP in background e successivamente
    il listener Telegram permanente.
    """

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "🚀 SOYUZ GAGARIN TELEGRAM"
    )

    print(
        "🧪 PAPER ONLY"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    health_thread = threading.Thread(
        target=run_health_server,
        name="render-health-server",
        daemon=True,
    )

    health_thread.start()

    print(
        "🟢 Health server thread started"
    )

    print(
        "📡 Starting Telegram polling..."
    )

    run_polling()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()