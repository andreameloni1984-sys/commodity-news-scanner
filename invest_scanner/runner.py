"""One-shot research runner. No broker orders, polling or public journal writes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from .core import select_setup, top_two
from .data import universe, chart
from .news import collect_news


def scan(bot, now=None, universe_loader=universe, price_loader=chart, news_loader=collect_news):
    if bot not in {"gagarin", "sputnik"}:
        raise ValueError("Unknown bot")
    now = now or datetime.now(timezone.utc)
    instruments, catalog_status = universe_loader()
    news, source_status = news_loader(instruments, now)
    selected = instruments if bot == "gagarin" else [i for i in instruments if news.get(i.symbol)]
    candidates, reasons = [], {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(price_loader, i.symbol): i for i in selected}
        for future in as_completed(futures):
            instrument = futures[future]
            try:
                candidate, reason = select_setup(instrument, future.result(), now, news.get(instrument.symbol, []), bot == "sputnik")
            except Exception as exc:
                candidate, reason = None, "DATI_NON_DISPONIBILI:" + type(exc).__name__
            reasons[instrument.symbol] = reason
            if candidate:
                candidates.append(candidate)
    unavailable = sum(v.startswith("DATI_NON_DISPONIBILI") for v in reasons.values())
    return {
        "bot": bot, "generated_at": now.isoformat(), "mode": "RESEARCH_ONLY",
        "universe_count": len(instruments), "price_scans": len(selected),
        "catalog_status": catalog_status, "source_status": source_status,
        "health": ("CATALOG_EMPTY" if not instruments else "SOURCE_ERROR" if bot == "sputnik" and not any("articoli esaminati" in d for d in source_status) else "DATA_ERROR" if selected and unavailable == len(selected) else "OK"),
        "candidates": top_two(candidates), "diagnostics": reasons,
        "method": "LONG: breakout 20 M5 + VWAP sessione + EMA20 + momentum 15m; punteggio non probabilistico",
    }


def format_report(report):
    lines = [f"{report['bot'].upper()} — INVEST LONG", "Ricerca/demo • nessun ordine automatico",
             report["catalog_status"], f"Titoli nel paniere: {report['universe_count']}; analizzati: {report['price_scans']}"]
    if report.get("health", "OK") != "OK":
        lines.append("Scansione incompleta: " + report["health"])
    if not report["candidates"]:
        lines.append("Nessun candidato LONG con conferma sufficiente in questa scansione.")
    for c in report["candidates"]:
        exit_time = datetime.fromisoformat(c["exit_before"]).astimezone(ZoneInfo("Europe/Rome"))
        lines.extend([
            "", f"{c['symbol']} — {c['name']} | LONG | {c['eligibility']}",
            f"Riferimento {c['entry_reference']:.2f} {c['currency']} • Stop {c['stop']:.2f} • Target {c['target']:.2f}",
            f"Rischio prezzo {c['risk_pct']:.2f}% • obiettivo 2R prima dei costi",
            f"Breakout M5; sopra VWAP/EMA20; momentum 15m {c['momentum_15m_pct']:+.3f}%",
            f"Prezzo del {c['quote_time']} • chiusura intraday entro {exit_time:%H:%M} ora italiana",
            "Livelli indicativi: confrontare prezzo e costi nell'app prima dell'ingresso.",
        ])
        for n in c["news"]:
            lines.extend([f"Fonte primaria: {n['title'][:180]}", n["url"], n["interpretation"]])
    return "\n".join(lines)


def send_report(report, state_path, sender=None):
    """Only eligible candidates; dedup per symbol/session after confirmed delivery.

    Read-only research candidates without account catalog verification never
    produce an actionable Telegram alert. No zero-candidate heartbeat spam.
    """
    path = Path(state_path)
    state = json.loads(path.read_text()) if path.exists() else {}
    day = datetime.fromisoformat(report["generated_at"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
    state = {k: v for k, v in state.items() if k.startswith(day + ":")}
    fresh = [c for c in report["candidates"] if c["eligibility"].startswith("PRESENTE_CATALOGO_") and f"{day}:{c['symbol']}" not in state]
    if not fresh:
        return False
    fresh = fresh[:max(0, 2 - len(state))]
    if not fresh:
        return False
    message = format_report(dict(report, candidates=fresh))
    if sender is None:
        token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            raise ValueError("Configurazione Telegram mancante")
        def sender(message):
            data = urlencode({"chat_id": chat_id, "text": message, "disable_web_page_preview": "true"}).encode()
            req = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
            with urlopen(req, timeout=15) as response:
                return json.loads(response.read())
    result = sender(message)
    message_id = (result.get("result") or {}).get("message_id")
    if result.get("ok") is not True or type(message_id) is not int or message_id <= 0:
        raise RuntimeError("Telegram non ha confermato la consegna")
    for c in fresh:
        state[f"{day}:{c['symbol']}"] = {"message_id": message_id, "digest": hashlib.sha256(message.encode()).hexdigest()}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state))
    temp.replace(path)
    return True


def main(default_bot=None):
    parser = argparse.ArgumentParser(description="Invest research scanner (no orders)")
    parser.add_argument("bot", nargs="?", default=default_bot or "gagarin", choices=("gagarin", "sputnik"))
    parser.add_argument("--notify", action="store_true", help="Send eligible new research candidates to configured Telegram chat")
    parser.add_argument("--state", default=".invest-state/delivery.json")
    args = parser.parse_args()
    try:
        report = scan(args.bot)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(format_report(report))
        if args.notify:
            send_report(report, args.state)
        return 1 if report["health"] != "OK" else 0
    except Exception as exc:
        # Do not leak credentials embedded in request URLs or exception details.
        print(f"INVEST ERROR: {type(exc).__name__}; nessun segnale inviato")
        return 1
