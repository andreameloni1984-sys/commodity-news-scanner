"""Comandi Telegram per IBKR (istruzioni paper/demo)."""
from __future__ import annotations

from engine.ibkr_client import (
    get_ibkr_status,
    prepare_from_signal,
    prepare_order_instruction,
    format_instruction_message,
)


def handle_ibkr_command(argument: str) -> str:
    """Gestisce /ibkr e /ibkr_prepare."""
    arg = (argument or "").strip()
    if not arg or arg.lower() in {"status", "stato"}:
        return get_ibkr_status()

    parts = arg.split()
    if len(parts) < 2:
        return (
            "Uso:\n"
            "/ibkr status — stato collegamento\n"
            "/ibkr prepare SYMBOL LONG|SHORT [QTY]\n"
            "Esempio: /ibkr prepare AAPL LONG 1\n"
            "Prepara un'istruzione paper da confermare manualmente su IBKR."
        )

    action = parts[0].lower()
    if action != "prepare":
        return "Comando non riconosciuto. Usa /ibkr status o /ibkr prepare SYMBOL LONG 1"

    symbol = parts[1].upper()
    direction = parts[2].upper() if len(parts) > 2 else "LONG"
    qty = 1.0
    if len(parts) > 3:
        try:
            qty = float(parts[3])
        except ValueError:
            return "Quantità non valida."

    payload, message = prepare_from_signal(symbol, direction, qty)
    return message
