"""Gagarin INVEST Demo worker. Run one process per PRAVDA database."""
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import time
from pathlib import Path

from invest_v2.gagarin_runner import send_telegram, session_open
from invest_v2.us_market_data import AlpacaData

from .demo import Demo
from .engine import evaluate, message
from .journal import Journal
from .news import Event, FEEDS, PRIMARY, feed_items, fetch, reviews, sec_directory
from .scan import (EXPECTED_ERRORS, build_rows, check_market, error_label,
                   expectations_from, macro_releases)


def utcnow():
    return datetime.now(timezone.utc)


def read_sources(now, directory, user_agent, extra_feeds, backoff, *, collect_macro=False):
    sources = [(source, url, None) for source, url in FEEDS.items()] + extra_feeds
    reviewed, statuses, macro_sources = [], {}, {}
    for source, url, configured in sorted(sources, key=lambda row: row[0] not in PRIMARY):
        if backoff.get(url, now) > now:
            continue
        try:
            data = fetch(url, user_agent)
            atom = source == "SEC EDGAR"
            items = list(reviews(data, source=source, now=utcnow(), directory=directory,
                                 configured_symbol=configured, atom=atom))
            reviewed.extend(items)
            statuses[url] = {"source": source, "items": len(items)}
            if collect_macro and source in ("BEA", "Federal Reserve"):
                macro_sources.setdefault(source, []).extend(feed_items(data, atom=atom))
        except EXPECTED_ERRORS as exc:
            backoff[url] = now + timedelta(minutes=5)
            statuses[url] = {"source": source, "error": error_label(exc)}
    return reviewed, statuses, macro_sources


