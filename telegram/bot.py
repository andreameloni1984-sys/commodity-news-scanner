"""
SOYUZ GAGARIN — Telegram interface v3.1

Comandi:
    /start
    /help
    /ping
    /status
    /id
    /classifica
    /setup
    /analisi
    /analisi oro
    /analisi argento
    /analisi platino
    /analisi palladio
    /analisi wti
    /analisi brent
    /analisi zucchero
    /prezzo

PAPER ONLY.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

from engine.gagarin import analyze_universe
from commodities.universe import (
    enabled_commodities,
    get_commodity_by_name,
    get_commodity_by_symbol,
)
from soyuz_gagarin.adapter import evaluate_states
from telegram.signals import (
    format_signal_board,
    format_top,
    format_channel_guide,
    format_risk_guide,
)


API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 30
POLL_TIMEOUT = 25


# ============================================================
# CACHE
# ============================================================

_LAST_RESULTS = None
_LAST_ANALYSIS_TIME = None


def set_last_results(results):
    global _LAST_RESULTS
    global _LAST_ANALYSIS_TIME

    _LAST_RESULTS = results
    _LAST_ANALYSIS_TIME = time.time()


def get_last_results():
    return _LAST_RESULTS


# ============================================================
# TELEGRAM API
# ============================================================

def _api(
    method: str,
    payload: Optional[dict] = None,
) -> tuple[bool, dict]:

    if not TELEGRAM_BOT_TOKEN:
        return (
            False,
            {
                "description":
                "TELEGRAM_BOT_TOKEN_MISSING"
            },
        )

    url = (
        f"{API_BASE}/bot"
        f"{TELEGRAM_BOT_TOKEN}/"
        f"{method}"
    )

    try:

        response = requests.post(
            url,
            json=payload or {},
            timeout=REQUEST_TIMEOUT,
        )

        try:
            data = response.json()

        except ValueError:

            data = {
                "description":
                response.text[:500]
            }

        return (
            response.status_code == 200
            and bool(data.get("ok")),
            data,
        )

    except requests.RequestException as exc:

        return (
            False,
            {
                "description":
                f"NETWORK_ERROR: {exc}"
            },
        )


# ============================================================
# DIAGNOSTICA
# ============================================================

def telegram_diagnostic() -> bool:

    ok, data = _api("getMe")

    if not ok:

        print(
            "Telegram DIAGNOSTIC FAILED | "
            f"{data.get('description', 'unknown error')}",
            flush=True,
        )

        return False

    result = data.get(
        "result",
        {},
    )

    print(
        "Telegram DIAGNOSTIC OK | "
        f"bot=@{result.get('username', 'unknown')} | "
        f"id={result.get('id', 'unknown')}",
        flush=True,
    )

    print(
        "Telegram CHAT ID: "
        + (
            "PRESENT"
            if TELEGRAM_CHAT_ID
            else "MISSING"
        ),
        flush=True,
    )

    # Menu comandi ufficiale del bot.
    _api(
        "setMyCommands",
        {
            "commands": [
                {"command": "segnali", "description": "Segnali operativi PAPER"},
                {"command": "top", "description": "Top setup"},
                {"command": "analisi", "description": "Analisi completa"},
                {"command": "classifica", "description": "Classifica Gagarin"},
                {"command": "setup", "description": "Setup e trigger"},
                {"command": "prezzo", "description": "Prezzi e provider"},
                {"command": "guida", "description": "Guida del canale"},
                {"command": "rischio", "description": "Regole di rischio"},
                {"command": "intraday", "description": "Dashboard intraday"},
                {"command": "comprare", "description": "Cosa comprare in PAPER"},
                {"command": "perche", "description": "Perché WAIT/ENTRY"},
                {"command": "status", "description": "Stato bot"},
                {"command": "ping", "description": "Test collegamento"},
            ]
        },
    )

    return True


# ============================================================
# WEBHOOK RESET
# ============================================================

def prepare_long_polling() -> bool:

    ok, data = _api(
        "deleteWebhook",
        {
            "drop_pending_updates": False
        },
    )

    if not ok:

        print(
            "Telegram WEBHOOK RESET FAILED | "
            f"{data.get('description', 'unknown error')}",
            flush=True,
        )

        return False

    print(
        "Telegram WEBHOOK RESET OK",
        flush=True,
    )

    return True


# ============================================================
# SEND MESSAGE
# ============================================================

def send_telegram(
    message: str,
) -> bool:

    if (
        not TELEGRAM_BOT_TOKEN
        or not TELEGRAM_CHAT_ID
    ):

        print(
            "Telegram disabled/not configured.",
            flush=True,
        )

        return False

    text = str(message)

    chunks = [
        text[i:i + 4000]
        for i in range(
            0,
            len(text),
            4000,
        )
    ]

    if not chunks:
        chunks = [""]

    for chunk in chunks:

        ok, data = _api(
            "sendMessage",
            {
                "chat_id":
                TELEGRAM_CHAT_ID,

                "text":
                chunk,

                "disable_web_page_preview":
                True,
            },
        )

        if not ok:

            print(
                "Telegram API: FAILED | "
                f"{data.get('description', 'unknown error')}",
                flush=True,
            )

            return False

    print(
        "Telegram API: OK",
        flush=True,
    )

    return True


# ============================================================
# REPLY
# ============================================================

def _reply(
    chat_id: int | str,
    text: str,
    reply_markup: Optional[dict] = None,
) -> bool:

    ok, data = _api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
            **({"reply_markup": reply_markup} if reply_markup else {}),
        },
    )

    if not ok:

        print(
            "Telegram reply failed | "
            f"{data.get('description', 'unknown error')}",
            flush=True,
        )

    return ok


# ============================================================
# CLASSIFICA
# ============================================================

def _format_classifica(results):

    if not results:

        return (
            "📊 CLASSIFICA GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun risultato disponibile."
        )

    lines = [
        "🚀 SOYUZ GAGARIN",
        "📊 CLASSIFICA",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY",
        "",
    ]

    for index, state in enumerate(
        results,
        start=1,
    ):

        direction = (
            state.setup_direction
            if state.setup_direction
            in {
                "LONG",
                "SHORT",
            }
            else "—"
        )

        lines.append(
            f"{index}. {state.commodity} | "
            f"{direction} | "
            f"Confluence {state.probability:.1f} | "
            f"Q {state.quality:.1f} | "
            f"C {state.confidence:.1f} | "
            f"{state.final_decision}"
        )

    entries = [
        state
        for state in results
        if state.final_decision == "ENTRY"
    ]

    lines.extend([
        "",
        "🎯 OPERATIVITÀ",
    ])

    if not entries:

        lines.append(
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

    else:

        lines.append(
            f"🟢 {len(entries)} "
            f"ENTRATA/E AUTORIZZATA/E"
        )

    return "\n".join(lines)


# ============================================================
# SETUP
# ============================================================

def _format_setup(results):

    if not results:

        return (
            "🎯 SETUP\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun risultato disponibile."
        )

    lines = [
        "🎯 SETUP GAGARIN",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    found = False

    for state in results:

        if state.setup_direction not in {
            "LONG",
            "SHORT",
        }:

            continue

        found = True

        trigger = (
            "✅ CONFERMATO"
            if state.trigger_confirmed
            else "⏳ IN ATTESA"
        )

        lines.extend([
            f"• {state.commodity}",
            f"  Direzione: {state.setup_direction}",
            f"  Setup Q: {state.setup_quality:.1f}",
            f"  Trigger: {trigger}",
            f"  Confluence: {state.probability:.1f}",
            f"  Quality: {state.quality:.1f}",
            f"  Confidence: {state.confidence:.1f}",
            "",
        ])

    if not found:

        lines.append(
            "Nessun setup LONG/SHORT rilevato nel snapshot."
        )
    else:

        lines.insert(2, "🟡 I setup mostrati possono essere IN ATTESA del trigger.")

    return "\n".join(lines)


# ============================================================
# PREZZI
# ============================================================

def _format_prezzi(results):

    if not results:

        return (
            "💰 PREZZI\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Nessun dato disponibile."
        )

    lines = [
        "💰 PREZZI GAGARIN",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for state in results:

        price = (
            "N/D"
            if state.price is None
            else f"{state.price:.6g}"
        )

        status = state.metadata.get(
            "data_status",
            "UNKNOWN",
        )

        provider = (
            state.data_source
            if state.data_source
            else "N/D"
        )

        lines.append(
            f"{state.commodity}: "
            f"{price} | "
            f"{status} | "
            f"{provider}"
        )

    return "\n".join(lines)


# ============================================================
# ANALISI
# ============================================================

def _run_analysis(
    commodity=None,
):

    commodities = enabled_commodities()

    if commodity is not None:

        commodities = [
            c
            for c in commodities
            if c.name.lower()
            == commodity.name.lower()
        ]

    if not commodities:

        return None

    results = analyze_universe(
        commodities
    )

    set_last_results(
        results
    )

    return results


# ============================================================
# RISOLUZIONE COMMODITY
# ============================================================

def _resolve_commodity(name: str):
    """Resolve any enabled commodity from the canonical universe.

    Exact canonical names and symbols are accepted first; common aliases
    remain supported for user-facing Telegram commands.
    """
    key = " ".join(str(name or "").strip().split()).lower()
    if not key:
        return None

    for commodity in enabled_commodities():
        if commodity.name.lower() == key or commodity.symbol.lower() == key:
            return commodity

    aliases = {
        "oro": "Oro", "gold": "Oro",
        "argento": "Argento", "silver": "Argento",
        "platino": "Platino", "platinum": "Platino",
        "palladio": "Palladio", "palladium": "Palladio",
        "wti": "Petrolio WTI", "petrolio": "Petrolio WTI",
        "petrolio wti": "Petrolio WTI",
        "brent": "Petrolio Brent", "petrolio brent": "Petrolio Brent",
        "riso": "Riso", "rice": "Riso",
        "zucchero": "Zucchero", "sugar": "Zucchero",
        "cacao": "Cacao", "cocoa": "Cacao",
        "caffe": "Caffè", "caffè": "Caffè", "coffee": "Caffè",
    }
    canonical = aliases.get(key)
    if canonical is None:
        return None
    return get_commodity_by_name(canonical)


# ============================================================
# FORMAT ANALISI SINGOLA
# ============================================================

def _format_single_analysis(
    state,
):

    direction = (
        state.setup_direction
        if state.setup_direction
        in {
            "LONG",
            "SHORT",
        }
        else "—"
    )

    trigger = (
        "✅ CONFERMATO"
        if state.trigger_confirmed
        else "⏳ IN ATTESA"
    )

    price = (
        "N/D"
        if state.price is None
        else f"{state.price:.6g}"
    )

    lines = [

        f"🛰 SOYUZ GAGARIN — "
        f"{state.commodity.upper()}",

        "━━━━━━━━━━━━━━━━━━━━",

        "🧪 PAPER ONLY",

        "",

        f"Prezzo: {price}",

        f"Direzione: {direction}",

        f"Setup: "
        f"{state.setup or 'NONE'}",

        f"Trigger: {trigger}",

        "",

        f"Confluence score: "
        f"{state.probability:.1f} / 100",

        f"Quality: "
        f"{state.quality:.1f}",

        f"Confidence: "
        f"{state.confidence:.1f}",
        f"ATR: {state.atr:.6g}" if state.atr is not None else "ATR: N/D",
        f"Regime: {state.regime}",
        f"Structure: {state.structure} | MTF: {state.mtf_direction} ({state.mtf_alignment:.0f})",
        f"Setup: {state.setup} | Trigger: {state.trigger}",
        f"Dati: {state.metadata.get('data_status', 'N/D')} | Age: {state.data_age_seconds:.0f}s" if state.data_age_seconds is not None else f"Dati: {state.metadata.get('data_status', 'N/D')}",

        "",
    ]

    if state.entry is not None:
        lines.append(f"ENTRY: {state.entry:.6g}")

    if state.stop is not None:
        lines.append(f"SL: {state.stop:.6g}")

    if state.tp1 is not None:
        lines.append(f"TP1: {state.tp1:.6g}")

    if state.tp2 is not None:
        lines.append(f"TP2: {state.tp2:.6g}")

    if state.tp3 is not None:
        lines.append(f"TP3: {state.tp3:.6g}")

    if state.rr1 is not None:
        lines.append(f"R/R TP1: {state.rr1:.2f}")

    if state.rr2 is not None:
        lines.append(f"R/R TP2: {state.rr2:.2f}")

    if state.rr3 is not None:
        lines.append(f"R/R TP3: {state.rr3:.2f}")

    lines.extend([
        "",
        f"🎯 DECISIONE: "
        f"{state.final_decision}",
    ])

    if state.blockers:

        lines.append("")
        lines.append("⚠️ BLOCKERS:")

        for blocker in state.blockers[:8]:
            lines.append(f"• {blocker}")

    return "\n".join(lines)


# ============================================================
# AUTOTRASPORTO-STYLE DASHBOARD
# ============================================================

def _format_intraday(results):
    if not results:
        return "⚡ INTRADAY\\n━━━━━━━━━━━━━━━━━━━━\\nNessun dato disponibile."

    lines = [
        "⚡ SOYUZ GAGARIN — INTRADAY",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY",
        "",
    ]
    for i, state in enumerate(results[:10], 1):
        direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "WAIT"
        setup = state.setup or "NONE"
        trigger = state.trigger or "NONE"
        decision = state.final_decision
        lines.append(f"{i}. {state.commodity} | {direction}")
        lines.append(f"   {setup} → {trigger} | {decision}")
    lines.append("")
    lines.append("Regola: nessun ingresso senza confluence + trigger + rischio validato.")
    return "\\n".join(lines)


def _format_buy(results):
    if not results:
        return "💰 COSA COMPRARE\\n━━━━━━━━━━━━━━━━━━━━\\nNessun dato disponibile."
    entries = [s for s in results if s.final_decision == "ENTRY"]
    lines = ["💰 COSA COMPRARE", "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY", ""]
    if not entries:
        lines.append("🟡 NESSUNA ENTRATA AUTORIZZATA")
        lines.append("")
        lines.append("Gagarin preferisce WAIT quando il trigger non è sufficientemente confermato.")
        return "\\n".join(lines)
    for state in entries[:3]:
        lines.append(f"🟢 {state.commodity} — {state.setup_direction}")
        lines.append(f"Entry: {state.entry:.6g}" if state.entry is not None else "Entry: N/D")
        lines.append(f"SL: {state.stop:.6g}" if state.stop is not None else "SL: N/D")
        lines.append(f"TP1: {state.tp1:.6g}" if state.tp1 is not None else "TP1: N/D")
        lines.append(f"TP2: {state.tp2:.6g}" if state.tp2 is not None else "TP2: N/D")
        lines.append(f"TP3: {state.tp3:.6g}" if state.tp3 is not None else "TP3: N/D")
        lines.append("")
    return "\\n".join(lines)


def _format_why(results):
    if not results:
        return "❓ PERCHÉ\\n━━━━━━━━━━━━━━━━━━━━\\nNessun dato disponibile."
    ranked = results[:5]
    lines = ["❓ PERCHÉ", "━━━━━━━━━━━━━━━━━━━━", ""]
    for state in ranked:
        direction = state.setup_direction if state.setup_direction in {"LONG", "SHORT"} else "WAIT"
        lines.append(f"• {state.commodity}: {direction}")
        lines.append(f"  Regime: {state.regime} | Structure: {state.structure}")
        lines.append(f"  Setup: {state.setup} | Trigger: {state.trigger}")
        lines.append(f"  Q {state.quality:.0f} | C {state.confidence:.0f} | Decision: {state.final_decision}")
    return "\\n".join(lines)


# ============================================================
# COMMAND RESPONSE
# ============================================================

def _command_response(
    command: str,
) -> Optional[str]:

    raw = command.strip()
    button_commands = {
        "🏆 classifica": "/classifica",
        "🎯 setup": "/setup",
        "🔥 top": "/top",
        "🔥 top opportunità": "/top",
        "📊 analisi": "/analisi",
        "💰 prezzi": "/prezzo",
        "📡 segnali": "/segnali",
        "📖 guida": "/guida",
        "⚠️ rischio": "/rischio",
        "🔄 aggiorna": "/analisi",
        "⚙️ stato": "/status",
        "⚡ intraday": "/intraday",
        "💰 cosa comprare": "/comprare",
        "❓ perché": "/perche",
        "❓ perche": "/perche",
    }
    raw = button_commands.get(raw.lower(), raw)
    parts = raw.split()

    if not parts:
        return None

    command_name = parts[0].lower()

    if "@" in command_name:
        command_name = command_name.split("@", 1)[0]

    argument = " ".join(parts[1:]).strip()

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if command_name in {
        "/start",
        "/help",
    }:

        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧪 PAPER ONLY\n\n"
            "/classifica — classifica completa\n"
            "/setup — setup e trigger\n"
            "/analisi — analisi completa\n"
            "/analisi oro — analisi singola\n"
            "/analisi argento\n"
            "/analisi platino\n"
            "/analisi palladio\n"
            "/analisi wti\n"
            "/analisi brent\n"
            "/analisi zucchero\n"
            "/analisi riso\n"
            "/analisi cacao\n"
            "/analisi caffe\n"
            "/prezzo — prezzi e provider\n"
            "/status — stato bot\n"
            "/ping — verifica collegamento\n"
            "/id — chat ID\n"
            "/segnali — signal board PAPER\n"
            "/top — top setup\n"
            "/guida — come leggere il canale\n"
            "/rischio — regole di rischio\n"
            "/gagarin — Risk Governor PAPER"
        )

    # --------------------------------------------------------
    # INTRADAY DASHBOARD
    # --------------------------------------------------------

    if command_name == "/intraday":
        try:
            results = get_last_results() or _run_analysis()
            return _format_intraday(results)
        except Exception as exc:
            return f"❌ INTRADAY ERROR\\n{type(exc).__name__}: {exc}"

    if command_name in {"/comprare", "/compra"}:
        try:
            results = get_last_results() or _run_analysis()
            return _format_buy(results)
        except Exception as exc:
            return f"❌ BUY BOARD ERROR\\n{type(exc).__name__}: {exc}"

    if command_name in {"/perche", "/perché"}:
        try:
            results = get_last_results() or _run_analysis()
            return _format_why(results)
        except Exception as exc:
            return f"❌ WHY BOARD ERROR\\n{type(exc).__name__}: {exc}"

# --------------------------------------------------------
    # SIGNAL CHANNEL
    # --------------------------------------------------------


    if command_name == "🏆":
        return _command_response("/classifica")

    if command_name in {"/segnali", "📡"}:
        try:
            results = get_last_results() or _run_analysis()
            return format_signal_board(results)
        except Exception as exc:
            return f"❌ SIGNAL ENGINE ERROR\\n{type(exc).__name__}: {exc}"

    if command_name in {"/top", "🔥"}:
        try:
            results = get_last_results() or _run_analysis()
            return format_top(results)
        except Exception as exc:
            return f"❌ TOP ENGINE ERROR\\n{type(exc).__name__}: {exc}"

    if command_name in {"/guida", "📖"}:
        return format_channel_guide()

    if command_name in {"/rischio", "⚠️"}:
        return format_risk_guide()

    # --------------------------------------------------------
    # GAGARIN V1 GOVERNOR
    # --------------------------------------------------------

    if command_name == "/gagarin":
        try:
            results = get_last_results() or _run_analysis()
            if not results:
                return "⚠️ Nessuna commodity disponibile."

            decisions = evaluate_states(results)
            lines = [
                "🚀 SOYUZ GAGARIN v1",
                "━━━━━━━━━━━━━━━━━━━━",
                "🧪 PAPER ONLY",
                "",
            ]
            for decision in decisions:
                lines.append(
                    f"{decision.symbol} | {decision.action} | {decision.reason}"
                )
            return "\n".join(lines)
        except Exception as exc:
            return (
                "❌ GAGARIN GOVERNOR ERROR\n"
                f"{type(exc).__name__}: {exc}"
            )

    # --------------------------------------------------------
    # PING
    # --------------------------------------------------------

    if command_name == "/ping":

        return (
            "🟢 SOYUZ ONLINE\n"
            "Telegram OK\n"
            "Trading: PAPER ONLY"
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if command_name in {"/status", "⚙️"}:

        results = get_last_results()

        if results:

            return (
                "🚀 SOYUZ GAGARIN\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🟢 Telegram: ONLINE\n"
                "🟢 Engine: DISPONIBILE\n"
                "🧪 Trading: PAPER ONLY\n"
                f"📊 Ultima analisi: "
                f"{len(results)} commodity"
            )

        return (
            "🚀 SOYUZ GAGARIN\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 Telegram: ONLINE\n"
            "🟢 Engine: DISPONIBILE\n"
            "🧪 Trading: PAPER ONLY\n"
            "📊 Nessuna analisi in memoria"
        )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    if command_name == "/id":

        return (
            "🆔 Usa il comando /id "
            "direttamente in chat."
        )

    # --------------------------------------------------------
    # CLASSIFICA
    # --------------------------------------------------------

    if command_name in {"/classifica", "🏆"}:

        try:

            results = (
                get_last_results()
                or _run_analysis()
            )

            return _format_classifica(
                results
            )

        except Exception as exc:

            return (
                "❌ ERRORE ANALISI\n"
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    # --------------------------------------------------------
    # SETUP
    # --------------------------------------------------------

    if command_name in {"/setup", "🎯"}:

        try:

            results = (
                get_last_results()
                or _run_analysis()
            )

            return _format_setup(
                results
            )

        except Exception as exc:

            return (
                "❌ ERRORE ANALISI\n"
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    # --------------------------------------------------------
    # PREZZO
    # --------------------------------------------------------

    if command_name in {"/prezzo", "💰"}:

        try:

            results = (
                get_last_results()
                or _run_analysis()
            )

            return _format_prezzi(
                results
            )

        except Exception as exc:

            return (
                "❌ ERRORE ANALISI\n"
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    # --------------------------------------------------------
    # ANALISI
    # --------------------------------------------------------

    if command_name in {"/analisi", "📊", "🔄"}:

        try:

            # /analisi
            # = analisi completa

            if not argument:

                results = _run_analysis()

                if not results:

                    return (
                        "⚠️ Nessuna commodity "
                        "disponibile."
                    )

                return (
                    "🔄 NUOVA ANALISI COMPLETATA\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    + _format_classifica(
                        results
                    )
                )

            # /analisi <commodity>
            # = analisi singola

            commodity = _resolve_commodity(
                argument
            )

            if commodity is None:

                return (
                    "❌ Commodity non riconosciuta.\n\n"
                    "Disponibili:\n"
                    "🥇 Oro\n"
                    "🥈 Argento\n"
                    "⚪ Platino\n"
                    "⚫ Palladio\n"
                    "🛢 WTI\n"
                    "🛢 Brent\n"
                    "🍬 Zucchero\n"
                    "🍚 Riso\n"
                    "🍫 Cacao\n"
                    "☕ Caffè"
                )

            results = _run_analysis(
                commodity
            )

            if not results:

                return (
                    "⚠️ Nessun dato disponibile "
                    f"per {commodity.name}."
                )

            return _format_single_analysis(
                results[0]
            )

        except Exception as exc:

            return (
                "❌ GAGARIN ENGINE ERROR\n"
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    return None


# ============================================================
# POLL ONCE
# ============================================================

def poll_once(
    offset: Optional[int] = None,
    handler: Optional[
        Callable[[dict], None]
    ] = None,
) -> Optional[int]:

    payload = {
        "timeout": POLL_TIMEOUT,
        "allowed_updates": ["message"],
    }

    if offset is not None:
        payload["offset"] = offset

    ok, data = _api(
        "getUpdates",
        payload,
    )

    if not ok:

        print(
            "Telegram getUpdates FAILED | "
            f"{data.get('description', 'unknown error')}",
            flush=True,
        )

        time.sleep(3)

        return offset

    updates = data.get(
        "result",
        [],
    )

    next_offset = offset

    for update in updates:

        update_id = update.get(
            "update_id"
        )

        if isinstance(
            update_id,
            int,
        ):

            next_offset = (
                update_id + 1
            )

        message = (
            update.get("message")
            or {}
        )

        chat = (
            message.get("chat")
            or {}
        )

        chat_id = chat.get(
            "id"
        )

        text = message.get(
            "text",
            "",
        )

        if chat_id is None:
            continue

        if handler is not None:

            try:

                handler(update)

            except Exception as exc:

                print(
                    "Telegram custom handler error | "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

            continue

        if text.startswith("/"):

            if text.lower().startswith(
                "/id"
            ):

                _reply(
                    chat_id,
                    f"🆔 CHAT ID: {chat_id}",
                )

            else:

                response = _command_response(
                    text
                )

                if response:

                    _reply(
                        chat_id,
                        response,
                        reply_markup=telegram_menu() if text.lower() in {"/start", "/help"} else None,
                    )

    return next_offset



def telegram_menu() -> dict:
    return {
        "keyboard": [
            [{"text": "🔥 TOP OPPORTUNITÀ"}, {"text": "🏆 CLASSIFICA"}],
            [{"text": "⚡ INTRADAY"}, {"text": "💰 COSA COMPRARE"}],
            [{"text": "❓ PERCHÉ"}, {"text": "🎯 SETUP"}],
            [{"text": "📊 ANALISI"}, {"text": "📡 SEGNALI"}],
            [{"text": "🔄 AGGIORNA"}, {"text": "⚙️ STATO"}],
            [{"text": "📖 GUIDA"}, {"text": "⚠️ RISCHIO"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "Scegli una sezione GAGARIN",
    }

# ============================================================
# PERMANENT LISTENER
# ============================================================

def run_polling(
    handler: Optional[
        Callable[[dict], None]
    ] = None,
) -> None:

    if not telegram_diagnostic():

        raise RuntimeError(
            "Telegram configuration invalid"
        )

    if not prepare_long_polling():

        raise RuntimeError(
            "Telegram webhook reset failed"
        )

    offset = None

    print(
        "Telegram polling started.",
        flush=True,
    )

    while True:

        offset = poll_once(
            offset=offset,
            handler=handler,
        )


# ============================================================
# REPORT FORMAT
# ============================================================

def format_report(
    results,
):

    return _format_classifica(
        results
    )