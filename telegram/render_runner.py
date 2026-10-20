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

from telegram.bot import _api, _command_response, _reply, telegram_diagnostic, _run_analysis, get_last_results, telegram_menu, send_telegram
from telegram.news_monitor import news_monitor_loop
from config import TELEGRAM_CHAT_ID
from soyuz_gagarin.adapter import evaluate_states
from soyuz_gagarin.mt5_bridge import build_demo_payloads

DEFAULT_PORT = 10000
WEBHOOK_PATH = "/telegram/webhook"
INVEST_AUTO_INTERVAL = 15 * 60  # 15 minuti


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


def invest_auto_loop() -> None:
    """Controllo periodico in sola lettura: non invia ordini in automatico."""
    from engine.invest import analyze_invest_universe, trading212_demo_available
    from engine.trading212_demo import get_account_summary

    print("Invest AUTO monitor started | interval=15min | READ ONLY | DEMO ONLY", flush=True)
    if trading212_demo_available():
        ok, data = get_account_summary()
        if ok:
            print("Trading212 DEMO API connectivity: OK (account summary read-only)", flush=True)
        else:
            err = data.get("error", data.get("message", "API_ERROR")) if isinstance(data, dict) else "API_ERROR"
            print(f"Trading212 DEMO API connectivity: FAILED | {str(err)[:180]}", flush=True)
    else:
        print("Trading212 DEMO API connectivity: NOT CONFIGURED (credentials missing)", flush=True)

    # Ricontrolla l'autenticazione almeno ogni ora; solo GET account summary.
    last_t212_check = time.monotonic()
    t212_check_interval = 60 * 60

    while True:
        try:
            now = time.monotonic()
            if now - last_t212_check >= t212_check_interval:
                last_t212_check = now
                if trading212_demo_available():
                    auth_ok, auth_data = get_account_summary()
                    if auth_ok:
                        print("Trading212 DEMO hourly auth check: OK (read-only)", flush=True)
                    else:
                        auth_err = auth_data.get("error", auth_data.get("message", "API_ERROR")) if isinstance(auth_data, dict) else "API_ERROR"
                        print(f"Trading212 DEMO hourly auth check: FAILED | {str(auth_err)[:180]}", flush=True)
                else:
                    print("Trading212 DEMO hourly auth check: NOT CONFIGURED", flush=True)

            signals = analyze_invest_universe()
            candidates = [s for s in signals if s.direction == "LONG"]
            if candidates:
                best = candidates[0]
                print(
                    f"Invest SCAN | LONG={len(candidates)} | best={best.ticker} "
                    f"score={best.score:.1f} price={best.price}",
                    flush=True,
                )
            else:
                print("Invest SCAN | no confirmed LONG", flush=True)

            # Automated buying is opt-in and strictly DEMO-only. Default remains OFF.
            if os.getenv("T212_AUTO_BUY_ENABLED", "0").strip() == "1":
                from engine.invest import auto_buy_best_signal_budget
                result = auto_buy_best_signal_budget(amount=10.0, min_score=50.0)
                print("Invest AUTO BUY | " + result.replace("\n", " | ")[:900], flush=True)
                if "ORDINE DEMO INVIATO" in result:
                    send_telegram(result)
        except Exception as exc:
            print(f"Invest SCAN error | {type(exc).__name__}: {exc}", flush=True)
        time.sleep(INVEST_AUTO_INTERVAL)


def position_monitor_loop() -> None:
    """Periodic forecast and position monitor; Telegram is transition-only."""
    from engine.position_monitor import evaluate_positions, list_positions
    from telegram.commodity_direction_alert import run_directional_commodity_alert
    from telegram.aggressive_alert import run_aggressive_alert

    interval = 15 * 60
    print("Gagarin market monitor | interval=15min | deduplicated forecast + position alerts", flush=True)
    while True:
        try:
            states = _run_analysis()
            if states:
                # Score old paper forecasts first, then register newly approved
                # forecasts from this exact market snapshot. The tracker never
                # changes the governor decision or sends routine Telegram alerts.
                try:
                    from engine.feedback import record_entries, summarize, update_open_outcomes
                    decisions = evaluate_states(states)
                    by_symbol = {decision.symbol: decision for decision in decisions}
                    for state in states:
                        decision = by_symbol.get(str(getattr(state, "symbol", "")).upper())
                        metadata = getattr(state, "metadata", None)
                        if not isinstance(metadata, dict):
                            metadata = {}
                            state.metadata = metadata
                        metadata["gagarin_action"] = decision.action if decision else "WAIT"
                        metadata["gagarin_reason"] = decision.reason if decision else "NO_DECISION"
                    updated = update_open_outcomes(states)
                    recorded = record_entries(states)
                    summary = summarize()
                    print(
                        "GAGARIN FEEDBACK | "
                        f"updated={updated} new={recorded} total={summary['total']} "
                        f"closed={summary['closed']} open={summary['open']} "
                        f"win_rate={summary['win_rate_pct']} avg_R={summary['average_r']} "
                        f"total_R={summary['realized_r']}",
                        flush=True,
                    )
                except Exception as feedback_exc:
                    print(
                        f"GAGARIN FEEDBACK ERROR | {type(feedback_exc).__name__}: {feedback_exc}",
                        flush=True,
                    )
                # New/meaningfully changed directional forecasts only; no no-signal heartbeat.
                run_directional_commodity_alert(states)
                # Pattern/exit alerts run in the actual Render service, not only in GitHub Actions.
                run_aggressive_alert(states)
                if list_positions():
                    for alert in evaluate_positions(states):
                        if send_telegram(alert):
                            print("Gagarin position monitor | transition alert delivered", flush=True)
                        else:
                            print("Gagarin position monitor | transition alert delivery failed", flush=True)
        except Exception as exc:
            # Diagnostics only: never send routine error/status spam to Telegram.
            print(f"Gagarin market monitor error | {type(exc).__name__}: {exc}", flush=True)
        time.sleep(interval)