class Worker:
    def __init__(self, demo, market, journal, publish, user_agent, extra_feeds, expectations=None):
        self.demo, self.market, self.journal = demo, market, journal
        self.publish, self.user_agent = publish, user_agent
        self.extra_feeds = extra_feeds
        self.expectations = expectations
        self.macro_checked = None
        self.universe = {}
        self.directory = {}
        self.directory_refresh = None
        self.refreshed = None
        self.catalog_retry_at = None
        self.last_checked = {}
        self.backoff = {}
        self.market_retry_at = None

    def discover(self, now):
        if self.catalog_retry_at and now < self.catalog_retry_at:
            raise ValueError("Catalogo in attesa di retry")
        if self.refreshed is None or now - self.refreshed >= timedelta(hours=6):
            universe = self.demo.universe()
            if not universe:
                raise ValueError("Nessuno strumento Demo compatibile con il feed USA")
            self.universe = universe
            self.refreshed = now
        if self.directory_refresh is None or now >= self.directory_refresh:
            try:
                self.directory = sec_directory(self.user_agent)
                self.directory_refresh = now + timedelta(hours=6)
            except EXPECTED_ERRORS as exc:
                self.directory_refresh = now + timedelta(minutes=5)
                self.journal.error(now, "SEC ticker directory", error_label(exc))

        macro_due = self.macro_checked is None or now - self.macro_checked >= timedelta(minutes=15)
        reviewed, statuses, macro_sources = read_sources(now, self.directory, self.user_agent,
                                                        self.extra_feeds, self.backoff, collect_macro=macro_due)
        for status in statuses.values():
            if "error" in status:
                self.journal.error(now, status["source"], status["error"])
        if macro_due:
            self.macro_checked = now
            try:
                expectations = expectations_from(self.expectations)
            except EXPECTED_ERRORS as exc:
                self.journal.error(now, "attese macro", error_label(exc))
                expectations = []
            releases, macro_statuses = macro_releases(fetch, self.user_agent, macro_sources, expectations)
            self.journal.record_macro(releases)
            for source, status in macro_statuses.items():
                if status != "letto":
                    self.journal.error(now, source, status)
        for event, reason in reviewed:
            if reason or event.symbol not in self.universe:
                continue
            payload = asdict(event)
            payload["published"] = event.published.astimezone(timezone.utc).isoformat()
            payload["detected"] = event.detected.isoformat()
            headline = re.sub(r"[^a-z0-9]+", " ", event.title.lower()).strip()
            key = hashlib.sha256(f"{event.symbol}|{payload['published'][:10]}|{headline}".encode()).hexdigest()
            self.journal.add(key, payload, event.published.astimezone(timezone.utc) + timedelta(hours=2))

    def monitor(self, now):
        opened = session_open(now)
        if opened is None or (self.market_retry_at and now < self.market_retry_at):
            return
        self.last_checked = {key: at for key, at in self.last_checked.items()
                             if now - at < timedelta(hours=2)}
        due = []
        for row in self.journal.active(now, 80):
            key, raw, latest, first, entry, _, observations, outcome, _ = row
            event = json.loads(raw)
            if event["symbol"] not in self.universe:
                continue
            if latest and json.loads(latest)["state"] == "SCARTARE" and not first:
                continue
            if len(json.loads(observations)) == 4 and (not entry or outcome):
                continue
            if key in self.last_checked and now - self.last_checked[key] < timedelta(minutes=5):
                continue
            due.append(row)
            if len(due) == 12:
                break
        symbols = sorted({json.loads(row[1])["symbol"] for row in due})
        series = self.market.bars(symbols, start=opened,
                                  end=now) if symbols else {}
        ranked = []
        for key, raw, latest, first, entry, notified, observations, outcome, _ in due:
            self.last_checked[key] = now
            values = json.loads(raw)
            for field in ("published", "detected"):
                values[field] = datetime.fromisoformat(values[field])
            event = Event(**values)
            bars = series.get(event.symbol, [])
            self.journal.follow(key, bars, json.loads(first or "null"), json.loads(entry or "null"),
                                json.loads(observations), json.loads(outcome or "null"), now)
            if latest and json.loads(latest)["state"] == "SCARTARE":
                continue
            checked_at = utcnow()
            if session_open(checked_at) != opened or checked_at - event.published > timedelta(hours=1):
                continue
            signal, reason = evaluate(event, bars, checked_at)
            if signal is None:
                self.journal.error(now, event.symbol, reason)
                continue
            signal["signaled_at"] = checked_at.isoformat()
            signal["historical"] = json.loads(latest)["historical"] if latest else self.journal.comparable(key, event)
            previous = json.loads(notified or "null")
            if entry and signal["state"] == "PREPARARE":
                continue
            self.journal.record(key, signal)
            changed = previous is None or (previous["state"], previous["phase"]) != (signal["state"], signal["phase"])
            if changed and (signal["state"] != "SCARTARE" or previous):
                ranked.append((event, key, signal))
        for event, key, signal in sorted(ranked, key=lambda row: -row[2]["heuristic_score"])[:3]:
            delivered_at = utcnow()
            if session_open(delivered_at) != opened or delivered_at - datetime.fromisoformat(signal["quote_at"]) > timedelta(minutes=2):
                continue
            if self.publish(message(event, self.universe[event.symbol][1], signal, delivered_at)):
                self.journal.record(key, signal, notify=True)
            else:
                self.journal.error(delivered_at, "Telegram", "Consegna non confermata")

    def poll(self):
        now = utcnow()
        if self.catalog_retry_at and now < self.catalog_retry_at:
            return False
        try:
            self.discover(now)
        except EXPECTED_ERRORS as exc:
            self.catalog_retry_at = now + timedelta(minutes=5)
            self.journal.error(now, "catalogo Demo", error_label(exc))
            print("Gagarin: catalogo Demo non disponibile", flush=True)
            return False
        try:
            self.monitor(utcnow())
        except EXPECTED_ERRORS as exc:
            self.market_retry_at = now + timedelta(minutes=5)
            self.journal.error(now, "dati mercato", error_label(exc))
            return False
        return True


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
    reviewed, report["feeds"], sources = read_sources(now, directory, user_agent, extra, {}, collect_macro=True)
    report["macro"], report["macro_sources"] = macro_releases(fetch, user_agent, sources, expectations)
    opened = session_open(utcnow())
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
    mode.add_argument("--scan", action="store_true", help="report di scansione JSON, senza consegne")
    parser.add_argument("--macro-expectations", type=Path)
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()
    simulated = os.getenv("GAGARIN_TELEGRAM_ENABLED") != "true"
    journal_path = args.journal or Path(".gagarin-pravda-sim.sqlite" if simulated else ".gagarin-pravda.sqlite")
    if args.report:
        print(json.dumps(Journal(journal_path).report(), indent=2))
        return
    if args.scan:
        report = scan_report(os.getenv("GAGARIN_SEC_USER_AGENT") or "Gagarin/3 (https://github.com/andreameloni1984-sys/commodity-news-scanner)",
                             extra_feeds(), expectations_from(args.macro_expectations))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.check_market:
        try:
            now = utcnow()
            print(json.dumps(check_market(configured_market(), {}, now, session_open(now)), indent=2))
        except EXPECTED_ERRORS as exc:
            parser.exit(1, f"Alpaca: {exc if isinstance(exc, ValueError) else error_label(exc)}\n")
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
        token, chat = os.environ["GAGARIN_TELEGRAM_TOKEN"], os.environ["GAGARIN_TELEGRAM_CHAT_ID"]
        if not token or not chat:
            raise ValueError("Secret Telegram mancanti")

        def publish(text):
            return send_telegram(text, token=token, chat_id=chat)
    worker = Worker(demo, market, Journal(journal_path), publish, os.environ["GAGARIN_SEC_USER_AGENT"],
                    extra_feeds(), args.macro_expectations)
    while True:
        success = worker.poll()
        if args.once:
            raise SystemExit(0 if success else 1)
        time.sleep(60)


if __name__ == "__main__":
    main()
