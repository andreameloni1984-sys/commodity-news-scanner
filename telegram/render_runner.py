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

from telegram.bot import _api, _command_response, _reply, telegram_diagnostic, _run_analysis, get_last_results
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

    while True:
        try:
            signals = analyze_invest_universe()
            candidates = [s for s in signals if s.direction == "LONG"]
            if candidates:
                best = candidates[0]
                print(
                    f"Invest SCAN | LONG={len(candidates)} | best={best.ticker} "
                    f"score={best.score:.1f} price={best.price} | NO ORDER (read-only monitor)",
                    flush=True,
                )
            else:
                print("Invest SCAN | no confirmed LONG | NO ORDER (read-only monitor)", flush=True)
        except Exception as exc:
            print(f"Invest SCAN error | {type(exc).__name__}: {exc}", flush=True)
        time.sleep(INVEST_AUTO_INTERVAL)

