from __future__ import annotations

import math
import os
import hashlib
from collections import deque
import hmac
import time
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from commodities.universe import enabled_commodities, validate_universe
from engine.gagarin import analyze_universe
from engine.forex_session import filter_forex_for_session
from engine.cloud_api_status import cloud_api_decision_status
from soyuz_gagarin.adapter import evaluate_states
from paper_portfolio import PaperPortfolio
from engine.day_registry import load as load_day_registry, run as run_day_registry, summary as day_summary
from state_store import ensure_schema, load_state, save_state

app = FastAPI(title="SOYUZ GAGARIN CLOUD", version="1.0")

# Private dashboard authentication. Configure both secrets on Render.
_APP_SESSION_TTL = 12 * 60 * 60
_APP_COOKIE = "gagarin_session"

# Best-effort per-client throttle for the single-password personal dashboard.
# The bounded in-process store avoids a new dependency or persistent credential data.
_LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60
_LOGIN_MAX_FAILED_ATTEMPTS = 5
_LOGIN_MAX_TRACKED_CLIENTS = 1024
_LOGIN_FAILURES: dict[str, deque[float]] = {}
_LOGIN_FAILURES_LOCK = Lock()


def _login_client_key(request: Request) -> str:
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return str(host or "unknown")[:128]


def _prune_login_failures(client_key: str, now: float):
    attempts = _LOGIN_FAILURES.get(client_key)
    if attempts is None:
        return None
    while attempts and now - attempts[0] >= _LOGIN_FAILURE_WINDOW_SECONDS:
        attempts.popleft()
    if not attempts:
        _LOGIN_FAILURES.pop(client_key, None)
        return None
    return attempts


def _begin_login_attempt(client_key: str, now: float | None = None) -> int:
    """Atomically reserve an attempt; return seconds to wait, or zero if allowed."""
    current = time.monotonic() if now is None else float(now)
    key = str(client_key or "unknown")[:128]
    with _LOGIN_FAILURES_LOCK:
        attempts = _prune_login_failures(key, current)
        if attempts is not None and len(attempts) >= _LOGIN_MAX_FAILED_ATTEMPTS:
            return max(1, math.ceil(
                _LOGIN_FAILURE_WINDOW_SECONDS - (current - attempts[0])
            ))
        if attempts is None:
            if len(_LOGIN_FAILURES) >= _LOGIN_MAX_TRACKED_CLIENTS:
                oldest_key = min(
                    _LOGIN_FAILURES,
                    key=lambda item: _LOGIN_FAILURES[item][-1],
                )
                _LOGIN_FAILURES.pop(oldest_key, None)
            attempts = deque()
            _LOGIN_FAILURES[key] = attempts
        # Reserve before PBKDF2 verification so concurrent requests cannot all
        # pass the limit check before their failures are recorded.
        attempts.append(current)
        return 0


def _clear_login_failures(client_key: str) -> None:
    key = str(client_key or "unknown")[:128]
    with _LOGIN_FAILURES_LOCK:
        _LOGIN_FAILURES.pop(key, None)


def _verify_app_password(password: str, encoded: str | None = None) -> bool:
    encoded = (encoded if encoded is not None else os.getenv("APP_PASSWORD_HASH", "")).strip()
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        rounds_i = int(rounds)
        if rounds_i < 200_000 or rounds_i > 2_000_000:
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), rounds_i)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _session_token(secret: str, issued_at: int) -> str:
    message = f"gagarin-session:{issued_at}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{issued_at}.{signature}"


def _valid_app_session(token: str | None, secret: str | None = None, now: int | None = None) -> bool:
    secret = (secret if secret is not None else os.getenv("APP_SESSION_SECRET", "")).strip()
    if not secret or not token:
        return False
    try:
        issued_text, signature = token.split(".", 1)
        issued_at = int(issued_text)
        current = int(time.time()) if now is None else int(now)
        if issued_at > current or current - issued_at > _APP_SESSION_TTL:
            return False
        expected = _session_token(secret, issued_at).split(".", 1)[1]
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


LOGIN_HTML = """<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090e17"><title>Accesso Gagarin</title><style>
:root{color-scheme:dark;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#090e17;color:#edf4ff;padding:20px}.box{width:min(100%,390px);padding:26px;background:#111a28;border:1px solid #233249;border-radius:18px}h1{font-size:22px;margin:0 0 8px}p{color:#8ea0b8;font-size:13px;line-height:1.5}input,button{box-sizing:border-box;width:100%;padding:14px;border-radius:11px;border:1px solid #233249;background:#0b1421;color:#fff;font-size:16px;margin-top:12px}button{background:#087da4;border:0;font-weight:750;cursor:pointer}#error{color:#ff6e79;min-height:20px;font-size:13px}</style></head><body><form class="box" id="login"><h1>🚀 GAGARIN INTELLIGENCE</h1><p>Area riservata. Inserisci la password personale per continuare.</p><input id="password" type="password" autocomplete="current-password" placeholder="Password" required><button id="submit" type="submit">ACCEDI</button><div id="error" role="alert"></div></form><script>
document.getElementById('login').addEventListener('submit',async e=>{e.preventDefault();const b=document.getElementById('submit'),err=document.getElementById('error');b.disabled=true;err.textContent='Verifica in corso…';try{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.getElementById('password').value})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Accesso non riuscito');location.replace('/static/intelligence.html');}catch(x){err.textContent=x.message;document.getElementById('password').value='';}finally{b.disabled=false;}});
</script></body></html>"""


