"""Testi dei messaggi Telegram (in italiano, testo semplice)."""
from __future__ import annotations

from .instruments import Instrument

FOOTER = "Segnale automatico, non è una consulenza finanziaria. Ordine da inserire a mano su Trading 212."


FOOTER_CRYPTO = ("🔬 IN OSSERVAZIONE: misurata a parte nel pagellino.\n"
                 "Ordine da inserire a mano su Trading 212.")


def f(x: float, d: int) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Sotto questa quantità Trading 212 potrebbe non accettare l'ordine (il minimo varia per strumento).
SMALL_UNITS = 0.1


# Leva massima dei CFD per i clienti al dettaglio in Europa (ESMA): margine = valore / leva
LEVERAGE = {"oro": 20, "wti": 10, "sp500": 20, "nasdaq": 20, "eurusd": 30}


def sizing_lines(pos: dict) -> list[str]:
    if not pos.get("risk_eur"):
        return ["Rischio: imposta ACCOUNT_SIZE per avere la dimensione della posizione calcolata."]
    units, risk = pos["units"], pos["risk_eur"]
    lines = []
    notional = pos.get("notional_eur")
    if notional:
        margin = notional / LEVERAGE.get(pos.get("key", ""), 20)
        lines.append(f"💶 Quanto investi: posizione da circa {f(notional, 2)} € "
                     f"(Trading 212 blocca circa {f(margin, 2)} € di margine)")
    lines.append(f"❌ Se va male (stop): perdi circa {f(risk, 2)} € ({pos['risk_pct']:g}% del conto)")
    if pos.get("target_dist") and pos.get("stop_dist"):
        lines.append(f"✅ Se va bene (target): guadagni circa {f(risk * pos['target_dist'] / pos['stop_dist'], 2)} €")
    lines.append(f"🔢 Quantità da inserire su Trading 212: {f(units, 4)}")
    unit_risk = pos.get("unit_risk_eur")
    if unit_risk and units < SMALL_UNITS:
        lines.append(
            f"⚠️ Quantità molto piccola: se Trading 212 non la accetta, il rischio sale. "
            f"Ogni 0,01 unità perde circa {f(unit_risk / 100, 2)} € allo stop: "
            f"con la quantità minima ammessa, rischio = quantità × {f(unit_risk, 2)} €.")
    return lines


def _take_profit_lines(pos: dict, d: int) -> list[str]:
    edge = "minimo" if pos["direction"] == "SHORT" else "massimo"
    gain = lambda dist: (f" → guadagni circa {f(pos['risk_eur'] * dist / pos['stop_dist'], 2)} €"
                         if pos.get("risk_eur") and pos.get("stop_dist") else "")
    if pos.get("target1"):
        tp1 = (f"🎯 Take profit 1 (prudente, {edge} degli ultimi 20 giorni): {f(pos['target1'], d)}  "
               f"(distanza {f(pos['target1_dist'], d)}){gain(pos['target1_dist'])}")
    else:
        tp1 = (f"🎯 Take profit 1 (prudente): nessun {edge} recente oltre il prezzo, "
               "il mercato l'ha appena superato — usa il take profit 2")
    return [tp1,
            f"🚀 Take profit 2 (del bot, 2 ATR): {f(pos['target'], d)}  "
            f"(distanza {f(pos['target_dist'], d)}){gain(pos['target_dist'])}",
            "Scegli tu: il 1 è più vicino e si tocca più spesso, il 2 è quello che segue il bot."]


