from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse\nfrom fastapi.staticfiles import StaticFiles

from commodities.universe import enabled_commodities, validate_universe
from engine.gagarin import analyze_universe
from soyuz_gagarin.adapter import evaluate_states
from paper_portfolio import PaperPortfolio

app = FastAPI(title="SOYUZ GAGARIN CLOUD", version="1.0")\napp.mount("/static", StaticFiles(directory="static"), name="static")
RUN_LOCK = Lock()
PORTFOLIO = PaperPortfolio(100.0)


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
    operational = [r for r in rows if r["action"] == "PAPER_SIGNAL"]
    # Operational signals first, then strong market opportunities, then normal WAITs.
    rows.sort(key=lambda x: (x["action"] != "PAPER_SIGNAL", x.get("opportunity_alert") not in {"STRONG_MOVE", "OPPORTUNITY"}, -(x.get("opportunity_score") or 0), -(x["probability"] or 0)))

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

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "PAPER ONLY",
        "universe": len(rows),
        "signals": operational,
        "closed": closed,
        "ranking": rows,
        "portfolio": PORTFOLIO.snapshot(),
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


@app.get("/api/status")
def status(x_api_key: str | None = Header(default=None)):
    _authorize(x_api_key)
    return {
        "status": "online",
        "service": "GAGARIN CLOUD",
        "mode": "PAPER ONLY",
        "execution_enabled": os.getenv("EXECUTION_ENABLED", "0") == "1",
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
<meta name="theme-color" content="#0b0f14">\n<link rel="manifest" href="/static/manifest.webmanifest">\n<link rel="icon" href="/static/icon.svg" type="image/svg+xml">\n<link rel="apple-touch-icon" href="/static/icon.svg">
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
<div id="portfolio" class="card"><div class="big">💶 PORTAFOGLIO PAPER</div><div class="row"><span>Capitale iniziale</span><b>€100,00</b></div><div class="row"><span>Disponibile</span><b id="cash">—</b></div><div class="row"><span>P/L realizzato</span><b id="pnl">—</b></div><div class="row"><span>Equity</span><b id="equity">—</b></div><div id="positions" class="muted">Nessuna posizione aperta.</div></div><div id="content"></div>
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
  document.getElementById('positions').innerHTML=(p.open_positions||[]).length ? p.open_positions.map(x=>'<div class="card signal"><b>🟢 '+esc(x.commodity)+' '+esc(x.direction)+'</b><div class="row"><span>Entry</span><b>'+money(x.entry)+'</b></div><div class="row"><span>Allocazione</span><b>€'+Number(x.allocation).toFixed(2)+'</b></div><div class="row"><span>SL / TP3</span><b>'+money(x.stop)+' / '+money(x.tp3)+'</b></div></div>').join('') : 'Nessuna posizione aperta.';
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
