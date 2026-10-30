"""
SOYUZ GAGARIN — Telegram interface

Comandi principali:
    /start /help /ping /status /id
    /classifica /setup /analisi /prezzo
    /segnali /top /guida /rischio
    /aggressivo212 /soft212 /prezzo212
    /invest /invest_demo /invest_account /invest_orders /invest_buy /invest_auto

PAPER ONLY.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from engine.gagarin import analyze_universe
from engine.forex_session import filter_forex_for_session
from commodities.universe import enabled_commodities, get_commodity_by_name
from engine.invest import (
    analyze_invest_universe,
    format_invest_report,
    get_trading212_demo_status,
    format_account_status,
    format_pending_orders,
    place_demo_order,
    auto_buy_best_signal,
    auto_buy_best_signal_budget,
)
from engine.daily_forecast import predict_today
from soyuz_gagarin.adapter import evaluate_states

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

def telegram_menu() -> dict:
    """Menu Telegram minimale: i tre comandi richiesti dall'utente."""
    return {
        "keyboard": [
            [{"text": "🚀 AGGRESSIVE 212"}],
            [{"text": "🛡 SOFT 212"}],
            [{"text": "🔗 COLLEGAMENTO INVEST TRADING212"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "one_time_keyboard": False,
    }

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

def _run_analysis(commodity=None, *, on_demand=True):
    commodities = filter_forex_for_session(enabled_commodities(), on_demand=on_demand)
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
        "rame": "Rame", "copper": "Rame",
        "wti": "Petrolio WTI", "brent": "Petrolio Brent",
        "grano": "Grano", "wheat": "Grano",
        "mais": "Mais", "corn": "Mais", "maize": "Mais",
        "soia": "Soia", "soybean": "Soia", "soybeans": "Soia",
    }
    canonical = aliases.get(key)
    if canonical is None:
        return None
    return get_commodity_by_name(canonical)

def _is_auxiliary_forex(state) -> bool:
    return str(getattr(state, "symbol", "") or "").strip().upper() in {
        "EUR/USD", "GBP/USD"
    }


def _format_classifica(results):
    if not results:
        return "📊 CLASSIFICA GAGARIN\nNessun risultato disponibile."
    lines = ["🚀 SOYUZ GAGARIN", "📊 CLASSIFICA", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    for index, state in enumerate(results, start=1):
        direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "—"
        decision_label = (
            "CONTESTO FX — NON OPERATIVO"
            if _is_auxiliary_forex(state)
            else state.final_decision
        )
        lines.append(
            f"{index}. {state.commodity} | {direction} | "
            f"Confluence {state.probability:.1f} | Q {state.quality:.1f} | "
            f"C {state.confidence:.1f} | {decision_label}"
        )
    entries = [
        s for s in results
        if not _is_auxiliary_forex(s) and s.final_decision == "ENTRY"
    ]
    lines.append("")
    lines.append("🎯 OPERATIVITÀ")
    lines.append(f"🟢 {len(entries)} ENTRATA/E AUTORIZZATA/E" if entries else "🟡 NESSUNA ENTRATA AUTORIZZATA")
    return "\n".join(lines)

def _format_setup(results):
    if not results:
        return "📊 SETUP\nNessun risultato disponibile."
    lines = ["🚀 SOYUZ GAGARIN", "📊 SETUP", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    for state in results:
        direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "—"
        if _is_auxiliary_forex(state):
            status = "CONTESTO FX — NON OPERATIVO"
        elif state.setup_direction in {"LONG", "SHORT"} and not getattr(state, "trigger_confirmed", False):
            status = "IN ATTESA"
        elif state.setup_direction in {"LONG", "SHORT"} and getattr(state, "trigger_confirmed", False):
            status = "TRIGGER CONFERMATO"
        else:
            status = "NESSUN SETUP"
        lines.append(
            f"{state.commodity} | {direction} | {status} | "
            f"Setup Q {getattr(state, 'setup_quality', 0):.1f} | "
            f"Confluence {state.probability:.1f} | Q {state.quality:.1f} | C {state.confidence:.1f}"
        )
    return "\n".join(lines)

def _format_intraday(results):
    if not results:
        return "INTRADAY\nNessun risultato disponibile."
    lines = ["🚀 SOYUZ GAGARIN", "INTRADAY", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    for state in results:
        direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "—"
        setup = getattr(state, "setup", "NONE")
        trigger = getattr(state, "trigger", "NONE")
        decision_label = (
            "CONTESTO FX — NON OPERATIVO"
            if _is_auxiliary_forex(state)
            else state.final_decision
        )
        lines.append(
            f"{state.commodity} | {direction} | {setup} | {trigger} | "
            f"{decision_label}"
        )
    return "\n".join(lines)

def _format_buy(results):
    if not results:
        return "GAGARIN — OGGI\nNessun risultato disponibile."
    operational_results = [
        state for state in results if not _is_auxiliary_forex(state)
    ]
    forecast = predict_today(operational_results)
    lines = ["GAGARIN — OGGI", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    # Prediction APIs may return a ranked list; Telegram displays its top candidate.
    if isinstance(forecast, (list, tuple)):
        forecast = forecast[0] if forecast else None
    if forecast is None:
        lines.append("Nessuna previsione disponibile.")
        return "\n".join(lines)
    lines.append(f"COMMODITY: {forecast['commodity']}")
    lines.append(f"PREVISIONE: {forecast['forecast']}")
    lines.append(f"DIREZIONE: {forecast['direction']}")
    if forecast.get("entry") is not None:
        lines.append(f"ENTRY: {forecast['entry']:.6g}")
    if forecast.get("stop") is not None:
        lines.append(f"SL: {forecast['stop']:.6g}")
    if forecast.get("tp1") is not None:
        lines.append(f"TP1: {forecast['tp1']:.6g}")
    if forecast.get("tp2") is not None:
        lines.append(f"TP2: {forecast['tp2']:.6g}")
    return "\n".join(lines)

def _format_morning_pick(results):
    if not results:
        return "GAGARIN — COSA COMPRO?\nNessun risultato disponibile."
    decisions = evaluate_states(results)
    best = None
    for decision in decisions:
        if decision.action == "PAPER_SIGNAL":
            best = decision
            break
    lines = ["GAGARIN — COSA COMPRO?", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    if best is None:
        lines.append("Nessun segnale PAPER disponibile.")
        return "\n".join(lines)
    state = next((s for s in results if str(getattr(s, "symbol", "")).upper() == best.symbol), None)
    if state is None:
        lines.append("Nessun segnale PAPER disponibile.")
        return "\n".join(lines)
    lines.append(f"COMMODITY: {state.commodity}")
    lines.append(f"DIREZIONE: {state.setup_direction}")
    if state.entry is not None:
        lines.append(f"ENTRY: {state.entry:.6g}")
    if state.stop is not None:
        lines.append(f"SL: {state.stop:.6g}")
    if state.tp3 is not None:
        lines.append(f"TP3: {state.tp3:.6g}")
    return "\n".join(lines)

def _command_response(command: str) -> Optional[str]:
    raw = command.strip()

    # Manual position registration enables transition-only post-entry monitoring.
    # Prices are compared with Gagarin's provider feed; this is not a Trading 212 API.
    command_name = raw.split(maxsplit=1)[0].lower() if raw else ""
    if command_name == "/monitora":
        parts = raw.split()
        if len(parts) < 6 or len(parts) > 8:
            return (
                "Uso: /monitora ORO LONG ENTRY SL TP1 [TP2] [TP3]\n"
                "ATTENZIONE: i numeri 2700 2680 2740 sono solo un esempio, NON quotazioni live.\n"
                "Prima usa /analisi oro per vedere il prezzo provider attuale; inserisci poi i livelli della tua posizione.\n"
                "I prezzi inseriti sono confrontati con il feed provider Gagarin, non con il Bid/Ask Trading 212."
            )
        commodity = _resolve_commodity(parts[1])
        if commodity is None:
            return "Commodity non riconosciuta o non abilitata. Usa oro, wti, brent, cacao, caffe, platino, riso o zucchero."
        from engine.position_monitor import register_position
        tp2 = parts[6] if len(parts) >= 7 else None
        tp3 = parts[7] if len(parts) >= 8 else None
        ok, message = register_position(
            symbol=commodity.symbol, commodity=commodity.name,
            direction=parts[2], entry=parts[3], stop=parts[4], tp1=parts[5],
            tp2=tp2, tp3=tp3,
        )
        return message

    if command_name == "/posizioni":
        from engine.position_monitor import list_positions
        positions = list_positions()
        if not positions:
            return "Nessuna posizione monitorata. Registra una con /monitora ORO LONG 2700 2680 2740."
        lines = ["GAGARIN — POSIZIONI MONITORATE", "PAPER/ADVISORY ONLY", ""]
        for p in positions:
            lines.append(
                f"{p.get('commodity')} {p.get('direction')} | Entry {p.get('entry'):g} "
                f"| SL {p.get('stop'):g} | TP1 {p.get('tp1'):g}"
            )
        lines.append("")
        lines.append("Quotazioni provider Gagarin, non Trading 212. Solo avvisi; nessun ordine viene modificato.")
        return "\n".join(lines)

    if command_name in {"/smetti", "/stopmonitore"}:
        parts = raw.split()
        if len(parts) != 2:
            return "Uso: /smetti ORO"
        commodity = _resolve_commodity(parts[1])
        symbol = commodity.symbol if commodity is not None else parts[1].upper()
        from engine.position_monitor import remove_position
        _, message = remove_position(symbol)
        return message
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
        "🚀 aggressive trading 2-1-2": "/aggressivo212",
        "🛡 soft trading 2-1-2": "/soft212",
        "🚀 aggressive 212": "/aggressivo212",
        "🛡 soft 212": "/soft212",
        "🔗 collegamento invest trading212": "/collegamento212",
        "🚀 aggressivo": "/aggressivo212",
        "🛡 soft": "/soft212",
    }
    raw = button_commands.get(raw.lower(), raw)
    parts = raw.split()
    if not parts:
        return None
    command_name = parts[0].lower()
    if "@" in command_name:
        command_name = command_name.split("@", 1)[0]
    argument = " ".join(parts[1:]).strip()

    if command_name in {"/start", "/help", "/menu"}:
        return (
            "🚀 GAGARIN — MENU SEMPLICE\n"
            "🧪 PAPER/DEMO — nessun ordine reale.\n\n"
            "🚀 AGGRESSIVE 212 — profilo aggressivo\n"
            "🛡 SOFT 212 — profilo prudente\n"
            "🔗 COLLEGAMENTO INVEST TRADING212 — verifica sola lettura\n\n"
            "Monitor posizione: /monitora ORO LONG ENTRY SL TP1 [TP2] [TP3]\n"
            "2700/2680/2740 nell'esempio sono valori fittizi: controlla prima /analisi oro.\n"
            "/posizioni — elenco monitorate | /smetti ORO — disattiva monitor.\n"
            "Gli avvisi automatici arrivano solo su nuovi segnali rilevanti o cambi di rischio/target; nessun messaggio di stato ripetitivo."
        )

    if command_name in {"/aggressivo212", "/aggressive212"}:
        try:
            from soyuz_gagarin.aggressive_desk import format_aggressive_desk
            from soyuz_gagarin.trading_profiles import get_profile
            from engine.trading212 import compare_price, format_comparison, parse_bid_ask
            profile = get_profile("AGGRESSIVE")
            results = _run_analysis()
            if results is None:
                return "Nessun risultato. Riprova con /analisi."
            set_last_results(results)
            desk = format_aggressive_desk(results)
            try:
                from cloud_api import FOREX_AGGRESSIVE_PORTFOLIO
                fx = FOREX_AGGRESSIVE_PORTFOLIO.snapshot()
                fx_lines = ["", "FX AGGRESSIVE", "Capitale: " + str(round(fx.get("equity", 100), 2)), "Aperte: " + str(len(fx.get("open_positions", [])))]
                for p in fx.get("open_positions", [])[:5]:
                    fx_lines.append(str(p.get("symbol")) + " " + str(p.get("direction")) + " entry " + str(p.get("entry")))
                desk = desk + "\n" + "\n".join(fx_lines)
            except Exception:
                pass
            if argument:
                bid, ask = parse_bid_ask(argument)
                if bid is not None:
                    sym = None
                    for part in argument.replace(",", ".").split():
                        up = part.upper()
                        if up in {"WTI", "BRENT", "ORO", "ARGENTO", "SPY", "QQQ", "EURUSD", "GBPUSD"}:
                            sym = up
                            break
                    if sym:
                        gprice = None
                        for st in results:
                            if str(getattr(st, "symbol", "")).upper() == sym:
                                gprice = getattr(st, "price", None)
                                break
                        comp = compare_price(sym, gprice, bid, ask)
                        desk = desk + "\n\n" + format_comparison(comp)
                    else:
                        desk = desk + "\n\n212: incolla anche il simbolo, es. /aggressivo212 WTI 78.10 78.13"
                else:
                    desk = desk + "\n\n212: per il confronto incolla bid e ask, es. /aggressivo212 WTI 78.10 78.13"
            else:
                desk = desk + "\n\n212: per confrontare i prezzi Trading 212 incolla bid e ask dopo il comando."
            desk = desk + "\n\nProfilo: probabilita >= " + str(profile.min_probability) + ", qualita >= " + str(profile.min_quality) + ", rischio " + str(profile.risk_per_trade_pct) + "% per operazione, max " + str(profile.max_open_positions) + " posizioni."
            try:
                from research.intraday_windows import format_intraday_window_summary
                desk = desk + "\n\n" + format_intraday_window_summary()
            except Exception as exc:
                desk = desk + "\n\nFasce orarie: dati non disponibili (" + type(exc).__name__ + ")."
            return desk
        except Exception as exc:
            return "Errore reparto aggressive: " + type(exc).__name__ + ": " + str(exc)

    if command_name in {"/soft212", "/soft"}:
        try:
            from soyuz_gagarin.trading_profiles import get_profile
            profile = get_profile("SOFT")
            results = _run_analysis()
            if results is None:
                return "Nessun risultato. Riprova con /analisi."
            set_last_results(results)
            try:
                from research.intraday_windows import format_intraday_window_summary
                window_summary = format_intraday_window_summary()
            except Exception as exc:
                window_summary = "Fasce orarie: dati non disponibili (" + type(exc).__name__ + ")."
            return _format_classifica(results) + "\n\n" + window_summary + "\n\nProfilo SOFT: probabilita >= " + str(profile.min_probability) + ", qualita >= " + str(profile.min_quality) + ", rischio " + str(profile.risk_per_trade_pct) + "%."
        except Exception as exc:
            return "Errore soft: " + type(exc).__name__ + ": " + str(exc)

    if command_name == "/prezzo212":
        try:
            from engine.trading212 import compare_price, format_comparison, parse_bid_ask
            if not argument:
                return "212 PREZZI\nIncolla: simbolo bid ask\nEs: /prezzo212 WTI 78.10 78.13"
            parts = argument.split()
            sym = parts[0].upper()
            bid, ask = parse_bid_ask(" ".join(parts[1:]))
            gprice = None
            results = get_last_results()
            if results:
                for st in results:
                    if str(getattr(st, "symbol", "")).upper() == sym:
                        gprice = getattr(st, "price", None)
                        break
            if gprice is None:
                try:
                    results = _run_analysis()
                    if results:
                        set_last_results(results)
                        for st in results:
                            if str(getattr(st, "symbol", "")).upper() == sym:
                                gprice = getattr(st, "price", None)
                                break
                except Exception:
                    pass
            return format_comparison(compare_price(sym, gprice, bid, ask))
        except Exception as exc:
            return "Errore 212: " + type(exc).__name__ + ": " + str(exc)

    if command_name == "/invest":
        signals = analyze_invest_universe()
        return format_invest_report(signals)

    if command_name in {"/collegamento212", "/collegamento-invest-trading212"}:
        status = get_trading212_demo_status()
        return (
            "🔗 COLLEGAMENTO INVEST TRADING212\n"
            "Verifica sola lettura dell'account DEMO. Nessun ordine viene inviato.\n\n"
            + status
            + "\n\nSe la connessione non è disponibile, controllare le chiavi API INVEST DEMO nelle variabili ambiente del servizio. "
              "Questo pulsante non esegue acquisti."
        )

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

    if command_name == "/invest_buy_value":
        parts = argument.split()
        if len(parts) != 3:
            return "Uso: /invest_buy_value TICKER SIMBOLO IMPORTO\nEsempio: /invest_buy_value NVDA_US_EQ NVDA 10"
        ticker, symbol = parts[0].upper(), parts[1].upper()
        try:
            amount = float(parts[2])
        except ValueError:
            return "Importo non valido."
        from engine.invest import place_demo_order_by_value
        return place_demo_order_by_value(ticker, symbol, amount)

    if command_name == "/invest_auto":
        # Explicit user command: one guarded €10 order at most, INVEST DEMO only.
        return auto_buy_best_signal_budget(amount=10.0, min_score=50.0)

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
                f"Decisione: {'CONTESTO AUSILIARIO — NON OPERATIVO' if _is_auxiliary_forex(state) else state.final_decision}"
            )
        return _format_classifica(results)

    if command_name == "/fasceorario":
        from research.intraday_windows import format_intraday_window_report
        return format_intraday_window_report()

    if command_name == "/status":
        return "Bot attivo. PAPER ONLY. Sezione Invest disponibile."

    if command_name == "/ping":
        return "pong"

    if raw.lower() in {"cosa compro?", "quale compro?", "cosa comprare"}:
        results = get_last_results() or _run_analysis()
        return _format_buy(results)

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


def run_polling() -> None:
    """Backward-compatible Render entry point.

    The Render service historically imports telegram.bot.run_polling.
    The actual bot runtime uses the webhook HTTP server in render_runner.
    """
    from telegram.render_runner import main as webhook_main
    webhook_main()