@app.middleware("http")
async def require_private_dashboard(request: Request, call_next):
    # Static assets remain available to the browser, but the dashboard HTML itself
    # is never served without a valid signed, HttpOnly session cookie.
    if request.url.path == "/static/intelligence.html":
        if not _valid_app_session(request.cookies.get(_APP_COOKIE)):
            return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
def app_login_page():
    if not os.getenv("APP_PASSWORD_HASH") or not os.getenv("APP_SESSION_SECRET"):
        return HTMLResponse(
            "<h2>Accesso privato non ancora configurato</h2><p>Imposta APP_PASSWORD_HASH e APP_SESSION_SECRET nelle variabili ambiente Render.</p>",
            status_code=503,
        )
    return HTMLResponse(LOGIN_HTML)


@app.post("/api/auth/login")
async def app_login(request: Request):
    if not os.getenv("APP_PASSWORD_HASH") or not os.getenv("APP_SESSION_SECRET"):
        raise HTTPException(status_code=503, detail="Autenticazione non configurata")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Richiesta non valida")
    client_key = _login_client_key(request)
    retry_after = _begin_login_attempt(client_key)
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Troppi tentativi. Riprova più tardi.",
            headers={"Retry-After": str(retry_after)},
        )

    password = payload.get("password", "") if isinstance(payload, dict) else ""
    if not isinstance(password, str) or not _verify_app_password(password):
        raise HTTPException(status_code=401, detail="Password non corretta")
    _clear_login_failures(client_key)
    issued_at = int(time.time())
    response = JSONResponse({"ok": True})
    response.set_cookie(
        _APP_COOKIE,
        _session_token(os.environ["APP_SESSION_SECRET"].strip(), issued_at),
        max_age=_APP_SESSION_TTL,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return response


@app.post("/api/auth/logout")
def app_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(_APP_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    return response

app.mount("/static", StaticFiles(directory="static"), name="static")
RUN_LOCK = Lock()
PORTFOLIO = PaperPortfolio(100.0)
AGGRESSIVE_PORTFOLIO = PaperPortfolio(100.0)
FOREX_AGGRESSIVE_PORTFOLIO = PaperPortfolio(100.0)

# Restore durable paper accounts at startup so Render restarts never reset them.
try:
    _DB_READY = ensure_schema()
    if _DB_READY:
        PORTFOLIO.restore_state(load_state("portfolio_main"))
        AGGRESSIVE_PORTFOLIO.restore_state(load_state("portfolio_aggressive"))
        FOREX_AGGRESSIVE_PORTFOLIO.restore_state(load_state("portfolio_forex_aggressive"))
    else:
        print("GAGARIN PERSISTENCE DISABLED | DATABASE_URL missing", flush=True)
except Exception as _persistence_error:
    _DB_READY = False
    print(f"GAGARIN PERSISTENCE INIT FAILED | {type(_persistence_error).__name__}: {_persistence_error}", flush=True)


def _authorize(x_api_key: str | None) -> None:
    expected = os.getenv("CLOUD_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="CLOUD_API_KEY is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")



_QUOTE_REFERENCE_FIELDS = (
    "provider", "symbol", "source_timestamp", "observed_at",
    "currency", "unit", "unit_key", "price_scale", "price", "bid", "ask",
    "age_seconds", "market_type", "contract_month", "delayed",
    "market_session", "stale", "status", "comparison_status",
    "deviation_pct", "basis_status", "basis_spot_minus_futures_pct",
    "source_independence_status", "use_restriction", "cache_status",
    "scheduled_symbol",
)


def _finite_quote_number(value, *, positive: bool = False, non_negative: bool = False):
    """Return a finite numeric quote field, or None; never serialize NaN/Infinity."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    if non_negative and number < 0:
        return None
    return number


def _quote_provenance_json(state, meta: dict) -> dict:
    """Expose the data-engine quote audit without inventing missing provenance."""
    bid = _finite_quote_number(meta.get("quote_bid"), positive=True)
    ask = _finite_quote_number(meta.get("quote_ask"), positive=True)
    age = _finite_quote_number(meta.get("quote_age_seconds"), non_negative=True)
    if age is None:
        age = _finite_quote_number(
            getattr(state, "data_age_seconds", None), non_negative=True
        )

    quote_provider = meta.get("quote_provider") or getattr(state, "data_source", None)
    quote_symbol = (
        meta.get("quote_symbol")
        or meta.get("resolved_symbol")
        or meta.get("execution_symbol")
    )
    quote_market_type = (
        meta.get("quote_market_type") or meta.get("execution_market_type")
    )
    bid_ask_flag = meta.get("quote_bid_ask_available")
    bid_ask_available = (
        bid is not None and ask is not None
        if bid_ask_flag is None
        else bid_ask_flag is True and bid is not None and ask is not None
    )

    execution_quote = {
        "provider": str(quote_provider) if quote_provider else None,
        "symbol": str(quote_symbol) if quote_symbol else None,
        "source_timestamp": (
            str(meta.get("quote_timestamp") or meta.get("last_bar_timestamp"))
            if (meta.get("quote_timestamp") or meta.get("last_bar_timestamp"))
            else None
        ),
        "currency": meta.get("quote_currency"),
        "unit": meta.get("quote_unit"),
        "market_type": quote_market_type,
        "price": _finite_quote_number(meta.get("quote_price"), positive=True),
        "bid": bid,
        "ask": ask,
        "bid_ask_available": bid_ask_available,
        "age_seconds": age,
        "freshness_status": (
            meta.get("quote_freshness_status")
            or meta.get("freshness_status")
            or meta.get("data_status")
            or "UNKNOWN"
        ),
        "status": meta.get("quote_status") or meta.get("data_status") or "UNKNOWN",
    }

    references = {}
    raw_references = meta.get("reference_quotes")
    if isinstance(raw_references, dict):
        numeric_fields = {
            "price": {"positive": True},
            "bid": {"positive": True},
            "ask": {"positive": True},
            "age_seconds": {"non_negative": True},
            "deviation_pct": {},
            "basis_spot_minus_futures_pct": {},
        }
        for name, raw in raw_references.items():
            if not isinstance(raw, dict):
                continue
            record = {}
            for field in _QUOTE_REFERENCE_FIELDS:
                if field not in raw:
                    continue
                value = raw[field]
                if field in numeric_fields:
                    options = numeric_fields[field]
                    value = _finite_quote_number(
                        value,
                        positive=options.get("positive", False),
                        non_negative=options.get("non_negative", False),
                    )
                record[field] = value
            references[str(name).upper()] = record

    return {
        "execution_quote": execution_quote,
        "execution_basis": {
            "provider": meta.get("execution_provider") or execution_quote["provider"],
            "symbol": meta.get("execution_symbol") or execution_quote["symbol"],
            "market_type": meta.get("execution_market_type") or quote_market_type,
        },
        "reference_quotes": references,
    }


def _state_json(state):
    meta = getattr(state, "metadata", {}) or {}
    decision_status = cloud_api_decision_status(state, meta)
    bias = decision_status["bias"]
    # Risk levels are meaningful only when the canonical D-L-A adapter has
    # validated fresh price/ATR inputs. Keep the directional BIAS visible,
    # but never leak stale or unvalidated entry/SL/TP values through the API.
    levels_visible = decision_status["setup"] in {"EARLY_SETUP", "CONFIRMED"}
    risk_level = lambda name: getattr(state, name, None) if levels_visible else None
    return {
        "symbol": str(getattr(state, "symbol", "")).upper(),
        "commodity": getattr(state, "commodity", ""),
        "price": getattr(state, "price", None),
        "direction": bias if bias in {"LONG", "SHORT"} else "",
        "bias": bias,
        "bias_source": decision_status["bias_source"],
        "setup": decision_status["setup"],
        "trade_paper": decision_status["trade_paper"],
        "blockers": decision_status["blockers"],
        "probability": getattr(state, "probability", None),
        "quality": getattr(state, "quality", None),
        "confidence": getattr(state, "confidence", None),
        "action": decision_status["action"],
        "reason": decision_status["reason"],
        "entry": risk_level("entry"),
        "stop": risk_level("stop"),
        "tp1": risk_level("tp1"),
        "tp2": risk_level("tp2"),
        "tp3": risk_level("tp3"),
        "rr3": risk_level("rr3"),
        "data_source": getattr(state, "data_source", None),
        "quote_provenance": _quote_provenance_json(state, meta),
        "data_status": meta.get("data_status", "UNKNOWN"),
        "live": meta.get("live") is True,
        "volume_confirmed": meta.get("volume_confirmed") is True,
        "relative_volume": meta.get("relative_volume"),
        "opportunity_alert": getattr(state, "opportunity_alert", "NONE"),
        "opportunity_direction": getattr(state, "opportunity_direction", "NONE"),
        "opportunity_score": getattr(state, "opportunity_score", 0.0),
        "pre_move_alert": getattr(state, "pre_move_alert", "NONE"),
        "pre_move_direction": getattr(state, "pre_move_direction", "NONE"),
        "pre_move_score": getattr(state, "pre_move_score", 0.0),
        "pre_move_components": getattr(state, "pre_move_components", {}),
        "move_4h_pct": getattr(state, "move_4h_pct", None),
        "move_24h_pct": getattr(state, "move_24h_pct", None),
        "move_atr": getattr(state, "move_atr", None),
    }


def _run_gagarin(*, on_demand: bool = False):
    errors = validate_universe()
    if errors:
        raise RuntimeError("CONFIGURATION_BLOCKED: " + ", ".join(errors))

    commodities = filter_forex_for_session(enabled_commodities(), on_demand=on_demand)
    results = analyze_universe(commodities)
    decisions = evaluate_states(results)
    by_symbol = {d.symbol: d for d in decisions}

    for state in results:
        symbol = str(getattr(state, "symbol", "")).upper()
        decision = by_symbol.get(symbol)
        metadata = getattr(state, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
            state.metadata = metadata
        metadata["gagarin_action"] = decision.action if decision else "NO_DECISION"
        metadata["gagarin_reason"] = decision.reason if decision else "DECISION_NOT_RETURNED"

    rows = [_state_json(s) for s in results]
    operational = [r for r in rows if r["action"] in {"PAPER_ENTRY", "PAPER_SIGNAL"} and str(r.get("symbol") or "").upper() not in {"EUR/USD", "GBP/USD"}]
    # Operational signals first, then strong market opportunities, then watch-only rows.
    rows.sort(key=lambda x: (x["action"] not in {"PAPER_ENTRY", "PAPER_SIGNAL"}, x.get("opportunity_alert") not in {"STRONG_MOVE", "OPPORTUNITY"}, -(x.get("opportunity_score") or 0), -(x["probability"] or 0)))

    prices = {r["symbol"]: r["price"] for r in rows if r.get("symbol") and r.get("price") is not None}
    closed = PORTFOLIO.evaluate_exits(prices)
    PORTFOLIO.mark_to_market(prices)

    # Prevent same-cycle churn: a position closed by SL/TP is not
    # reopened from the identical signal during this monitor pass.
    closed_symbols = {
        str(item.get("symbol") or "").upper()
        for item in closed
    }
    for signal in operational:
        symbol = str(signal.get("symbol") or "").upper()
        if symbol in closed_symbols:
            continue
        PORTFOLIO.open_signal(signal, allocation_pct=0.25)
    PORTFOLIO.mark_to_market(prices)

    # Independent AGGRESSIVE paper account: top-ranked valid setups, separate
    # capital and P/L. Only open when direction, price, SL and all targets form
    # a coherent setup; never fabricate missing levels.
    aggressive_closed = AGGRESSIVE_PORTFOLIO.evaluate_exits(prices)
    AGGRESSIVE_PORTFOLIO.mark_to_market(prices)
    aggressive_closed_symbols = {str(item.get("symbol") or "").upper() for item in aggressive_closed}
    candidates = sorted(
        [row for row in rows if str(row.get("symbol") or "").upper() not in {"EUR/USD", "GBP/USD"}],
        key=lambda x: (
            -(float(x.get("opportunity_score") or 0)),
            -(float(x.get("probability") or 0)),
            -(float(x.get("quality") or 0)),
        ),
    )
    for candidate in candidates:
        symbol = str(candidate.get("symbol") or "").upper()
        if not symbol or symbol in aggressive_closed_symbols:
            continue
        if float(candidate.get("probability") or 0) < 45:
            continue
        paper_candidate = dict(candidate)
        paper_candidate["action"] = "PAPER_SIGNAL"
        AGGRESSIVE_PORTFOLIO.open_signal(
            paper_candidate, allocation_pct=0.25, risk_pct=0.015, max_allocation_pct=0.35
        )
        # At most one fresh entry per symbol per run; portfolio itself blocks duplicates.
    AGGRESSIVE_PORTFOLIO.mark_to_market(prices)

    # Separate aggressive account for Forex symbols already analyzed by Gagarin.
    forex_symbols = {str(item.symbol).upper() for item in commodities if str(getattr(item, "category", "")).strip().lower() == "forex"}
    forex_rows = [row for row in rows if str(row.get("symbol") or "").upper() in forex_symbols]
    forex_prices = {str(row["symbol"]).upper(): float(row["price"]) for row in forex_rows if row.get("price") is not None and float(row["price"]) > 0}
    forex_closed = FOREX_AGGRESSIVE_PORTFOLIO.evaluate_exits(forex_prices)
    FOREX_AGGRESSIVE_PORTFOLIO.mark_to_market(forex_prices)
    forex_closed_symbols = {str(item.get("symbol") or "").upper() for item in forex_closed}
    forex_candidates = sorted(forex_rows, key=lambda x: (-(float(x.get("opportunity_score") or 0)), -(float(x.get("probability") or 0)), -(float(x.get("quality") or 0))))
    # Forex is retained as auxiliary context and existing positions are managed,
    # but no new autonomous Forex paper entries are opened.
    FOREX_AGGRESSIVE_PORTFOLIO.mark_to_market(forex_prices)

    # Day trading registry: update open positions with any prices present.
    # PostgreSQL is the source of truth; the JSON file is only a local fallback.
    day_registry = (load_state("day_registry") if _DB_READY else None) or load_day_registry()
    day_registry = run_day_registry(day_registry)
    if _DB_READY:
        save_state("day_registry", day_registry)
    day_snap = day_summary(day_registry)

    # Persist before returning the completed analysis response.
    if _DB_READY:
        save_state("portfolio_main", PORTFOLIO.export_state())
        save_state("portfolio_aggressive", AGGRESSIVE_PORTFOLIO.export_state())
        save_state("portfolio_forex_aggressive", FOREX_AGGRESSIVE_PORTFOLIO.export_state())

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "PAPER ONLY",
        "universe": len(rows),
        "signals": operational,
        "closed": closed,
        "ranking": rows,
        "portfolio": PORTFOLIO.snapshot(),
        "aggressive_portfolio": AGGRESSIVE_PORTFOLIO.snapshot(),
        "forex_aggressive_portfolio": FOREX_AGGRESSIVE_PORTFOLIO.snapshot(),
        "forex_universe": sorted(forex_symbols),
        "forex_rows": forex_rows,
        "forex_closed": forex_closed,
        "forex_note": "Solo coppie Forex già presenti nell'universo operativo Gagarin; ETF e indici esclusi perché non sono analizzati dal motore attuale.",
        "aggressive_closed": aggressive_closed,
        "day_registry": day_snap,
    }


# Sputnik is a catalyst/context layer, never an order generator.
from engine.sputnik_intelligence import match_event_instruments, historical_analogues


def _is_sputnik_setup_confirmed(row: dict) -> bool:
    """Fail closed unless live data, explicit volume confirmation and coherent levels exist."""
    if not isinstance(row, dict) or str(row.get("data_status") or "").upper() != "LIVE":
        return False
    if row.get("live") is not True or row.get("volume_confirmed") is not True:
        return False
    try:
        price = float(row.get("price"))
        stop = float(row.get("stop"))
        target = float(row.get("tp1"))
        relative_volume = float(row.get("relative_volume"))
    except (TypeError, ValueError):
        return False
    if price <= 0 or relative_volume < 1.0:
        return False
    direction = str(row.get("direction") or "").upper()
    if direction == "LONG":
        return stop < price < target
    if direction == "SHORT":
        return target < price < stop
    return False


def _run_sputnik_confirmation(events: list[dict]) -> dict:
    """Refresh Gagarin analysis and contextualize Sputnik public events."""
    errors = validate_universe()
    if errors:
        raise RuntimeError("CONFIGURATION_BLOCKED: " + ", ".join(errors))
    results = analyze_universe(enabled_commodities())
    decisions = evaluate_states(results)
    by_symbol = {str(getattr(d, "symbol", "")).upper(): d for d in decisions}
    for state in results:
        symbol = str(getattr(state, "symbol", "")).upper()
        decision = by_symbol.get(symbol)
        metadata = getattr(state, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
            state.metadata = metadata
        metadata["gagarin_action"] = getattr(decision, "action", "NO_DECISION")
        metadata["gagarin_reason"] = getattr(decision, "reason", "DECISION_NOT_RETURNED")
    rows = [_state_json(state) for state in results]
    output = []
    for event in events:
        if not isinstance(event, dict):
            continue
        domains = event.get("domains") if isinstance(event.get("domains"), list) else []
        matched = match_event_instruments(rows, domains)
        eligible = [
            row for row in matched
            if row.get("action") in {"PAPER_ENTRY", "PAPER_SIGNAL"}
            and _is_sputnik_setup_confirmed(row)
        ]
        output.append({
            "event_id": str(event.get("event_id") or "")[:200],
            "title": str(event.get("title") or "")[:300],
            "source_url": str(event.get("url") or "")[:1000],
            "published": str(event.get("published") or "")[:100],
            "domains": [str(x).upper() for x in domains],
            "historical_analogues": historical_analogues(str(event.get("title") or "")),
            "status": "GAGARIN_SETUP_CONFIRMED" if eligible else (
                "NO_MATCHING_INSTRUMENT" if not matched else "WATCH_ONLY"
            ),
            "matched_instruments": matched[:10],
            "eligible_setups": eligible[:5],
            "trade_placed": False,
        })
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "PAPER ONLY",
        "analysis_type": "SPUTNIK_CATALYST_CONFIRMATION",
        "trade_placed": False,
        "events": output,
    }


@app.post("/api/sputnik/confirm")
def confirm_sputnik_catalysts(payload: dict, x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list) or not events:
        raise HTTPException(status_code=422, detail="Payload must contain a non-empty events list")
    if len(events) > 20:
        raise HTTPException(status_code=422, detail="At most 20 catalyst events per request")
    if not RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Analysis already running")
    try:
        return _run_sputnik_confirmation(events)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    finally:
        RUN_LOCK.release()


@app.get("/health")
def health():
    return {"status": "ok", "service": "gagarin-cloud", "mode": "PAPER ONLY"}


@app.post("/api/monitor")
def monitor(x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    if not RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Analysis already running")
    try:
        return _run_gagarin(on_demand=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    finally:
        RUN_LOCK.release()


@app.get("/api/portfolio")
def portfolio(x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    return {"mode": "PAPER ONLY", "portfolio": PORTFOLIO.snapshot()}


@app.get("/api/day")
def day_registry(x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    return {"mode": "PAPER ONLY", "day_registry": day_summary(load_day_registry())}


@app.get("/api/status")
def status(x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    return {
        "status": "online",
        "service": "GAGARIN CLOUD",
        "mode": "PAPER ONLY",
        "execution_enabled": os.getenv("EXECUTION_ENABLED", "0") == "1",
        "persistence": "POSTGRESQL" if _DB_READY else "DISABLED",
        "broker": os.getenv("EXECUTION_BROKER", "paper"),
    }


@app.post("/api/run")
def run_analysis(x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    if not RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Analysis already running")
    try:
        return _run_gagarin(on_demand=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    finally:
        RUN_LOCK.release()


@app.get("/")
def dashboard(request: Request):
    if _valid_app_session(request.cookies.get(_APP_COOKIE)):
        return RedirectResponse("/static/intelligence.html")
    return RedirectResponse("/login", status_code=303)


DASHBOARD = r"""<!doctype html>
<html lang="it">
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0f14">
<link rel="manifest" href="/static/manifest.webmanifest">
<link rel="icon" href="/static/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/static/icon.svg">
<title>GAGARIN CLOUD</title>
<style>
:root{color-scheme:dark;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display",sans-serif}
body{margin:0;background:#0b0f14;color:#f4f7fb;padding:20px}
h1{font-size:28px;margin:0 0 4px}.sub{color:#9aa5b1;margin-bottom:18px}
button,input{width:100%;box-sizing:border-box;border-radius:14px;border:1px solid #26303c;background:#121923;color:#fff;padding:14px;font-size:16px}
button{background:#1f7aff;border:0;font-weight:700;margin-top:10px}
.card{background:#111821;border:1px solid #202a35;border-radius:18px;padding:16px;margin:12px 0}
.status{display:flex;justify-content:space-between}.green{color:#39d98a}
.signal{border-left:4px solid #39d98a}.opportunity{border-left:4px solid #f5b942}.wait{border-left:4px solid #6f7b88}
.row{display:flex;justify-content:space-between;gap:10px;margin:6px 0}.muted{color:#9aa5b1}.big{font-size:20px;font-weight:700}
small{color:#7f8a97}
</style>
</head>
<body>
<h1>🚀 GAGARIN CLOUD</h1>
<div class="sub">Controllo da iPhone · Paper Only</div>

<div class="card">
<input id="key" type="password" placeholder="Cloud API Key">
<button onclick="run()">ANALIZZA ORA</button>
<div id="status" class="muted" style="margin-top:12px">Pronto.</div>
</div>
<div class="card"><div class="big">💶 PORTAFOGLIO PAPER</div><div class="row"><span>Capitale iniziale</span><b id="cash-init">€100,00</b></div><div class="row"><span>Disponibile</span><b id="cash">—</b></div><div class="row"><span>P/L realizzato</span><b id="pnl">—</b></div><div class="row"><span>Equity</span><b id="equity">—</b></div><div id="positions" class="muted">Nessuna posizione aperta.</div></div>
<div class="card"><div class="big">💱 AGGRESSIVE PAPER — FOREX</div><div class="muted">Solo coppie valutarie già analizzate dal motore Gagarin. Capitale separato €100 · probabilità ≥45/100 · ingresso, SL e TP verificabili · rischio obiettivo 1,5% per operazione. ETF e indici non sono inclusi perché il motore attuale non li analizza.</div><div class="row"><span>Disponibile</span><b id="fx-cash">€100,00</b></div><div class="row"><span>Posizioni aperte</span><b id="fx-open">0</b></div><div class="row"><span>Operazioni chiuse</span><b id="fx-closed">0</b></div><div class="row"><span>P/L non realizzato</span><b id="fx-unrealized">€0,00</b></div><div class="row"><span>P/L realizzato</span><b id="fx-realized">€0,00</b></div><div class="row"><span>Equity</span><b id="fx-equity">€100,00</b></div><div id="fx-positions" class="muted">Nessuna posizione Forex aperta.</div><div id="fx-candidates" class="muted"></div></div>
<div class="card"><div class="big">📈 DAY TRADING</div><div class="row"><span>Capitale</span><b id="day-capital">€100,00</b></div><div class="row"><span>Aperte</span><b id="day-open">0</b></div><div class="row"><span>Chiuse</span><b id="day-closed">0</b></div><div class="row"><span>P/L non realizzato</span><b id="day-unrealized">€0,00</b></div><div class="row"><span>P/L realizzato</span><b id="day-realized">€0,00</b></div><div class="row"><span>Equity</span><b id="day-equity">€100,00</b></div><div id="day-positions" class="muted">Nessuna posizione day aperta.</div></div>
<div class="card" style="border:2px solid #f5b942"><div class="big">⚡ AGGRESSIVE PAPER</div><div class="muted">Conto separato · capitale iniziale €100 · rischio per operazione più alto. Aperture e chiusure simulate su SL/TP.</div><div class="row"><span>Disponibile</span><b id="agg-cash">€100,00</b></div><div class="row"><span>Posizioni aperte</span><b id="agg-open">0</b></div><div class="row"><span>Operazioni chiuse</span><b id="agg-closed">0</b></div><div class="row"><span>P/L non realizzato</span><b id="agg-unrealized">€0,00</b></div><div class="row"><span>P/L realizzato</span><b id="agg-realized">€0,00</b></div><div class="row"><span>Equity</span><b id="agg-equity">€100,00</b></div><div id="agg-positions" class="muted">Nessuna posizione aggressiva aperta.</div><div id="agg-history" class="muted"></div></div><div id="content"></div>
<script>
const keyEl=document.getElementById('key');
keyEl.value=localStorage.getItem('gagarin_key')||'';
function esc(v){return String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function money(v){return v==null?'—':Number(v).toLocaleString('it-IT',{maximumFractionDigits:6});}
async function run(){
 const key=keyEl.value.trim(); if(!key){alert('Inserisci la Cloud API Key');return;}
 localStorage.setItem('gagarin_key',key);
 const s=document.getElementById('status'); s.textContent='Analisi in corso…';
 try{
  const r=await fetch('/api/run',{method:'POST',headers:{'X-API-Key':key}});
  const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Errore');
  s.innerHTML='<span class="green">● ONLINE</span> · '+esc(d.timestamp_utc);
  const p=d.portfolio||{}; document.getElementById('cash').textContent='€'+Number(p.cash||0).toFixed(2); document.getElementById('pnl').textContent='€'+Number(p.realized_pnl||0).toFixed(2); document.getElementById('equity').textContent='€'+Number(p.equity||0).toFixed(2);
  document.getElementById('positions').innerHTML=(p.open_positions||[]).length ? p.open_positions.map(x=>'<div class="card signal"><b>🟢 '+esc(x.commodity)+' '+esc(x.direction)+'</b><div class="row"><span>Entry</span><b>'+money(x.entry)+'</b></div><div class="row"><span>Allocazione</span><b>'+money(x.allocation)+'</b></div><div class="row"><span>SL / TP3</span><b>'+money(x.stop)+' / '+money(x.tp3)+'</b></div></div>').join('') : 'Nessuna posizione aperta.';
  const agg=d.aggressive_portfolio||{}; const aggOpen=agg.open_positions||[], aggClosed=agg.closed_positions||[]; document.getElementById('agg-cash').textContent='€'+Number(agg.cash??100).toFixed(2); document.getElementById('agg-open').textContent=aggOpen.length; document.getElementById('agg-closed').textContent=aggClosed.length; document.getElementById('agg-unrealized').textContent='€'+Number(agg.unrealized_pnl||0).toFixed(2); document.getElementById('agg-realized').textContent='€'+Number(agg.realized_pnl||0).toFixed(2); document.getElementById('agg-equity').textContent='€'+Number(agg.equity||100).toFixed(2); document.getElementById('agg-positions').innerHTML=aggOpen.length?aggOpen.map(x=>'<div class="card opportunity"><b>⚡ '+esc(x.commodity)+' '+esc(x.direction)+'</b><div class="row"><span>Apertura</span><b>'+money(x.entry)+'</b></div><div class="row"><span>Prezzo attuale</span><b>'+money(x.mark_price)+'</b></div><div class="row"><span>SL / TP1 / TP2 / TP3</span><b>'+money(x.stop)+' / '+money(x.tp1)+' / '+money(x.tp2)+' / '+money(x.tp3)+'</b></div><div class="row"><span>P/L non realizzato</span><b>€'+Number(x.unrealized_pnl||0).toFixed(2)+'</b></div></div>').join(''):'Nessuna posizione aggressiva aperta.'; document.getElementById('agg-history').innerHTML=aggClosed.length?'<b>Ultime chiuse</b>'+aggClosed.slice(-5).reverse().map(x=>'<div class="row"><span>'+esc(x.commodity)+' '+esc(x.direction)+' · '+esc(x.closed_at||'')+'</span><b>€'+Number(x.pnl||0).toFixed(2)+'</b></div>').join(''):'Nessuna operazione chiusa.';
  const fx=d.forex_aggressive_portfolio||{}; const fxOpen=fx.open_positions||[], fxClosed=fx.closed_positions||[]; document.getElementById("fx-cash").textContent="€"+Number(fx.cash??100).toFixed(2); document.getElementById("fx-open").textContent=fxOpen.length; document.getElementById("fx-closed").textContent=fxClosed.length; document.getElementById("fx-unrealized").textContent="€"+Number(fx.unrealized_pnl||0).toFixed(2); document.getElementById("fx-realized").textContent="€"+Number(fx.realized_pnl||0).toFixed(2); document.getElementById("fx-equity").textContent="€"+Number(fx.equity||100).toFixed(2); document.getElementById("fx-positions").innerHTML=fxOpen.length?fxOpen.map(x=>"<div class='card opportunity'><b>"+esc(x.commodity)+" "+esc(x.direction)+"</b><div class='row'><span>Entry / SL / TP3</span><b>"+money(x.entry)+" / "+money(x.stop)+" / "+money(x.tp3)+"</b></div><div class='row'><span>Prezzo aggiornato</span><b>"+money(x.mark_price)+"</b></div><div class='row'><span>P/L non realizzato</span><b>€"+Number(x.unrealized_pnl||0).toFixed(2)+"</b></div></div>").join(""):"Nessuna posizione Forex aperta."; document.getElementById("fx-candidates").innerHTML="<b>Coppie analizzate in questo ciclo</b><div>"+(d.forex_universe||[]).map(esc).join(" · ")+"</div>"+(d.forex_rows||[]).map(x=>"<div class='row'><span>"+esc(x.symbol)+" · "+esc(x.direction||x.opportunity_direction||"NONE")+" · prob. "+esc(x.probability)+"</span><b>"+money(x.entry)+" / "+money(x.stop)+" / "+money(x.tp3)+"</b></div>").join("");
  const day=d.day_registry||{}; document.getElementById('day-capital').textContent='€'+Number(day.capital||100).toFixed(2); document.getElementById('day-open').textContent=day.open_count||0; document.getElementById('day-closed').textContent=day.closed_count||0; document.getElementById('day-unrealized').textContent='€'+Number(day.unrealized_pnl||0).toFixed(2); document.getElementById('day-realized').textContent='€'+Number(day.realized_pnl||0).toFixed(2); document.getElementById('day-equity').textContent='€'+Number(day.equity||100).toFixed(2);
  document.getElementById('day-positions').innerHTML=(day.positions||[]).length ? day.positions.map(x=>'<div class="card signal"><b>🟢 '+esc(x.symbol)+' '+esc(x.side)+'</b><div class="row"><span>Entry</span><b>'+money(x.entry)+'</b></div><div class="row"><span>Stop</span><b>'+money(x.stop)+'</b></div><div class="row"><span>Uscita</span><b>'+esc(x.exit_rule||'—')+'</b></div><div class="row"><span>Qty</span><b>'+money(x.qty)+'</b></div></div>').join('') : 'Nessuna posizione day aperta.';
  let html='';
  if(!d.signals.length) html+='<div class="card"><div class="big">🟡 NESSUNA ENTRATA</div><div class="muted">Il governor Gagarin non ha autorizzato segnali.</div></div>';
  for(const x of d.signals){
   html+='<div class="card signal"><div class="big">🟢 '+esc(x.commodity)+' '+esc(x.direction)+'</div>'+
   '<div class="row"><span>Probabilità</span><b>'+esc(x.probability)+'%</b></div>'+
   '<div class="row"><span>Entry</span><b>'+money(x.entry)+'</b></div>'+
   '<div class="row"><span>Stop</span><b>'+money(x.stop)+'</b></div>'+
   '<div class="row"><span>TP1 / TP2 / TP3</span><b>'+money(x.tp1)+' / '+money(x.tp2)+' / '+money(x.tp3)+'</b></div></div>';
  }
  html+='<div class="card"><div class="big">📊 CLASSIFICA</div>';
  d.ranking.forEach((x,i)=>{const alert=x.opportunity_alert||"NONE"; const cls=x.action==='PAPER_SIGNAL'?'signal':(alert==='STRONG_MOVE'||alert==='OPPORTUNITY'?'opportunity':'wait'); html+='<div class="card '+cls+'"><div class="row"><b>'+(i+1)+'. '+esc(x.commodity)+'</b><b>'+(x.action==='PAPER_SIGNAL'?'PAPER_SIGNAL':esc(alert))+'</b></div><small>'+esc(x.direction||x.opportunity_direction)+' · 24h '+esc(x.move_24h_pct)+'% · 4h '+esc(x.move_4h_pct)+'% · Score '+esc(x.opportunity_score)+'</small><div class="muted" style="margin-top:6px">Prob '+esc(x.probability)+' · Q '+esc(x.quality)+' · C '+esc(x.confidence)+'</div></div>';});
  html+='</div>'; document.getElementById('content').innerHTML=html;
 }catch(e){s.textContent='Errore: '+e.message;}
}
</script>
</body>
</html>"""
