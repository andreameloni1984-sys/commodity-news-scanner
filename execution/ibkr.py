from __future__ import annotations
import os, requests
from .models import ExecutionOrder, ExecutionResult
TIMEOUT=int(os.getenv("EXECUTION_TIMEOUT_SECONDS","15"))
BASE_URL=os.getenv("IBKR_GATEWAY_URL","https://localhost:5000/v1/api").rstrip("/")
VERIFY_TLS=os.getenv("IBKR_VERIFY_TLS","0")=="1"

def _session():
    s=requests.Session(); s.verify=VERIFY_TLS; return s

def _account_id(session):
    r=session.get(f"{BASE_URL}/iserver/accounts", timeout=TIMEOUT); r.raise_for_status()
    accounts=r.json().get("accounts",[])
    if not accounts: raise RuntimeError("IBKR_NO_ACCOUNT_AVAILABLE")
    return str(accounts[0])

def submit(order: ExecutionOrder)->ExecutionResult:
    if os.getenv("PAPER_TRADING_ONLY","1")!="1":
        return ExecutionResult(False,"IBKR_BLOCKED",order.symbol,message="PAPER_TRADING_ONLY must remain enabled for this rollout.")
    s=_session(); account_id=_account_id(s)
    item={"acctId":account_id,"symbol":order.symbol,"side":"BUY" if order.side=="LONG" else "SELL","orderType":"LMT","price":order.entry,"tif":"DAY","quantity":order.quantity}
    r=s.post(f"{BASE_URL}/iserver/account/orders",json={"orders":[item]},timeout=TIMEOUT); r.raise_for_status()
    data=r.json(); oid=str((data[0] if isinstance(data,list) and data else {}).get("order_id",""))
    return ExecutionResult(True,"IBKR_PAPER",order.symbol,oid,"Order submitted to the configured IBKR Client Portal session.")
