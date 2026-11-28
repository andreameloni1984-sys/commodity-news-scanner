"""Prezzi da Yahoo Finance (chart API pubblica, nessuna chiave).

Yahoo a volte rifiuta le richieste ("429 troppe richieste"), soprattutto dai server
condivisi di GitHub. Per questo fetch():
* alterna i due indirizzi equivalenti di Yahoo (query1 e query2) e aspetta di più dopo un 429;
* se tutto fallisce usa l'ultima copia scaricata (BARS_CACHE_DIR), se ha meno di 3 ore.
  La copia ha l'ora del suo ultimo prezzo: i controlli sull'età del prezzo impediscono
  segnali nuovi su dati vecchi, mentre stop e target vengono ricontrollati sullo storico
  al giro successivo.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

_URL = "https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}"
_HOSTS = ("query1", "query2")
_WAIT_429 = (3, 8, 15)
_WAIT_OTHER = (2, 4, 6)
CACHE_MAX_AGE = timedelta(hours=3)
log = logging.getLogger("cfdbot.data")
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cfd-signals-bot/1.0)"}


class DataError(RuntimeError):
    pass


@dataclass
class Bars:
    symbol: str
    time: list[datetime]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    last_price: float | None = None
    last_price_time: datetime | None = None

    def __len__(self) -> int:
        return len(self.close)

    def upto(self, n: int) -> "Bars":
        """Prime n barre (per backtest e per escludere la barra in corso)."""
        return Bars(self.symbol, self.time[:n], self.open[:n], self.high[:n], self.low[:n], self.close[:n],
                    self.last_price, self.last_price_time)


def parse_chart(symbol: str, payload: dict) -> Bars:
    try:
        result = payload["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        stamps = result["timestamp"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DataError(f"risposta inattesa per {symbol}") from exc
    rows = []
    for i, ts in enumerate(stamps):
        vals = [quote[k][i] for k in ("open", "high", "low", "close")]
        if None in vals:
            continue
        rows.append((datetime.fromtimestamp(ts, tz=timezone.utc), *map(float, vals)))
    if not rows:
        raise DataError(f"nessuna barra per {symbol}")
    meta = result.get("meta", {})
    lp, lt = meta.get("regularMarketPrice"), meta.get("regularMarketTime")
    return Bars(
        symbol=symbol,
        time=[r[0] for r in rows], open=[r[1] for r in rows], high=[r[2] for r in rows],
        low=[r[3] for r in rows], close=[r[4] for r in rows],
        last_price=float(lp) if lp else rows[-1][4],
        last_price_time=datetime.fromtimestamp(lt, tz=timezone.utc) if lt else rows[-1][0],
    )


def _cache_file(symbol: str, range_: str, interval: str) -> Path | None:
    folder = os.getenv("BARS_CACHE_DIR", "").strip()
    if not folder:
        return None
    safe = "".join(ch if ch.isalnum() else "_" for ch in f"{symbol}_{range_}_{interval}")
    return Path(folder) / f"{safe}.json"


def _save_cache(path: Path | None, bars: Bars) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "saved": datetime.now(timezone.utc).isoformat(), "symbol": bars.symbol,
            "time": [t.isoformat() for t in bars.time], "open": bars.open, "high": bars.high,
            "low": bars.low, "close": bars.close, "last_price": bars.last_price,
            "last_price_time": bars.last_price_time.isoformat() if bars.last_price_time else None,
        }), encoding="utf-8")
    except OSError as exc:
        log.warning("Copia dei prezzi non salvata: %s", exc)


def _load_cache(path: Path | None, now: datetime) -> Bars | None:
    if path is None:
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        if now - datetime.fromisoformat(d["saved"]) > CACHE_MAX_AGE:
            return None
        return Bars(d["symbol"], [datetime.fromisoformat(t) for t in d["time"]], d["open"], d["high"],
                    d["low"], d["close"], d.get("last_price"),
                    datetime.fromisoformat(d["last_price_time"]) if d.get("last_price_time") else None)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def fetch(symbol: str, range_: str = "2y", interval: str = "1d", session=None, sleep=time.sleep) -> Bars:
    http = session or requests
    cache = _cache_file(symbol, range_, interval)
    last: Exception | None = None
    attempts = len(_WAIT_429) + 1
    for attempt in range(attempts):
        try:
            r = http.get(_URL.format(host=_HOSTS[attempt % len(_HOSTS)], symbol=symbol),
                         params={"range": range_, "interval": interval}, headers=_HEADERS, timeout=20)
            r.raise_for_status()
            bars = parse_chart(symbol, r.json())
            _save_cache(cache, bars)
            return bars
        except (requests.RequestException, ValueError, DataError) as exc:
            last = exc
            if attempt < attempts - 1:
                limited = getattr(getattr(exc, "response", None), "status_code", None) == 429
                sleep((_WAIT_429 if limited else _WAIT_OTHER)[min(attempt, 2)])
    copy = _load_cache(cache, datetime.now(timezone.utc))
    if copy is not None:
        log.warning("%s: Yahoo non risponde (%s), uso l'ultima copia scaricata", symbol, last)
        return copy
    raise DataError(f"download fallito per {symbol}: {last}")


def completed_daily(bars: Bars, now: datetime) -> Bars:
    """Esclude la barra giornaliera di oggi (ancora in formazione)."""
    if bars.time and bars.time[-1].date() >= now.date():
        return bars.upto(len(bars) - 1)
    return bars
