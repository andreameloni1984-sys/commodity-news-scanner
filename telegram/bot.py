"""
SOYUZ GAGARIN — Telegram interface

Comandi principali:
    /start /help /ping /status /id
    /classifica /setup /analisi /prezzo
    /segnali /top /guida /rischio
    /aggressivo212 /soft212 /prezzo212
    /invest /invest_demo /invest_account /invest_orders /invest_buy

PAPER ONLY.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from engine.gagarin import analyze_universe
from commodities.universe import enabled_commodities, get_commodity_by_name
from engine.invest import (
    analyze_invest_universe,
    format_invest_report,
    get_trading212_demo_status,
    format_account_status,
    format_pending_orders,
    place_demo_order,
)

API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 30

_LAST_RESULTS = None
_LAST_ANALYSIS_TIME = None

def set_last_results(results):
    global _LAST_RESULTS, _LAST_ANALYSIS_TIME
    _LAST_RESULTS = results
    _LAST_ANALYSIS_TIME = time.time()

def get_last_results():
    return _LAST_RESULTS

def _api(method: str, payload: Optional[dict] = None) -> tuple[bool, dict]:
    if not TELEGRAM_BOT_TOKEN:
        return False, {"description": "TELEGRAM_BOT_TOKEN_MISSING"}
    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, json=payload or {}, timeout=REQUEST_TIMEOUT)
        try:
            data = response.json()
        except ValueError:
            data = {"description": response.text[:500]}
        return response.status_code == 200 and bool(data.get("ok")), data
    except requests.RequestException as exc:
        return False, {"description": f"NETWORK_ERROR: {exc}"}

def telegram_diagnostic() -> bool:
    """Verifica il bot Telegram. Richiesta da render_runner."""
    ok, data = _api("getMe")
    if not ok:
        print(f"Telegram DIAGNOSTIC FAILED | {data.get('description', 'unknown')}", flush=True)
        return False
    result = data.get("result", {})
    print(f"Telegram DIAGNOSTIC OK | bot=@{result.get('username', 'unknown')} | id={result.get('id', 'unknown')}", flush=True)
    print("Telegram CHAT ID: " + ("PRESENT" if TELEGRAM_CHAT_ID else "MISSING"), flush=True)
    return True

def send_telegram(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    text = str(message)
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] or [""]
    for chunk in chunks:
        ok, data = _api("sendMessage", {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "disable_web_page_preview": True,
        })
        if not ok:
            return False
    return True

def _reply(chat_id, text: str, reply_markup: Optional[dict] = None) -> bool:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    ok, _ = _api("sendMessage", payload)
    return ok

def _run_analysis(commodity=None):
    commodities = enabled_commodities()
    if commodity is not None:
        commodities = [c for c in commodities if c.name.lower() == commodity.name.lower()]
    if not commodities:
        return None
    results = analyze_universe(commodities)
    set_last_results(results)
    return results

def _resolve_commodity(name: str):
    key = " ".join(str(name or "").strip().split()).lower()
    if not key:
        return None
    for commodity in enabled_commodities():
        if commodity.name.lower() == key or commodity.symbol.lower() == key:
            return commodity
    aliases = {
        "oro": "Oro", "gold": "Oro",
        "argento": "Argento", "silver": "Argento",
        "wti": "Petrolio WTI", "brent": "Petrolio Brent",
        "zucchero": "Zucchero", "cacao": "Cacao", "caffe": "Caffè",
    }
    canonical = aliases.get(key)
    if canonical is None:
        return None
    return get_commodity_by_name(canonical)

def _format_classifica(results):
    if not results:
        return "📊 CLASSIFICA GAGARIN\nNessun risultato disponibile."
    lines = ["🚀 SOYUZ GAGARIN", "📊 CLASSIFICA", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    for index, state in enumerate(results, start=1):
        direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "—"
        lines.append(
            f"{index}. {state.commodity} | {direction} | "
            f"Confluence {state.probability:.1f} | Q {state.quality:.1f} | "
            f"C {state.confidence:.1f} | {state.final_decision}"
        )
    entries = [s for s in results if s.final_decision == "ENTRY"]
    lines.append("")
    lines.append("🎯 OPERATIVITÀ")
    lines.append(f"🟢 {len(entries)} ENTRATA/E AUTORIZZATA/E" if entries else "🟡 NESSUNA ENTRATA AUTORIZZATA")
    return "\n".join(lines)

def _command_response(command: str) -> Optional[str]:
    raw = command.strip()
    button_commands = {
        "🏆 classifica": "/classifica",
        "🎯 setup": "/setup",
        "🔥 top": "/top",
        "📊 analisi": "/analisi",
        "💰 prezzi": "/prezzo",
        "📡 segnali": "/segnali",
        "📖 guida": "/guida",
        "⚠️ rischio": "/rischio",
        "🔄 aggiorna": "/analisi",
        "⚙️ stato": "/status",
    }
    raw = button_commands.get(raw.lower(), raw)
    parts = raw.split()
    if not parts:
        return None
    command_name = parts[0].lower()
    if "@" in command_name:
        command_name = command_name.split("@", 1)[0]
    argument = " ".join(parts[1:]).strip()

    if command_name in {"/start", "/help"}:
        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧪 PAPER ONLY\n\n"
            "/classifica — classifica completa\n"
            "/setup — setup e trigger\n"
            "/analisi — analisi completa\n"
            "/prezzo — prezzi e provider\n"
            "/status — stato bot\n"
            "/ping — verifica collegamento\n"
            "/segnali — signal board\n"
            "/top — top setup\n"
            "/guida — guida canale\n"
            "/rischio — regole di rischio\n"
            "/aggressivo212 — confronto Trading 212 CFD\n"
            "/invest — sezione Invest (azioni/ETF)\n"
            "/invest_demo — stato API Trading 212 demo\n"
            "/invest_account — saldo demo\n"
            "/invest_orders — ordini demo pendenti\n"
            "/invest_buy TICKER QTY — ordine market demo"
        )

    if command_name == "/invest":
        signals = analyze_invest_universe()
        return format_invest_report(signals)

    if command_name == "/invest_demo":
        return get_trading212_demo_status()

    if command_name == "/invest_account":
        return format_account_status()

    if command_name == "/invest_orders":
        return format_pending_orders()

    if command_name == "/invest_buy":
        parts = argument.split()
        if len(parts) < 2:
            return "Uso: /invest_buy TICKER QTY\nEsempio: /invest_buy AAPL_US_EQ 1"
        ticker = parts[0].upper()
        try:
            qty = float(parts[1])
        except ValueError:
            return "Quantità non valida."
        return place_demo_order(ticker, qty)

    if command_name == "/classifica":
        results = get_last_results() or _run_analysis()
        return _format_classifica(results)

    if command_name == "/analisi":
        commodity = _resolve_commodity(argument) if argument else None
        results = _run_analysis(commodity)
        if not results:
            return "Nessun risultato."
        if commodity:
            state = results[0]
            direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "—"
            price = "N/D" if state.price is None else f"{state.price:.6g}"
            return (
                f"🛰 SOYUZ GAGARIN — {state.commodity.upper()}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🧪 PAPER ONLY\n\n"
                f"Prezzo: {price}\n"
                f"Direzione: {direction}\n"
                f"Confluence: {state.probability:.1f} / 100\n"
                f"Quality: {state.quality:.1f}\n"
                f"Confidence: {state.confidence:.1f}\n"
                f"Decisione: {state.final_decision}"
            )
        return _format_classifica(results)

    if command_name == "/status":
        return "Bot attivo. PAPER ONLY. Sezione Invest disponibile."

    if command_name == "/ping":
        return "pong"

    return None

def handle_update(update: dict) -> None:
    message = update.get("message") or {}
    text = message.get("text", "")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or not chat_id:
        return
    response = _command_response(text)
    if response:
        _reply(chat_id, response)
