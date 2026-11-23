"""Testi dei messaggi Telegram (in italiano, testo semplice)."""
from __future__ import annotations

from .instruments import Instrument

FOOTER = "Segnale automatico, non è una consulenza finanziaria. Ordine da inserire a mano su Trading 212."


def f(x: float, d: int) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Sotto questa quantità Trading 212 potrebbe non accettare l'ordine (il minimo varia per strumento).
SMALL_UNITS = 0.1


def sizing_lines(pos: dict) -> list[str]:
    if not pos.get("risk_eur"):
        return ["Rischio: imposta ACCOUNT_SIZE per avere la dimensione della posizione calcolata."]
    units, risk = pos["units"], pos["risk_eur"]
    lines = [
        f"Rischio: {pos['risk_pct']:g}% del conto = {f(risk, 2)} €",
        f"Quantità indicativa: {f(units, 4)} unità del sottostante "
        f"(verifica su Trading 212 che la perdita allo stop sia circa {f(risk, 2)} €)",
    ]
    unit_risk = pos.get("unit_risk_eur")
    if unit_risk and units < SMALL_UNITS:
        lines.append(
            f"⚠️ Quantità molto piccola: se Trading 212 non la accetta, il rischio sale. "
            f"Ogni 0,01 unità perde circa {f(unit_risk / 100, 2)} € allo stop: "
            f"con la quantità minima ammessa, rischio = quantità × {f(unit_risk, 2)} €.")
    return lines


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
        *([""] + pos["sputnik"]["lines"] + ["(contesto informativo da Sputnik: il segnale tecnico non cambia)"]
          if pos.get("sputnik", {}).get("lines") else []),
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


def rebound_signal(inst: Instrument, pos: dict) -> str:
    from .rebound import FOOTER as REBOUND_FOOTER, MAX_DAYS
    d = inst.decimals
    return "\n".join([
        f"🔄 SEGNALE RIMBALZO — {inst.name}",
        f"🟢 LONG (compra) · CFD Trading 212: {inst.t212}",
        "",
        f"Ingresso: {f(pos['entry'], d)}",
        f"Stop di sicurezza: {f(pos['stop'], d)}  (distanza {f(pos['stop_dist'], d)})",
        "Uscita: quando l'indice rimbalza (chiusura sopra la media a 5 giorni o vicino al massimo "
        f"della giornata) — te lo scrivo io. Al massimo {MAX_DAYS} giorni di borsa.",
        "",
        *sizing_lines(pos),
        "",
        "Perché: " + "; ".join(pos["reasons"]),
        "",
        REBOUND_FOOTER,
    ])


def rebound_closed(inst: Instrument, pos: dict, history: list[dict]) -> str:
    d = inst.decimals
    icon = {"rimbalzo": "✅ CHIUDI: RIMBALZO ARRIVATO", "stop": "❌ STOP DI SICUREZZA TOCCATO",
            "tempo": "⏱️ CHIUDI: SCADUTI 5 GIORNI"}[pos["exit_reason"]]
    n = len(history)
    wins = sum(1 for c in history if c["r"] > 0)
    total = sum(c["r"] for c in history)
    lines = [
        f"🔄 {icon} — {inst.name} LONG (rimbalzo)",
        f"Ingresso {f(pos['entry'], d)} → uscita {f(pos['exit'], d)} · risultato {pos['r']:+.2f}R",
    ]
    if pos["exit_reason"] != "stop":
        lines.append("Chiudi la posizione su Trading 212.")
    lines.append(f"Storico rimbalzi: {n} operazioni · vincenti {wins}/{n} · totale {total:+.1f}R")
    return "\n".join(lines)
