"""SOYUZ GAGARIN engine/data.py v2.0
Twelve Data -> FMP 5m -> Yahoo fallback.
FMP requires FMP_API_KEY in environment/GitHub Secrets.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os, time, requests
from config import LOOKBACK, LIVE_MAX_AGE_SECONDS, TIMEOUT_SECONDS, TWELVE_DATA_API_KEY
FMP_API_KEY=os.getenv("FMP_API_KEY","").strip()
try:
    from config import FMP_API_KEY as _F
    FMP_API_KEY=_F
except ImportError: pass

TWELVE_DATA_URL="https://api.twelvedata.com/time_series"
FMP_URL="https://financialmodelingprep.com/stable/historical-chart/5min"
YAHOO_URLS=("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}")
FMP_SYMBOLS={"XAU/USD":["GCUSD"],"XAG/USD":["SIUSD"],"XPT/USD":["PLUSD"],"XPD/USD":["PAUSD"],
             "WTI/USD":["CLUSD"],"BRENT/USD":["BZUSD"],"RICE/USD":["ZRUSD"],
             "SUGAR/USD":["SBUSD"],"COCOA/USD":["CCUSD"],"COFFEE/USD":["KCUSD"]}
YAHOO_SYMBOLS={"XAU/USD":"GC=F","XAG/USD":"SI=F","XPT/USD":"PL=F","XPD/USD":"PA=F",
               "WTI/USD":"CL=F","BRENT/USD":"BZ=F","RICE/USD":"ZR=F",
               "SUGAR/USD":"SB=F","COCOA/USD":"CC=F","COFFEE/USD":"KC=F"}
EFFECTIVE_LIVE_MAX_AGE_SECONDS=max(float(LIVE_MAX_AGE_SECONDS),360.0)
FUTURE_TIMESTAMP_TOLERANCE_SECONDS=90.0
HEADERS={"User-Agent":"Mozilla/5.0","Accept":"application/json,text/plain,*/*"}

def _parse_time(v):
    try:
        if v is None:return None
        if isinstance(v,(int,float)):return float(v)
        s=str(v).strip()
        if s.endswith("Z"):s=s[:-1]+"+00:00"
        d=datetime.fromisoformat(s)
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).timestamp()
    except Exception:return None

def _normalize(ts,o,h,l,c,v=0):
    try:
        ts=_parse_time(ts); o,h,l,c=map(float,(o,h,l,c)); v=float(v or 0)
        if ts is None or h<l or min(o,h,l,c)<=0:return None
        return {"timestamp":ts,"open":o,"high":h,"low":l,"close":c,"volume":v}
    except (TypeError,ValueError):return None

def _get(url,params,retries=0):
    last=None
    for i in range(retries+1):
        try:
            r=requests.get(url,params=params,headers=HEADERS,timeout=TIMEOUT_SECONDS)
            if r.status_code==429:
                last="HTTP_429: Too Many Requests"
                if i<retries: time.sleep(2**i); continue
                return None,last
            if r.status_code!=200:return None,f"HTTP_{r.status_code}: {r.text[:300]}"
            return r.json(),None
        except requests.RequestException as e:
            last=f"REQUEST_ERROR: {e}"
            if i<retries: time.sleep(2**i); continue
            return None,last
        except ValueError as e:return None,f"JSON_ERROR: {e}"
    return None,last or "REQUEST_FAILED"

def _atr(cs,period=14):
    if not cs:return 0.0
    tr=[]; prev=None
    for x in cs:
        tr.append(max(x["high"]-x["low"],abs(x["high"]-prev),abs(x["low"]-prev)) if prev is not None else x["high"]-x["low"])
        prev=x["close"]
    tr=tr[-period:]; return sum(tr)/len(tr) if tr else 0.0

def _twelve(symbol):
    if not TWELVE_DATA_API_KEY:return [],"TWELVE_DATA_API_KEY_MISSING"
    p,e=_get(TWELVE_DATA_URL,{"symbol":symbol,"interval":"5min","outputsize":LOOKBACK,
                              "apikey":TWELVE_DATA_API_KEY,"timezone":"UTC"},1)
    if e:return [],e
    if isinstance(p,dict) and p.get("status")=="error":return [],str(p.get("message") or "TWELVE_DATA_ERROR")
    out=[]
    for r in reversed((p or {}).get("values",[])):
        x=_normalize(r.get("datetime"),r.get("open"),r.get("high"),r.get("low"),r.get("close"),r.get("volume",0))
        if x:out.append(x)
    return out[-LOOKBACK:],None

def _fmp(symbol):
    if not FMP_API_KEY:return [],"FMP_API_KEY_MISSING"
    errs=[]
    for s in FMP_SYMBOLS.get(symbol,[]):
        p,e=_get(FMP_URL,{"symbol":s,"apikey":FMP_API_KEY},1)
        if e:errs.append(f"{s}: {e}");continue
        if not isinstance(p,list):
            errs.append(f"{s}: "+str((p or {}).get("message") or (p or {}).get("Error Message") or "INVALID_RESPONSE"));continue
        out=[]
        for r in p:
            x=_normalize(r.get("date"),r.get("open"),r.get("high"),r.get("low"),r.get("close"),r.get("volume",0))
            if x:out.append(x)
        out.sort(key=lambda x:x["timestamp"])
        if out:return out[-LOOKBACK:],None
        errs.append(f"{s}: NO_CANDLES")
    return []," | ".join(errs) or "FMP_SYMBOL_NOT_MAPPED"

def _yahoo(symbol):
    ys=YAHOO_SYMBOLS.get(symbol)
    if not ys:return [],"YAHOO_SYMBOL_NOT_MAPPED"
    now=int(time.time()); params={"period1":now-LOOKBACK*900,"period2":now,"interval":"5m","events":"history","includePrePost":"true","range":"5d"}
    errs=[]
    for u in YAHOO_URLS:
        p,e=_get(u.format(symbol=ys),params,0)
        if e:errs.append(e);continue
        q=((p or {}).get("chart",{}).get("result") or [])
        if not q:errs.append("YAHOO_EMPTY_RESULT");continue
        z=q[0]; ts=z.get("timestamp") or []; quote=((z.get("indicators") or {}).get("quote") or [{}])[0]
        out=[]
        for i,t in enumerate(ts):
            try:
                x=_normalize(t,quote["open"][i],quote["high"][i],quote["low"][i],quote["close"][i],(quote.get("volume") or [0]*len(ts))[i])
                if x:out.append(x)
            except (IndexError,TypeError):pass
        if out:return out[-LOOKBACK:],None
        errs.append("YAHOO_NO_CANDLES")
    return []," | ".join(errs) or "YAHOO_FAILED"

def _agg(cs,minutes):
    b={}
    step=minutes*60
    for x in cs:
        k=int(x["timestamp"]//step)*step
        if k not in b:b[k]={"timestamp":float(k),"open":x["open"],"high":x["high"],"low":x["low"],"close":x["close"],"volume":x["volume"]}
        else:
            b[k]["high"]=max(b[k]["high"],x["high"]); b[k]["low"]=min(b[k]["low"],x["low"])
            b[k]["close"]=x["close"]; b[k]["volume"]+=x["volume"]
    return [b[k] for k in sorted(b)]

def _mtf(cs):
    m5=list(cs); m15=_agg(cs,15); m30=_agg(cs,30); h1=_agg(cs,60)
    return {"M5":m5,"M15":m15,"M30":m30,"H1":h1,"5min":m5,"15min":m15,"30min":m30,"1h":h1}

def _final(state,cs,provider,error=None):
    if not cs:
        state.data_ok=False; state.live=False; state.data_source=provider
        state.metadata["data_error"]=error or "NO_DATA"; state.metadata["data_status"]="NO_DATA"
        if "DATA_MISSING" not in state.blockers:state.blockers.append("DATA_MISSING")
        return state
    cs=sorted(cs,key=lambda x:x["timestamp"]); state.candles=cs
    state.opens=[x["open"] for x in cs]; state.highs=[x["high"] for x in cs]; state.lows=[x["low"] for x in cs]
    state.closes=[x["close"] for x in cs]; state.volumes=[x["volume"] for x in cs]
    state.price=cs[-1]["close"]; state.previous_price=cs[-2]["close"] if len(cs)>1 else state.price
    state.atr=_atr(cs); state.mtf_data=_mtf(cs); latest=cs[-1]["timestamp"]
    now=datetime.now(timezone.utc).timestamp(); delta=now-latest
    status="FUTURE_TIMESTAMP" if delta < -FUTURE_TIMESTAMP_TOLERANCE_SECONDS else ("LIVE" if max(0,delta)<=EFFECTIVE_LIVE_MAX_AGE_SECONDS else ("MARKET_CLOSED_OR_DELAYED" if provider=="YAHOO" else "STALE"))
    age=max(0,delta)
    state.data_source=provider; state.data_age_seconds=age; state.metadata["provider"]=provider
    state.metadata["data_status"]=status; state.metadata["data_error"]=error
    state.metadata["last_bar_timestamp"]=datetime.fromtimestamp(latest,tz=timezone.utc).isoformat()
    state.metadata["effective_live_max_age_seconds"]=EFFECTIVE_LIVE_MAX_AGE_SECONDS
    if status=="FUTURE_TIMESTAMP":
        state.data_ok=False;state.live=False
        if "DATA_TIMESTAMP_INVALID" not in state.blockers:state.blockers.append("DATA_TIMESTAMP_INVALID")
        return state
    state.data_ok=True;state.live=(status=="LIVE")
    if not state.live and "DATA_NOT_LIVE" not in state.blockers:state.blockers.append("DATA_NOT_LIVE")
    return state

def load_data(state:Any,commodity:Any):
    symbol=commodity.symbol; state.commodity=commodity.name; state.symbol=symbol
    if symbol=="XAU/USD":
        cs,e=_twelve(symbol)
        if cs:return _final(state,cs,"TWELVE_DATA",e)
    cs,fe=_fmp(symbol)
    if cs:return _final(state,cs,"FMP",fe)
    cs,ye=_yahoo(symbol)
    return _final(state,cs,"YAHOO"," | ".join(x for x in (fe,ye) if x))
