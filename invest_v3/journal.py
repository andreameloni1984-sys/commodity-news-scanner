"""Persistent PRAVDA event and simulation journal."""
import json
import sqlite3
from datetime import datetime, timedelta
from statistics import mean

from .engine import HORIZONS


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
        """)

    def add(self, key, event, expires):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO candidates (id,event,expires) VALUES (?,?,?)",
                            (key, json.dumps(event), expires.isoformat()))

    def error(self, now, component, reason):
        with self.db:
            self.db.execute("INSERT INTO errors VALUES (?,?,?)", (now.isoformat(), component, reason))

    def active(self, now, limit):
        return self.db.execute("""
            SELECT id,event,latest,first_signal,entry_signal,notified,observations,outcome,expires
            FROM candidates WHERE expires >= ?
            ORDER BY (first_signal IS NOT NULL) DESC,
                     json_extract(event, '$.impact') DESC,
                     json_extract(event, '$.published') DESC, id LIMIT ?
        """, (now.isoformat(), limit)).fetchall()

    def record(self, key, signal, *, notify=False):
        payload = json.dumps(signal)
        with self.db:
            if notify:
                self.db.execute("UPDATE candidates SET notified=? WHERE id=?", (payload, key))
                return
            if signal["state"] == "SCARTARE":
                self.db.execute("UPDATE candidates SET latest=? WHERE id=?", (payload, key))
                return
            self.db.execute("""
                UPDATE candidates SET latest=?, first_signal=coalesce(first_signal,?),
                    entry_signal=coalesce(entry_signal,?) WHERE id=?
            """, (payload, payload, payload if signal["state"] == "ENTRARE" else None, key))

    def follow(self, key, bars, first, entry, observations, outcome, now):
        if not first:
            return
        start = datetime.fromisoformat(first["signaled_at"])
        for offset in HORIZONS:
            horizon = start + timedelta(minutes=offset)
            if str(offset) in observations or now < horizon:
                continue
            bar = next((b for b in bars if horizon <= b.closed_at <= horizon + timedelta(minutes=1)), None)
            if bar:
                observations[str(offset)] = {"price": bar.close, "at": bar.closed_at.isoformat()}
        if entry and not outcome:
            entry_price, stop, tp1, _, _ = entry["levels"]
            entry_time = datetime.fromisoformat(entry["signaled_at"])
            until = entry_time + timedelta(hours=1)
            for bar in bars:
                if not entry_time < bar.closed_at <= until + timedelta(minutes=1):
                    continue
                # OHLC cannot resolve intrabar order. Stop takes priority.
                if bar.low <= stop:
                    outcome = {"reason": "STOP", "exit": stop}
                elif bar.high >= tp1:
                    outcome = {"reason": "TP1", "exit": tp1}
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

    def report(self):
        directions = []
        delays = []
        returns = []
        historical = {}
        for event_json, first_json, observations_json, outcome_json in self.db.execute(
            "SELECT event,first_signal,observations,outcome FROM candidates WHERE first_signal IS NOT NULL"
        ):
            event, first, observations = map(json.loads, (event_json, first_json, observations_json))
            delays.append((datetime.fromisoformat(event["detected"]) - datetime.fromisoformat(event["published"])).total_seconds())
            if "60" in observations:
                change = observations["60"]["price"] / first["price"] - 1
                correct = change * (1 if event["direction"] == "LONG" else -1) > 0
                directions.append(correct)
                historical.setdefault((event["category"], event["direction"]), []).append(change)
            if outcome_json:
                outcome = json.loads(outcome_json)
                returns.append((outcome["at"], outcome["sim_return"]))
        equity = peak = 1.0
        drawdown = 0.0
        for _, change in sorted(returns):
            equity *= 1 + change
            peak = max(peak, equity)
            drawdown = max(drawdown, 1 - equity / peak)
        return {
            "directional_samples_60m": len(directions),
            "directional_accuracy_60m": mean(directions) if directions else None,
            "false_signal_rate_60m": 1 - mean(directions) if directions else None,
            "detection_delay_seconds_mean": mean(delays) if delays else None,
            "closed_simulations": len(returns),
            "sequential_sim_return": equity - 1 if returns else None,
            "sequential_max_drawdown": drawdown if returns else None,
            "historical_reactions": [
                {"category": category, "direction": direction, "samples": len(samples),
                 "mean_return_60m": mean(samples)}
                for (category, direction), samples in sorted(historical.items())
            ],
        }
