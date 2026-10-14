from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from commodities.universe import enabled_commodities, validate_universe
from engine.gagarin import analyze_universe
from soyuz_gagarin.adapter import evaluate_states
from paper_portfolio import PaperPortfolio
from engine.day_registry import load as load_day_registry, run as run_day_registry, summary as day_summary
from state_store import ensure_schema, load_state, save_state

app = FastAPI(title="SOYUZ GAGARIN CLOUD", version="1.0")
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


def _state_json(state):
    meta = getattr(state, "metadata", {}) or {}
    return {
        "symbol": str(getattr(state, "symbol", "")).upper(),
        "commodity": getattr(state, "commodity", ""),
        "price": getattr(state, "price", None),
        "direction": getattr(state, "setup_direction", "") or "",
        "probability": getattr(state, "probability", None),
        "quality": getattr(state, "quality", None),
        "confidence": getattr(state, "confidence", None),
        "action": meta.get("gagarin_action", "WAIT"),
        "reason": meta.get("gagarin_reason", ""),
        "entry": getattr(state, "entry", None),
        "stop": getattr(state, "stop", None),
        "tp1": getattr(state, "tp1", None),
        "tp2": getattr(state, "tp2", None),
        "tp3": getattr(state, "tp3", None),
        "rr3": getattr(state, "rr3", None),
        "data_source": getattr(state, "data_source", None),
        "data_status": meta.get("data_status", "UNKNOWN"),
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


def _run_gagarin():
    errors = validate_universe()
    if errors:
        raise RuntimeError("CONFIGURATION_BLOCKED: " + ", ".join(errors))

    commodities = enabled_commodities()
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
        metadata["gagarin_action"] = decision.action if decision else "WAIT"
        metadata["gagarin_reason"] = decision.reason if decision else "NO_DECISION"

    rows = [_state_json(s) for s in results]
    operational = [r for r in rows if r["action"] in {"PAPER_ENTRY", "PAPER_SIGNAL"}]
    # Operational signals first, then strong market opportunities, then normal WAITs.
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
        rows,
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
    for candidate in forex_candidates:
        symbol = str(candidate.get("symbol") or "").upper()
        if not symbol or symbol in forex_closed_symbols or float(candidate.get("probability") or 0) < 45:
            continue
        paper_candidate = dict(candidate)
        paper_candidate["action"] = "PAPER_SIGNAL"
        FOREX_AGGRESSIVE_PORTFOLIO.open_signal(paper_candidate, allocation_pct=0.25, risk_pct=0.015, max_allocation_pct=0.35)
    FOREX_AGGRESSIVE_PORTFOLIO.mark_to_market(forex_prices)

    # Day trading registry: update open positions with any prices present.
    day_registry = load_day_registry()
    day_registry = run_day_registry(day_registry)
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "gagarin-cloud", "mode": "PAPER ONLY"}


@app.post("/api/monitor")
def monitor():
    if not RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Analysis already running")
    try:
        return _run_gagarin()
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
        return _run_gagarin()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    finally:
        RUN_LOCK.release()


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD)


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
