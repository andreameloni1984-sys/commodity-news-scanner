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
from xml.etree.ElementTree import ParseError

from invest_v2.gagarin_runner import send_telegram, session_open
from invest_v2.us_market_data import AlpacaData

from .demo import Demo
from .engine import assess, message
from .journal import Journal
from .news import Event, FEEDS, PRIMARY, events, fetch, sec_directory

EXPECTED_ERRORS = (OSError, ValueError, RuntimeError, KeyError, TypeError, ParseError)


def utcnow():
    return datetime.now(timezone.utc)


class Worker:
    def __init__(self, demo, market, journal, publish, user_agent, extra_feeds):
        self.demo, self.market, self.journal = demo, market, journal
        self.publish, self.user_agent = publish, user_agent
        self.extra_feeds = extra_feeds
        self.universe = {}
        self.directory = {}
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
            try:
                self.directory = sec_directory(self.user_agent)
            except EXPECTED_ERRORS as exc:
                self.journal.error(now, "SEC ticker directory", type(exc).__name__)

        sources = [(source, url, None) for source, url in FEEDS.items()] + self.extra_feeds
        found = []
        for source, url, configured in sorted(sources, key=lambda row: row[0] not in PRIMARY):
            if self.backoff.get(url, now) > now:
                continue
            try:
                found.extend(events(fetch(url, self.user_agent), source=source, now=utcnow(),
                                    directory=self.directory, configured_symbol=configured,
                                    atom=source == "SEC EDGAR"))
            except EXPECTED_ERRORS as exc:
                self.backoff[url] = now + timedelta(minutes=5)
                self.journal.error(now, source, f"HTTP {exc.code}" if hasattr(exc, "code") else type(exc).__name__)
        for event in found:
            if event.symbol not in self.universe:
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
            if checked_at - event.published > timedelta(hours=1):
                continue
            signal = assess(event, bars, checked_at)
            if signal is None:
                self.journal.error(now, event.symbol, "Dati intraday assenti, scaduti o liquidità insufficiente")
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
            self.journal.error(now, "catalogo Demo", str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__)
            print("Gagarin: catalogo Demo non disponibile", flush=True)
            return False
        try:
            self.monitor(utcnow())
        except EXPECTED_ERRORS as exc:
            self.market_retry_at = now + timedelta(minutes=5)
            self.journal.error(now, "dati mercato", f"HTTP {exc.code}" if hasattr(exc, "code") else type(exc).__name__)
            return False
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--check-demo", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()
    simulated = os.getenv("GAGARIN_TELEGRAM_ENABLED") != "true"
    journal_path = args.journal or Path(".gagarin-pravda-sim.sqlite" if simulated else ".gagarin-pravda.sqlite")
    if args.report:
        print(json.dumps(Journal(journal_path).report(), indent=2))
        return
    demo = Demo(os.getenv("GAGARIN_DEMO_KEY"), os.getenv("GAGARIN_DEMO_SECRET"))
    if args.check_demo:
        print(f"Demo: {len(demo.universe())} strumenti USA compatibili, "
              f"{demo.check_account()} posizioni. Lettura del saldo verificata.")
        return
    market = AlpacaData(os.environ["GAGARIN_ALPACA_KEY"], os.environ["GAGARIN_ALPACA_SECRET"],
                        os.getenv("GAGARIN_ALPACA_FEED") or "iex")
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
    feeds = json.loads(os.getenv("GAGARIN_EXTRA_FEEDS", "[]"))
    extra = [(item["source"], item["url"], item.get("symbol")) for item in feeds]
    worker = Worker(demo, market, Journal(journal_path), publish, os.environ["GAGARIN_SEC_USER_AGENT"], extra)
    while True:
        success = worker.poll()
        if args.once:
            raise SystemExit(0 if success else 1)
        time.sleep(60)


if __name__ == "__main__":
    main()
