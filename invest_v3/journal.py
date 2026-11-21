"""PRAVDA: persistent journal of candidates, emitted signals and their outcomes."""
import json
import sqlite3
from datetime import datetime, timedelta
from statistics import mean

from .engine import HORIZONS

OBSERVATION_WINDOW = timedelta(minutes=5)


class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY, event TEXT NOT NULL, expires TEXT NOT NULL,
                latest TEXT, first_signal TEXT, entry_signal TEXT, notified TEXT,
                observations TEXT NOT NULL DEFAULT '{}', outcome TEXT
            );
            CREATE TABLE IF NOT EXISTS errors (
                at TEXT NOT NULL, component TEXT NOT NULL, reason TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cache (
                name TEXT PRIMARY KEY, saved TEXT NOT NULL, payload TEXT NOT NULL
            );
        """)

    # Small persistent cache: the scheduled worker is a fresh process every run.
    def cached(self, name, now, max_age):
        row = self.db.execute("SELECT saved, payload FROM cache WHERE name=?", (name,)).fetchone()
        if not row:
            return None, False
        return json.loads(row[1]), now - datetime.fromisoformat(row[0]) < max_age

    def store(self, name, now, payload):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)",
                            (name, now.isoformat(), json.dumps(payload)))

    def add(self, key, event, expires):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO candidates (id,event,expires) VALUES (?,?,?)",
                            (key, json.dumps(event), expires.isoformat()))

    def error(self, now, component, reason):
        with self.db:
            self.db.execute("INSERT INTO errors VALUES (?,?,?)", (now.isoformat(), component, reason))

    def active(self, now, limit):
        return self.db.execute("""
            SELECT id,event,latest,first_signal,entry_signal,notified,observations,outcome
            FROM candidates WHERE expires >= ?
            ORDER BY (first_signal IS NOT NULL) DESC,
                     json_extract(event, '$.impact') DESC,
                     json_extract(event, '$.published') DESC, id LIMIT ?
        """, (now.isoformat(), limit)).fetchall()

    def record(self, key, latest):
        with self.db:
            self.db.execute("UPDATE candidates SET latest=? WHERE id=?", (json.dumps(latest), key))

    def notified(self, key, signal):
        """Store a delivered signal. The first delivery is the PRAVDA baseline."""
        payload = json.dumps(signal)
        with self.db:
            self.db.execute("""
                UPDATE candidates SET notified=?, latest=?, first_signal=coalesce(first_signal,?),
                    entry_signal=coalesce(entry_signal,?) WHERE id=?
            """, (payload, payload, payload,
                  payload if signal["state"] == "ENTRARE" and signal["levels"] else None, key))

    def follow(self, key, bars, first, entry, observations, outcome, now):
        if not first:
            return
        start = datetime.fromisoformat(first["signaled_at"])
        for offset in HORIZONS:
            horizon = start + timedelta(minutes=offset)
            if str(offset) in observations or now < horizon:
                continue
            bar = next((b for b in bars if horizon <= b.closed_at <= horizon + OBSERVATION_WINDOW), None)
            if bar:
                observations[str(offset)] = {"price": bar.close, "at": bar.closed_at.isoformat()}
            elif now > horizon + OBSERVATION_WINDOW:
                observations[str(offset)] = {"price": None, "at": None}  # missing: excluded
        if entry and not outcome:
            entry_price, stop, target = entry["levels"]  # ENTRARE is LONG only
            entry_time = datetime.fromisoformat(entry["signaled_at"])
            until = entry_time + timedelta(hours=1)
            for bar in bars:
                if not entry_time < bar.closed_at <= until + OBSERVATION_WINDOW:
                    continue
                # OHLC cannot resolve intrabar order. Stop takes priority.
                if bar.low <= stop:
                    outcome = {"reason": "STOP", "exit": stop}
                elif bar.high >= target:
                    outcome = {"reason": "TP", "exit": target}
                elif bar.closed_at >= until:
                    outcome = {"reason": "TIME", "exit": bar.close}
                if outcome:
                    outcome.update(at=bar.closed_at.isoformat(), sim_return=outcome["exit"] / entry_price - 1)
                    break
        with self.db:
            self.db.execute("UPDATE candidates SET observations=?, outcome=? WHERE id=?",
                            (json.dumps(observations), json.dumps(outcome) if outcome else None, key))

    def report(self, limit=30):
        per_horizon = {str(h): [] for h in HORIZONS}
        delays, returns, details = [], [], []
        for event_json, first_json, observations_json, outcome_json in self.db.execute(
            "SELECT event,first_signal,observations,outcome FROM candidates "
            "WHERE first_signal IS NOT NULL ORDER BY json_extract(first_signal,'$.signaled_at')"
        ):
            event, first, observations = map(json.loads, (event_json, first_json, observations_json))
            sign = 1 if event["direction"] == "LONG" else -1
            delay = (datetime.fromisoformat(first["signaled_at"])
                     - datetime.fromisoformat(event["published"])).total_seconds()
            delays.append(delay)
            moves, results = {}, {}
            for horizon, sample in observations.items():
                if sample.get("price") is None:
                    continue
                change = sample["price"] / first["price"] - 1
                moves[horizon] = round(change, 5)
                results[horizon] = "corretto" if sign * change > 0 else "errato"
                per_horizon[horizon].append(sign * change > 0)
            outcome = json.loads(outcome_json) if outcome_json else None
            if outcome:
                returns.append(outcome["sim_return"])
            details.append({
                "ticker": event["symbol"], "direzione": event["direction"],
                "stato": first["state"], "notizia": event["title"][:120], "fonte": event["url"],
                "pubblicata": event["published"], "segnale": first["signaled_at"],
                "ritardo_secondi": round(delay), "prezzo_segnale": first["price"],
                "livelli": first["levels"], "movimento": moves, "esito": results,
                "simulazione": outcome,
            })
        return {
            "segnali": len(details),
            "accuratezza": {
                horizon: {"campioni": len(rows), "corretti": sum(rows),
                          "percentuale": round(100 * mean(rows), 1) if rows else None}
                for horizon, rows in per_horizon.items()
            },
            "ritardo_medio_notizia_segnale_secondi": round(mean(delays)) if delays else None,
            "simulazioni_chiuse": len(returns),
            "rendimento_medio_simulato": mean(returns) if returns else None,
            "ultimi_segnali": details[-limit:],
        }
