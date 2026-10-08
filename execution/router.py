from __future__ import annotations
import os
from .models import ExecutionOrder, ExecutionResult
from .paper import submit as submit_paper

def _quantity(state):
    try: return max(0.0,float(os.getenv("EXECUTION_DEFAULT_QUANTITY","1")))
    except ValueError: return 1.0

def order_from_state(state):
    return ExecutionOrder(str(getattr(state,"symbol","")).upper(),str(getattr(state,"setup_direction","")).upper(),_quantity(state),float(state.entry),getattr(state,"stop",None),getattr(state,"tp1",None),getattr(state,"tp2",None),getattr(state,"tp3",None))

def execute_state(state):
    symbol=str(getattr(state,"symbol",""))
    if os.getenv("EXECUTION_ENABLED","0")!="1": return ExecutionResult(False,"DISABLED",symbol,message="Execution layer disabled.")
    meta=getattr(state,"metadata",{}) or {}
    if str(meta.get("gagarin_action","")).upper() not in {"PAPER_ENTRY", "PAPER_SIGNAL"}: return ExecutionResult(False,"BLOCKED",symbol,message="Only canonical Gagarin PAPER_ENTRY/PAPER_SIGNAL can reach the paper execution adapter.")
    order=order_from_state(state); broker=os.getenv("EXECUTION_BROKER","paper").lower()
    if broker=="paper": return submit_paper(order)
    if broker=="ibkr":
        from .ibkr import submit as submit_ibkr
        return submit_ibkr(order)
    return ExecutionResult(False,"BLOCKED",order.symbol,message=f"Unknown execution broker: {broker}")