def handle_update(update: dict) -> None:
    try:
        message = update.get("message") or {}
        chat = message.get("chat") or {}

        chat_id = chat.get("id")
        text = message.get("text", "")

        if chat_id is None or not text:
            return

        button_commands = {
            "🚀 AGGRESSIVE 212": "/aggressivo212",
            "🛡 SOFT 212": "/soft212",
            "🔗 COLLEGAMENTO INVEST TRADING212": "/collegamento212",
        }
        original_text = text.strip()
        normalized = " ".join(original_text.upper().split())
        text = button_commands.get(normalized, original_text)

        if text == original_text and normalized.startswith("🚀 AGGRESSIVE 212"):
            text = "/aggressivo212"
        elif text == original_text and normalized.startswith("🛡 SOFT 212"):
            text = "/soft212"
        elif text == original_text and normalized.startswith("🔗 COLLEGAMENTO INVEST TRADING212"):
            text = "/collegamento212"

        if not text.startswith("/"):
            _reply(chat_id, "Comando non riconosciuto. Usa /aggressivo212, /soft212, /analisi, /classifica oppure /help.")
            return

        print(
            "Telegram webhook command | "
            f"chat_id={chat_id} | text={original_text} | routed={text}",
            flush=True,
        )

        command_name = text.strip().split("@", 1)[0].lower()

        heavy_commands = {
            "/aggressivo", "/aggressive", "/aggressivo212", "/soft212", "/analisi", "/top", "/classifica",
            "/setup", "/intraday", "/comprare", "/compra", "/cosa",
            "/cosacomprare", "/qualeccompro", "/quale", "/compro",
            "/segnali", "/perche", "/perché", "/prezzo", "/metalli",
            "/petrolio", "/agri", "/macro", "/fasceorario",
        }
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

        if path == "/mt5/paper":
            try:
                results = get_last_results() or _run_analysis()
                if not results:
                    self._send_text(200, json.dumps({
                        "paper_only": True,
                        "execution": "DISABLED",
                        "signal": False,
                        "reason": "NO_RESULTS",
                    }))
                    return

                decisions = evaluate_states(results)
                payloads = build_demo_payloads(decisions)

                if not payloads:
                    self._send_text(200, json.dumps({
                        "paper_only": True,
                        "execution": "DISABLED",
                        "signal": False,
                        "reason": "NO_PAPER_SIGNAL",
                    }))
                    return

                self._send_text(200, json.dumps(payloads[0]))
            except Exception as exc:
                print(f"MT5 bridge error | {type(exc).__name__}: {exc}", flush=True)
                self._send_text(500, json.dumps({
                    "paper_only": True,
                    "execution": "DISABLED",
                    "signal": False,
                    "reason": "BRIDGE_ERROR",
                }))
            return

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
        {"command": "aggressivo212", "description": "Profilo AGGRESSIVE 212"},
        {"command": "soft212", "description": "Profilo SOFT 212"},
        {"command": "collegamento212", "description": "Stato collegamento Invest Trading 212"},
        {"command": "fasceorario", "description": "Statistiche delle tre fasce orarie"},
        {"command": "monitora", "description": "Registra una posizione per avvisi di rischio"},
        {"command": "posizioni", "description": "Elenca le posizioni monitorate"},
        {"command": "smetti", "description": "Disattiva il monitor di una posizione"},
    ]})
    print(f"Telegram commands menu | configured={'YES' if commands_ok else 'NO'}", flush=True)

    # Monitor NEWS indipendente: controlla le fonti ogni minuto e avvia
    # l'analisi Gagarin fuori ciclo solo per eventi nuovi e rilevanti.
    threading.Thread(
        target=news_monitor_loop,
        args=(send_telegram, _run_analysis),
        name="gagarin-news-monitor",
        daemon=True,
    ).start()
    print("Gagarin NEWS monitor | interval=60s | PAPER/DEMO | event-triggered analysis", flush=True)

    # Avvia i monitor indipendenti; il monitor posizioni invia soltanto cambi di stato rilevanti.
    threading.Thread(
        target=invest_auto_loop,
        name="invest-auto",
        daemon=True,
    ).start()
    threading.Thread(
        target=position_monitor_loop,
        name="gagarin-position-monitor",
        daemon=True,
    ).start()

    if TELEGRAM_CHAT_ID:
        welcome_sent = _reply(
            TELEGRAM_CHAT_ID,
            "🚀 GAGARIN ONLINE\n🧪 PAPER/DEMO — nessun ordine reale.\n\nUsa uno dei tre pulsanti:\n• AGGRESSIVE 212\n• SOFT 212\n• COLLEGAMENTO INVEST TRADING212",
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
