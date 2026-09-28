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
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


# ============================================================
# PROJECT ROOT
# ============================================================

# Render esegue:
#
#     python telegram/render_runner.py
#
# In questo caso Python può mettere la cartella "telegram"
# nel sys.path invece della root del progetto.
#
# Aggiungiamo esplicitamente la root del repository così
# l'import "telegram.bot" viene risolto correttamente.

ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# ============================================================
# TELEGRAM IMPORT
# ============================================================

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
    Endpoint HTTP minimale richiesto da Render
    per il Web Service.
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
        format,
        *args,
    ) -> None:
        """
        Evita di riempire i log Render
        con le normali richieste HTTP.
        """

        return


# ============================================================
# HEALTH SERVER
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
    Avvia:

    1. HTTP health server in background
    2. Telegram long polling permanente
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

    # --------------------------------------------------------
    # HEALTH SERVER
    # --------------------------------------------------------

    health_thread = threading.Thread(
        target=run_health_server,
        name="render-health-server",
        daemon=True,
    )

    health_thread.start()

    print(
        "🟢 Health server thread started"
    )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    print(
        "📡 Starting Telegram polling..."
    )

    run_polling()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()