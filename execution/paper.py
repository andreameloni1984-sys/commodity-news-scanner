from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import ExecutionOrder, ExecutionResult

LEDGER = Path("execution_paper_orders.jsonl")

def submit(order: ExecutionOrder) -> ExecutionResult:
    record = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mode":"PAPER", "status":"ACCEPTED", "symbol":order.symbol, "side":order.side, "quantity":order.quantity, "entry":order.entry, "stop":order.stop, "tp1":order.tp1, "tp2":order.tp2, "tp3":order.tp3, "source":order.source}
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return ExecutionResult(True, "PAPER", order.symbol, f"PAPER-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}", "Paper order recorded; no broker was contacted.")