def new_signal(inst: Instrument, pos: dict) -> str:
    d = inst.decimals
    arrow = "🟢 LONG (compra)" if pos["direction"] == "LONG" else "🔴 SHORT (vendi)"
    lines = [
        f"🚨 NUOVO SEGNALE CFD — {inst.name}",
        f"{arrow} · CFD Trading 212: {inst.t212}",
        "",
        f"Ingresso: {f(pos['entry'], d)}",
        f"Stop loss: {f(pos['stop'], d)}  (distanza {f(pos['stop_dist'], d)})",
        *_take_profit_lines(pos, d),
        "Durata massima 5 giorni di borsa",
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


def target1_hit(inst: Instrument, pos: dict) -> str:
    d = inst.decimals
    gain = (f" con circa +{f(pos['risk_eur'] * pos['target1_dist'] / pos['stop_dist'], 2)} €"
            if pos.get("risk_eur") and pos.get("stop_dist") else "")
    return "\n".join([
        f"🎯 TAKE PROFIT 1 RAGGIUNTO — {inst.name} {pos['direction']}",
        f"Il prezzo ha toccato {f(pos['target1'], d)} (minimo/massimo dei 20 giorni).",
        f"Se l'avevi impostato come take profit, la posizione si è chiusa{gain}.",
        f"Il bot continua verso il take profit 2 ({f(pos['target'], d)}) con lo stop a {f(pos['stop'], d)}.",
        "Solo informativo: le regole non cambiano.",
    ])


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
    lines += ["", "Il bot controlla i mercati ogni 15 minuti e scrive quando c'è un segnale, una chiusura o un movimento eccezionale."]
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
        *([f"Take profit indicativo: {f(pos['target'], d)}  (distanza {f(pos['target_dist'], d)}, "
           "media a 5 giorni: di solito il rimbalzo arriva lì)"] if pos.get("target") else []),
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


def big_move(inst: Instrument, move: float, prev_close: float, price: float, ratio: float, open_dir: str | None) -> str:
    d = inst.decimals
    arrow = "📈" if move > 0 else "📉"
    lines = [
        f"🌋 MOVIMENTO FORTE — {inst.name} {arrow} {'+' if move > 0 else ''}{f(move / prev_close * 100, 1)}% oggi",
        f"Da {f(prev_close, d)} a {f(price, d)}: circa {f(ratio, 1)} volte un giorno normale.",
        "Nessun segnale da seguire: è solo un'informazione.",
    ]
    if open_dir:
        against = (move > 0) != (open_dir == "LONG")
        lines.append(f"Hai un {open_dir} aperto su questo strumento: "
                     + ("il movimento è CONTRO di te, controlla lo stop." if against else "il movimento è a tuo favore."))
    else:
        lines.append("Se hai posizioni aperte su questo strumento, controlla gli stop.")
    return "\n".join(lines)


def _pct(x: float) -> str:
    return f"{x:.1%}".replace(".", ",")


def crypto_signal(coin, pos: dict) -> str:
    d = coin.decimals
    e = pos["entry"]
    long_ = pos["direction"] == "LONG"
    up, down = ("+", "−") if long_ else ("−", "+")
    edge = "massimo" if long_ else "minimo"
    if long_:
        lines = [f"🪙 SEGNALE CRIPTO — {coin.name} (sezione Cripto di Trading 212, solo acquisto)",
                 f"🟢 COMPRA · {coin.t212}", ""]
        if pos.get("amount_eur"):
            lines.append(f"💶 Compra circa {f(pos['amount_eur'], 2)} € di {coin.name}"
                         + (" (95% del conto: il massimo ammesso)" if pos.get("capped") else ""))
    else:
        lines = [f"🪙 SEGNALE CRIPTO CFD — {coin.name} (sezione CFD di Trading 212)",
                 f"🔴 SHORT (vendi) · CFD {coin.t212} · leva 1:2", ""]
        if pos.get("notional_eur"):
            lines.append(f"💶 Posizione da circa {f(pos['notional_eur'], 2)} € "
                         f"(Trading 212 blocca circa {f(pos['margin_eur'], 2)} € di margine)")
    lines += [f"Prezzo d'ingresso: {f(e, d)} $",
              f"🛑 Stop: {f(pos['stop'], d)} $ ({down}{_pct(pos['stop_dist'] / e)})"]
    gain = lambda dist: (f" → guadagni circa {f(pos['risk_eur'] * dist / pos['stop_dist'], 2)} €"
                         if pos.get("risk_eur") else "")
    if pos.get("target1"):
        lines.append(f"🎯 Take profit 1 (prudente, {edge} dei 20 giorni): {f(pos['target1'], d)} $ "
                     f"({up}{_pct(pos['target1_dist'] / e)}){gain(pos['target1_dist'])}")
    lines.append(f"🚀 Take profit 2 (del bot, 2 ATR): {f(pos['target'], d)} $ "
                 f"({up}{_pct(pos['target_dist'] / e)}){gain(pos['target_dist'])}")
    if pos.get("risk_eur"):
        lines.append(f"❌ Se scatta lo stop perdi circa {f(pos['risk_eur'], 2)} € ({pos['risk_pct']:g}% del conto)")
    else:
        lines.append("Imposta ACCOUNT_SIZE per avere la cifra in euro.")
    if not long_ and pos.get("units"):
        lines.append(f"🔢 Quantità da inserire: {f(pos['units'], 4)}")
    lines += ["⏱️ Durata massima 5 giorni (anche nel weekend: le cripto non chiudono mai)", "",
              "Perché: " + "; ".join(pos["reasons"]), ""]
    if long_:
        lines.append("Se lo stop non si può impostare su Trading 212, quando lo tocca ti scrivo: vendi subito a mano.")
    else:
        lines.append("Inserisci stop e take profit sul CFD. Costo per notte: controlla «Informazioni» su Trading 212.")
    lines += ["Se il prezzo è diverso, mantieni le stesse percentuali di stop e take profit.", FOOTER_CRYPTO]
    return "\n".join(lines)


def crypto_target1(coin, pos: dict) -> str:
    gain = (f" con circa +{f(pos['risk_eur'] * pos['target1_dist'] / pos['stop_dist'], 2)} €"
            if pos.get("risk_eur") else "")
    return "\n".join([
        f"🎯 CRIPTO — TAKE PROFIT 1 RAGGIUNTO — {coin.name} {pos['direction']}",
        f"Il prezzo ha toccato {f(pos['target1'], coin.decimals)} $.",
        (f"Se l'avevi scelto come obiettivo, vendi ora{gain}." if pos["direction"] == "LONG"
         else f"Se l'avevi impostato sul CFD, la posizione si è chiusa{gain}."),
        f"Il bot continua verso il take profit 2 ({f(pos['target'], coin.decimals)} $), "
        f"stop a {f(pos['stop'], coin.decimals)} $.",
    ])


def crypto_closed(coin, pos: dict, history: list[dict]) -> str:
    long_ = pos.get("direction", "LONG") == "LONG"
    head = {"target": "✅ TAKE PROFIT 2 RAGGIUNTO",
            "stop": "❌ STOP TOCCATO: VENDI SUBITO se non è già venduto" if long_ else "❌ STOP TOCCATO",
            "tempo": "⏱️ VENDI: SCADUTI 5 GIORNI" if long_ else "⏱️ CHIUDI IL CFD: SCADUTI 5 GIORNI"}[pos["exit_reason"]]
    total = sum(c["r"] for c in history)
    wins = sum(1 for c in history if c["r"] > 0)
    lines = [f"🪙 {head} — {coin.name} {pos.get('direction', 'LONG')}",
             f"Ingresso {f(pos['entry'], coin.decimals)} $ → uscita {f(pos['exit'], coin.decimals)} $ "
             f"· {pos['r']:+.2f}R".replace(".", ",")]
    if pos.get("risk_eur"):
        lines.append(f"Risultato circa {pos['r'] * pos['risk_eur']:+.2f} €".replace(".", ","))
    lines.append(f"Storico cripto: {len(history)} operazioni · vincenti {wins} · totale {total:+.1f}R".replace(".", ","))
    return "\n".join(lines)
