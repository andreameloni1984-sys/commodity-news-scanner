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
            CREATE INDEX IF NOT EXISTS candidates_expires ON candidates(expires);
            CREATE TABLE IF NOT EXISTS macro_releases (
                series TEXT NOT NULL, published TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY (series, published)
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

    def record_macro(self, releases):
        with self.db:
            self.db.executemany("""
                INSERT INTO macro_releases VALUES (?,?,?)
                ON CONFLICT(series,published) DO UPDATE SET payload=excluded.payload
            """, [(row["series"], row["published"], json.dumps(row)) for row in releases])

    def add(self, key, event, expires):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO candidates (id,event,expires) VALUES (?,?,?)",
                            (key, json.dumps(event), expires.isoformat()))

    def error(self, now, component, reason):
        with self.db:
            self.db.execute("INSERT INTO errors VALUES (?,?,?)", (now.isoformat(), component, reason))

    def active(self, now):
        return self.db.execute("""
            SELECT id,event,latest,first_signal,entry_signal,notified,observations,outcome
            FROM candidates WHERE expires >= ?
            ORDER BY (latest IS NULL) DESC, (first_signal IS NOT NULL) DESC,
                     json_extract(event, '$.impact') DESC,
                     json_extract(event, '$.published') DESC, id
        """, (now.isoformat(),)).fetchall()

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
            bar = next((b for b in bars if horizon <= b.closed_at <= min(now, horizon + OBSERVATION_WINDOW)), None)
            if bar:
                observations[str(offset)] = {"price": bar.close, "at": bar.closed_at.isoformat()}
            elif now > horizon + OBSERVATION_WINDOW:
                observations[str(offset)] = {"price": None, "at": None}  # missing: excluded
        if entry and not outcome:
            entry_price, stop, target = entry["levels"][:3]  # ENTRARE is LONG only
            entry_time = datetime.fromisoformat(entry["signaled_at"])
            until = entry_time + timedelta(hours=1)
            first_full_close = entry_time + timedelta(minutes=1)
            last_close = min(now, until + OBSERVATION_WINDOW)
            for bar in bars:
                if not first_full_close <= bar.closed_at <= last_close:
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

    def comparable(self, key, event):
        row = self.db.execute("""
            SELECT count(*), avg(json_extract(observations, '$."60".price') /
                                 json_extract(first_signal, '$.price') - 1)
            FROM candidates WHERE id != ?
              AND json_extract(event, '$.category') = ?
              AND json_extract(event, '$.direction') = ?
              AND json_extract(observations, '$."60".at') <= ?
        """, (key, event.category, event.direction, event.detected.isoformat())).fetchone()
        return {"samples": row[0], "mean_return_60m": row[1]} if row[0] else None

    def report(self, limit=30):
        per_horizon = {str(h): [] for h in HORIZONS}
        delays, returns, details = [], [], []
        historical = {}
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
                if horizon == "60":
                    historical.setdefault((event["category"], event["direction"]), []).append(change)
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
        confirmed = self.db.execute("SELECT count(*) FROM candidates WHERE notified IS NOT NULL").fetchone()[0]
        unconfirmed = self.db.execute("SELECT count(*) FROM errors WHERE component = 'Telegram'").fetchone()[0]
        return {
            "segnali": len(details),
            "candidates_with_confirmed_delivery": confirmed,
            "telegram_unconfirmed_attempts": unconfirmed,
            "accuratezza": {
                horizon: {"campioni": len(rows), "corretti": sum(rows),
                          "percentuale": round(100 * mean(rows), 1) if rows else None}
                for horizon, rows in per_horizon.items()
            },
            "ritardo_medio_notizia_segnale_secondi": round(mean(delays)) if delays else None,
            "simulazioni_chiuse": len(returns),
            "rendimento_medio_simulato": mean(returns) if returns else None,
            "historical_reactions": [
                {"category": category, "direction": direction, "samples": len(samples),
                 "mean_return_60m": mean(samples)}
                for (category, direction), samples in sorted(historical.items())
            ],
            "ultimi_segnali": details[-limit:],
        }
