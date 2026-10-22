"""Client IBKR per Gagarin — preparazione istruzioni di ordine.

PAPER / DEMO ONLY. Non piazza ordini live.

La modalità corrente è REVIEW_AND_APPROVE: il bot prepara un'istruzione
che l'utente deve rivedere e inviare manualmente da IBKR (Client Portal / Desktop).

Per un collegamento completo (Client Portal Gateway o TWS API) servono:
- IB Gateway / TWS in esecuzione (porta 4002 paper / 7497 TWS paper)
- oppure Client Portal Gateway con sessione autenticata
- credenziali paper (username/password separati dal live)

Questo modulo fornisce:
- verifica credenziali ambiente
- preparazione payload ordine
- formattazione messaggio Telegram con i dettagli da confermare
"""
from __future__ import annotations

import os
from typing import Optional, Any


def ibkr_configured() -> bool:
    """True se le variabili d'ambiente base sono presenti."""
    return bool(
        os.getenv("IBKR_ACCOUNT", "").strip()
        or os.getenv("IBKR_PAPER_ACCOUNT", "").strip()
    )


def get_ibkr_status() -> str:
    if ibkr_configured():
        acct = os.getenv("IBKR_PAPER_ACCOUNT") or os.getenv("IBKR_ACCOUNT") or "N/D"
        return (
            f"✅ IBKR configurato (account: {acct})\n"
            "Modalità: REVIEW_AND_APPROVE — solo istruzioni, nessun ordine automatico."
        )
    return (
        "⚪ IBKR non configurato.\n"
        "Imposta IBKR_PAPER_ACCOUNT (o IBKR_ACCOUNT) su Render.\n"
        "Per il Gateway: avvia IB Gateway paper (porta 4002) o TWS paper (7497)."
    )


def prepare_order_instruction(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    limit_price: Optional[float] = None,
    time_in_force: str = "DAY",
    reason: str = "",
) -> dict[str, Any]:
    """Prepara un payload di istruzione ordine. Non lo invia."""
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        return {"error": "SIDE deve essere BUY o SELL"}
    if quantity <= 0:
        return {"error": "QUANTITY deve essere positiva"}
    order_type = order_type.upper()
    if order_type not in {"MARKET", "LIMIT"}:
        return {"error": "ORDER_TYPE deve essere MARKET o LIMIT"}
    if order_type == "LIMIT" and (limit_price is None or limit_price <= 0):
        return {"error": "LIMIT richiede limit_price positivo"}

    payload = {
        "symbol": symbol.upper(),
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "time_in_force": time_in_force.upper(),
        "paper_only": True,
        "requires_manual_submit": True,
        "reason": reason,
    }
    if limit_price is not None:
        payload["limit_price"] = limit_price
    return payload


def format_instruction_message(payload: dict[str, Any]) -> str:
    """Formatta l'istruzione per Telegram."""
    if "error" in payload:
        return f"❌ Istruzione non valida: {payload['error']}"

    lines = [
        "📋 ISTRUZIONE ORDINE IBKR — PAPER/DEMO",
        "━" * 28,
        "🧪 PAPER ONLY — nessun ordine inviato automaticamente.",
        "",
        f"Strumento: {payload['symbol']}",
        f"Lato: {payload['side']}",
        f"Quantità: {payload['quantity']}",
        f"Tipo: {payload['order_type']}",
    ]
    if payload.get("limit_price"):
        lines.append(f"Prezzo limite: {payload['limit_price']}")
    lines.append(f"Validità: {payload['time_in_force']}")
    if payload.get("reason"):
        lines.append(f"Motivo: {payload['reason']}")
    lines.extend([
        "",
        "Per inviare: apri IBKR Client Portal / Desktop,",
        "cerca lo strumento e conferma l'ordine manualmente.",
        "Oppure usa il link dell'istruzione se generato dal connettore.",
    ])
    return "\n".join(lines)


def prepare_from_signal(
    symbol: str,
    direction: str,
    quantity: float = 1.0,
    reason: str = "",
) -> tuple[dict[str, Any], str]:
    """Prepara istruzione da un segnale Gagarin (LONG→BUY, SHORT→SELL)."""
    side = "BUY" if direction.upper() == "LONG" else "SELL" if direction.upper() == "SHORT" else None
    if side is None:
        return {"error": f"Direzione non valida: {direction}"}, "Direzione non supportata."
    payload = prepare_order_instruction(
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type="MARKET",
        reason=reason or f"Segnale Gagarin {direction}",
    )
    return payload, format_instruction_message(payload)
