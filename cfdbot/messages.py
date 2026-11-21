"""Testi dei messaggi Telegram (in italiano, testo semplice)."""
from __future__ import annotations

from .instruments import Instrument

FOOTER = "Segnale automatico, non è una consulenza finanziaria. Ordine da inserire a mano su Trading 212."


def f(x: float, d: int) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sizing_lines(pos: dict) -> list[str]:
    if not pos.get("risk_eur"):
        return ["Rischio: imposta ACCOUNT_SIZE per avere la dimensione della posizione calcolata."]
    return [
        f"Rischio: {pos['risk_pct']:g}% del conto = {f(pos['risk_eur'], 0)} €",
        f"Quantità indicativa: {f(pos['units'], 2)} unità del sottostante "
        f"(verifica su Trading 212 che la perdita allo stop sia circa {f(pos['risk_eur'], 0)} €)",
    ]


def new_signal(inst: Instrument, pos: dict) -> str:
    d = inst.decimals
    arrow = "🟢 LONG (compra)" if pos["direction"] == "LONG" else "🔴 SHORT (vendi)"
    lines = [
        f"🚨 NUOVO SEGNALE CFD — {inst.name}",
        f"{arrow} · CFD Trading 212: {inst.t212}",
        "",
        f"Ingresso: {f(pos['entry'], d)}",
        f"Stop loss: {f(pos['stop'], d)}  (distanza {f(pos['stop_dist'], d)})",
        f"Take profit: {f(pos['target'], d)}  (distanza {f(pos['target_dist'], d)})",
        "Rischio/rendimento 1:2 · durata massima 5 giorni di borsa",
        "",
        *sizing_lines(pos),
        "",
        "Perché: " + "; ".join(pos["reasons"]),
        "",
        "Se il prezzo su Trading 212 è diverso, mantieni le stesse distanze di stop e take profit.",
        FOOTER,
    ]
    return "\n".join(lines)


def closed(inst: Instrument, pos: dict, stats: dict) -> str:
    d = inst.decimals
    icon = {"target": "✅ TAKE PROFIT RAGGIUNTO", "stop": "❌ STOP LOSS TOCCATO", "tempo": "⏱️ CHIUDI: SCADUTI 5 GIORNI"}[pos["exit_reason"]]
    lines = [
        f"{icon} — {inst.name} {pos['direction']}",
        f"Ingresso {f(pos['entry'], d)} → uscita {f(pos['exit'], d)} · risultato {pos['r']:+.2f}R",
    ]
    if pos["exit_reason"] == "tempo":
        lines.append("Chiudi la posizione su Trading 212 se è ancora aperta.")
    lines.append(f"Storico bot: {stats['n']} operazioni · vincenti {stats['win']:.0%} · totale {stats['total']:+.1f}R")
    return "\n".join(lines)


def daily_summary(rows: list[str], open_lines: list[str], stats: dict) -> str:
    lines = ["☀️ CFD Bot — riepilogo del giorno", ""]
    lines += ["Posizioni aperte:"] + (open_lines or ["nessuna"])
    lines += ["", "Trend degli strumenti:"] + rows
    if stats["n"]:
        lines += ["", f"Storico: {stats['n']} operazioni · vincenti {stats['win']:.0%} · totale {stats['total']:+.1f}R"]
    lines += ["", "Il bot controlla i mercati ogni ora e scrive solo quando c'è un segnale o una chiusura."]
    return "\n".join(lines)
