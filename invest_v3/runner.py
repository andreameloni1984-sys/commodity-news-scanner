"""Gagarin INVEST Demo worker. Run one process per PRAVDA database."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import time
from pathlib import Path

from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

import exchange_calendars

from invest_v2.gagarin_runner import send_telegram, session_open
from invest_v2.us_market_data import AlpacaData

from .demo import Demo
from .engine import HORIZONS, RANK, evaluate, message
from .journal import Journal
from .news import CATALYST_FEEDS, Event, FEEDS, feed_items, fetch, reviews, sec_directory
from .scan import (EXPECTED_ERRORS, build_rows, check_market, error_label,
                   expectations_from, macro_releases)


UNIVERSE_TTL = timedelta(hours=24)
MACRO_INTERVAL = timedelta(minutes=15)
SIGNAL_WINDOW = timedelta(hours=1)
CANDIDATE_LIFETIME = timedelta(hours=2, minutes=15)  # signal window + 60 min PRAVDA follow-up
MAX_CANDIDATES = 12
MAX_MESSAGES = 3
DEFAULT_USER_AGENT = "Gagarin/3 (https://github.com/andreameloni1984-sys/commodity-news-scanner)"


def utcnow():
    return datetime.now(timezone.utc)


def news_cutoff(now, opened):
    """60 minutes, or since the previous close during the first session hour.

    Most earnings and guidance releases come out pre-market or after the close:
    they are evaluated in the first hour of the next session instead of being lost.
    """
    if opened is not None and now - opened <= timedelta(hours=1):
        return exchange_calendars.get_calendar("XNYS").previous_close(opened).to_pydatetime()
    return now - timedelta(hours=1)


def read_sources(now, directory, user_agent, sources, *, cutoff=None, include_excluded=True):
    """Fetch all feeds in parallel. Returns (reviewed, statuses, raw items per source)."""
    def load(row):
        source, url, configured = row
        try:
            data = fetch(url, user_agent)
            atom = source == "SEC EDGAR"
            items = list(reviews(data, source=source, now=now, directory=directory,
                                 configured_symbol=configured, atom=atom, cutoff=cutoff,
                                 include_excluded=include_excluded))
            raw = list(feed_items(data, atom=atom)) if source in ("BEA", "Federal Reserve") else []
            return source, url, items, raw, None
        except EXPECTED_ERRORS as exc:
            return source, url, [], [], error_label(exc)

    reviewed, statuses, raw_sources = [], {}, {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for source, url, items, raw, error in pool.map(load, sources):
            reviewed.extend(items)
            statuses[url] = {"source": source, "error": error} if error else {"source": source, "items": len(items)}
            if raw:
                raw_sources.setdefault(source, []).extend(raw)
    return reviewed, statuses, raw_sources


def event_key(event):
    published = event.published.astimezone(timezone.utc).isoformat()
    headline = re.sub(r"[^a-z0-9]+", " ", event.title.lower()).strip()
    return hashlib.sha256(f"{event.symbol}|{published[:10]}|{headline}".encode()).hexdigest()


def window_start(event, opened):
    """The 60-minute signal window starts at publication or at the session open."""
    return max(event.published, opened)


class Worker:
    def __init__(self, demo, market, journal, publish, user_agent, extra_feeds, expectations=None):
        self.demo, self.market, self.journal = demo, market, journal
        self.publish, self.user_agent = publish, user_agent
        self.sources = [(name, FEEDS[name], None) for name in CATALYST_FEEDS] + extra_feeds
        self.expectations = expectations
        self.universe = {}
        self.stats = {}

    def cached(self, name, now, max_age, loader):
        """Persistent cache; a failed refresh falls back to the stale copy."""
        value, fresh = self.journal.cached(name, now, max_age)
        if fresh:
            return value
        try:
            value = loader()
            self.journal.store(name, now, value)
        except EXPECTED_ERRORS as exc:
            self.journal.error(now, name, error_label(exc))
            if value is None:
                raise
        return value

    def discover(self, now, opened):
        self.universe = self.cached("universe", now, UNIVERSE_TTL, self.demo.universe)
        if not self.universe:
            raise ValueError("Nessuno strumento Demo compatibile con il feed USA")
        try:
            directory = {int(cik): symbol for cik, symbol in
                         self.cached("sec_directory", now, UNIVERSE_TTL,
                                     lambda: sec_directory(self.user_agent)).items()}
        except EXPECTED_ERRORS:
            directory = {}
        reviewed, statuses, _ = read_sources(now, directory, self.user_agent, self.sources,
                                             cutoff=news_cutoff(now, opened), include_excluded=False)
        for status in statuses.values():
            if "error" in status:
                self.journal.error(now, status["source"], status["error"])
        added = 0
        for event, reason in reviewed:
            if reason or event.symbol not in self.universe:
                continue
            payload = asdict(event)
            payload["published"] = event.published.astimezone(timezone.utc).isoformat()
            payload["detected"] = event.detected.isoformat()
            self.journal.add(event_key(event), payload,
                             window_start(event, opened) + CANDIDATE_LIFETIME)
            added += 1
        self.stats.update(notizie=len(reviewed), catalizzatori=added)

    def monitor(self, now, opened):
        due, symbols = [], set()
        for row in self.journal.active(now):
            event = json.loads(row[1])
            symbol = event["symbol"]
            if symbol not in self.universe:
                continue
            first, entry, observations, outcome = row[3], row[4], json.loads(row[6]), row[7]
            published = datetime.fromisoformat(event["published"])
            fresh = now - max(published, opened) <= SIGNAL_WINDOW
            following = first and (len(observations) < len(HORIZONS) or (entry and not outcome))
            if not fresh and not following:
                continue
            if symbol not in symbols and len(symbols) >= MAX_CANDIDATES:
                continue
            due.append((row, event))
            symbols.add(symbol)
        series = self.market.bars(sorted(symbols), start=opened, end=now) if symbols else {}
        ranked = []
        for row, values in due:
            key, _, _, first, entry, notified, observations, outcome = row
            for field in ("published", "detected"):
                values[field] = datetime.fromisoformat(values[field])
            event = Event(**values)
            bars = series.get(event.symbol, [])
            self.journal.follow(key, bars, json.loads(first or "null"), json.loads(entry or "null"),
                                json.loads(observations), json.loads(outcome or "null"), now)
            if now - window_start(event, opened) > SIGNAL_WINDOW:
                continue
            signal, reason = evaluate(event, bars, now)
            if signal is None:
                self.journal.record(key, {"reason": reason, "at": now.isoformat()})
                continue
            signal["signaled_at"] = now.isoformat()
            signal["historical"] = self.journal.comparable(key, event)
            self.journal.record(key, signal)
            previous = json.loads(notified or "null") or {}
            if RANK[signal["state"]] > RANK.get(previous.get("state"), 0):
                ranked.append((event, key, signal))
        sent = 0
        for event, key, signal in sorted(ranked, key=lambda row: -row[2]["heuristic_score"])[:MAX_MESSAGES]:
            if self.publish(message(event, self.universe[event.symbol][1], signal, utcnow())):
                self.journal.notified(key, signal)
                sent += 1
            else:
                self.journal.error(now, "Telegram", "Consegna non confermata")
        self.stats.update(candidati=len(due), segnali=sent)

    def collect_macro(self, now):
        _, fresh = self.journal.cached("macro_checked", now, MACRO_INTERVAL)
        if fresh:
            return
        sources = [(source, FEEDS[source], None) for source in ("BEA", "Federal Reserve") if source in FEEDS]
        _, statuses, items = read_sources(now, {}, self.user_agent, sources, include_excluded=False)
        for status in statuses.values():
            if "error" in status:
                self.journal.error(now, status["source"], status["error"])
        try:
            expectations = expectations_from(self.expectations)
        except EXPECTED_ERRORS as exc:
            self.journal.error(now, "attese macro", error_label(exc))
            expectations = []
        releases, macro_statuses = macro_releases(fetch, self.user_agent, items, expectations)
        self.journal.record_macro(releases)
        for source, status in macro_statuses.items():
            if status != "letto":
                self.journal.error(now, source, status)
        self.journal.store("macro_checked", now, True)

    def poll(self):
        """One cycle: news -> selection -> analysis -> Telegram -> PRAVDA."""
        started = time.monotonic()
        now = utcnow()
        opened = session_open(now)
        self.stats = {}
        if opened is None:
            print("Gagarin: seduta XNYS chiusa, nessuna chiamata esterna", flush=True)
            return True
        ok = True
        try:
            self.discover(now, opened)
            self.monitor(now, opened)
        except EXPECTED_ERRORS as exc:
            self.journal.error(now, "ciclo", error_label(exc))
            self.stats["errore"] = str(exc) if isinstance(exc, ValueError) else error_label(exc)
            ok = False
        self.collect_macro(now)
        self.stats["secondi"] = round(time.monotonic() - started, 2)
        print("Gagarin: " + json.dumps(self.stats, ensure_ascii=False), flush=True)
        return ok


def telegram_credentials():
    return os.getenv("GAGARIN_TELEGRAM_TOKEN"), os.getenv("GAGARIN_TELEGRAM_CHAT_ID")


def check_telegram(token, chat):
    """Read-only Telegram check: bot token valid and chat reachable. Sends no message."""
    if not token or not chat:
        raise ValueError("Secret Telegram mancanti")
    result = {}
    for method, params in (("getMe", {}), ("getChat", {"chat_id": chat})):
        try:
            with urlopen(f"https://api.telegram.org/bot{token}/{method}?{urlencode(params)}",
                         timeout=10) as response:
                reply = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"Telegram {method}: HTTP {exc.code}") from None
        except (OSError, ValueError):
            # The URL contains the token: never print the original exception.
            raise RuntimeError(f"Telegram {method}: errore di rete") from None
        if reply.get("ok") is not True:
            raise RuntimeError(f"Telegram {method}: risposta non valida")
        result[method] = reply["result"].get("username") or reply["result"].get("type")
    return {"bot": result["getMe"], "chat": result["getChat"]}


def configured_demo():
    return Demo(os.getenv("GAGARIN_DEMO_KEY"), os.getenv("GAGARIN_DEMO_SECRET"))


def configured_market():
    return AlpacaData(os.getenv("GAGARIN_ALPACA_KEY"), os.getenv("GAGARIN_ALPACA_SECRET"),
                      os.getenv("GAGARIN_ALPACA_FEED") or "iex")


def extra_feeds():
    return [(item["source"], item["url"], item.get("symbol"))
            for item in json.loads(os.getenv("GAGARIN_EXTRA_FEEDS", "[]"))]


def scan_report(user_agent, extra, expectations):
    now = utcnow()
    report = {"started_at": now.isoformat(), "trading_212_demo": {}, "alpaca": {}}
    universe = market = None
    try:
        demo = configured_demo()
        universe = demo.universe()
        report["trading_212_demo"]["strumenti_usa"] = len(universe)
        demo.check_account()
        report["trading_212_demo"]["lettura_conto"] = "verificata"
    except EXPECTED_ERRORS as exc:
        report["trading_212_demo"]["errore"] = str(exc) if isinstance(exc, ValueError) else error_label(exc)
    try:
        probe = configured_market()
        report["alpaca"] = check_market(probe, universe or {}, utcnow(), session_open(utcnow()))
        market = probe
    except EXPECTED_ERRORS as exc:
        report["alpaca"]["errore"] = str(exc) if isinstance(exc, ValueError) else error_label(exc)
    try:
        directory = sec_directory(user_agent)
        report["sec_directory"] = {"cik_univoci": len(directory)}
    except EXPECTED_ERRORS as exc:
        directory = {}
        report["sec_directory"] = {"errore": error_label(exc)}
    opened = session_open(now)
    feeds = [(source, url, None) for source, url in FEEDS.items()] + extra
    reviewed, report["feeds"], sources = read_sources(now, directory, user_agent, feeds,
                                                      cutoff=news_cutoff(now, opened))
    report["macro"], report["macro_sources"] = macro_releases(fetch, user_agent, sources, expectations)
    report["seduta_xnys"] = "aperta" if opened else "chiusa"
    rows = build_rows(reviewed, universe=universe, market=market, opened=opened, clock=utcnow)
    report["news"] = rows
    report["notizie_lette"] = len(rows)
    report["ticker_selezionati"] = sorted({row["symbol"] for row in rows if row["selected"]})
    report["segnali"] = sum(bool(row.get("signal")) for row in rows)
    report["finished_at"] = utcnow().isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--check-demo", action="store_true")
    mode.add_argument("--check-market", action="store_true")
    mode.add_argument("--check-telegram", action="store_true",
                      help="verifica token e chat Telegram senza inviare messaggi")
    mode.add_argument("--scan", action="store_true", help="report di scansione JSON, senza consegne")
    parser.add_argument("--macro-expectations", type=Path)
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()
    simulated = os.getenv("GAGARIN_TELEGRAM_ENABLED") != "true"
    journal_path = args.journal or Path(".gagarin-pravda-sim.sqlite" if simulated else ".gagarin-pravda.sqlite")
    user_agent = os.getenv("GAGARIN_SEC_USER_AGENT") or DEFAULT_USER_AGENT
    if args.report:
        print(json.dumps(Journal(journal_path).report(), ensure_ascii=False, indent=2))
        return
    if args.scan:
        report = scan_report(user_agent, extra_feeds(), expectations_from(args.macro_expectations))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.check_telegram:
        try:
            print(json.dumps(check_telegram(*telegram_credentials())))
        except EXPECTED_ERRORS as exc:
            parser.exit(1, f"{exc}\n")
        return
    if args.check_market:
        try:
            now = utcnow()
            print(json.dumps(check_market(configured_market(), {}, now, session_open(now)), indent=2))
        except EXPECTED_ERRORS as exc:
            parser.exit(1, f"Alpaca: {exc if isinstance(exc, ValueError) else error_label(exc)}\n")
        return
    if args.once and session_open(utcnow()) is None:
        print("Gagarin: seduta XNYS chiusa, nessuna chiamata esterna", flush=True)
        return
    try:
        demo = configured_demo()
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    if args.check_demo:
        try:
            universe = demo.universe()
            positions = demo.check_account()
            if not universe:
                raise RuntimeError("catalogo: nessuno strumento compatibile con il feed USA")
            print(f"Demo: {len(universe)} strumenti USA compatibili, "
                  f"{positions} posizioni. Lettura del saldo verificata.")
        except EXPECTED_ERRORS as exc:
            parser.exit(1, f"{error_label(exc)}\n")
        return
    try:
        market = configured_market()
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    if simulated:
        def publish(text):
            print(text, flush=True)
            return True
    else:
        token, chat = telegram_credentials()
        if not token or not chat:
            parser.exit(1, "Secret Telegram mancanti\n")

        def publish(text):
            return send_telegram(text, token=token, chat_id=chat)
    worker = Worker(demo, market, Journal(journal_path), publish, user_agent, extra_feeds(), args.macro_expectations)
    while True:
        success = worker.poll()
        if args.once:
            raise SystemExit(0 if success else 1)
        time.sleep(60)


if __name__ == "__main__":
    main()
