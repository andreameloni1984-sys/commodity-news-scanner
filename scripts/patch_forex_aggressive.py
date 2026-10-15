#!/usr/bin/env python3
from pathlib import Path

BOT = Path(__file__).resolve().parents[1] / "telegram" / "bot.py"
t = BOT.read_text(encoding="utf-8")

if "_format_forex_aggressive" in t:
    print("already patched")
    raise SystemExit(0)

NL = chr(10)
DQ = chr(34)

lines = []
lines.append(NL)
lines.append("# " + "=" * 60)
lines.append("# FOREX AGGRESSIVE BLOCK (for /aggressivo212)")
lines.append("# " + "=" * 60)
lines.append(NL)
lines.append("def _format_forex_aggressive(results) -> str:")
lines.append("    if not results:")
lines.append("        return NL.join([NL, "FOREX AGGRESSIVE", "Nessun dato disponibile."])")
lines.append("    forex_states = []")
lines.append("    for state in results:")
lines.append("        cat = str(getattr(getattr(state, "commodity_obj", None), "category", "") or "").lower()")
lines.append("        if not cat:")
lines.append("            sym = str(getattr(state, "symbol", "") or "").upper()")
lines.append("            if sym in {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURJPY"}:")
lines.append("                cat = "forex"")
lines.append("        if cat == "forex":")
lines.append("            forex_states.append(state)")
lines.append("    if not forex_states:")
lines.append("        return NL.join([NL, "FOREX AGGRESSIVE", "Nessuna coppia forex nell'universo analizzato."])")
lines.append("    out = [NL, "FOREX AGGRESSIVE", "Conto separato capitale 100, probabilita >= 45, rischio 1.5%", NL]")
lines.append("    ranked = sorted(forex_states, key=lambda s: (-(float(getattr(s, "opportunity_score", 0) or 0)), -(float(getattr(s, "probability", 0) or 0)), -(float(getattr(s, "quality", 0) or 0))))")
lines.append("    found = False")
lines.append("    for index, state in enumerate(ranked[:3], 1):")
lines.append("        direction = getattr(state, "setup_direction", None) or getattr(state, "opportunity_direction", None) or "")")
lines.append("        direction = direction.upper() if direction else "--"")
lines.append("        prob = float(getattr(state, "probability", 0) or 0)")
lines.append("        if prob < 45 and direction == "--":")
lines.append("            continue")
lines.append("        found = True")
lines.append("        price = getattr(state, "price", None)")
lines.append("        entry = getattr(state, "entry", None)")
lines.append("        stop = getattr(state, "stop", None)")
lines.append("        tp1 = getattr(state, "tp1", None)")
lines.append("        tp2 = getattr(state, "tp2", None)")
lines.append("        tp3 = getattr(state, "tp3", None)")
lines.append("        alert = getattr(state, "opportunity_alert", "NONE") or "NONE"")
lines.append("        score = float(getattr(state, "opportunity_score", 0) or 0)")
lines.append("        quality = float(getattr(state, "quality", 0) or 0)")
lines.append("        confidence = float(getattr(state, "confidence", 0) or 0)")
lines.append("        trigger = getattr(state, "trigger_confirmed", False)")
lines.append("        title = "SCELTA PRINCIPALE" if index == 1 else "Alternativa %d" % index")
lines.append("        out.append(title + ": " + str(state.commodity) + " -- " + direction)")
lines.append("        out.append("Prezzo: %.6g" % price if price is not None else "Prezzo: N/D")")
lines.append("        out.append("ENTRY: %.6g" % entry if entry is not None else "ENTRY: N/D")")
lines.append("        out.append("STOP: %.6g" % stop if stop is not None else "STOP: N/D")")
lines.append("        if tp1 is not None:")
lines.append("            out.append("TP1: %.6g | TP2: %.6g | TP3: %.6g" % (tp1, tp2, tp3))")
lines.append("        else:")
lines.append("            out.append("TP: N/D")")
lines.append("        out.append("Probabilita: %.0f | Quality: %.0f | Confidence: %.0f" % (prob, quality, confidence))")
lines.append("        out.append("Opportunita: %s (score %.1f) | Trigger: %s" % (alert, score, "CONFERMATO" if trigger else "DA CONFERMARE"))")
lines.append("        out.append(NL)")
lines.append("    if not found:")
lines.append("        out.append("Nessuna coppia forex sopra soglia 45.")")
lines.append("        out.append(NL)")
lines.append("    out.append("Solo coppie gia analizzate dal motore Gagarin. ETF e indici esclusi.")")
lines.append("    return NL.join(out)")
lines.append(NL)

BLOCK = NL.join(lines) + NL
marker = "def _command_response("
if marker not in t:
    raise SystemExit("marker missing")
t = t.replace(marker, BLOCK + marker, 1)

needle = 'if command_name == "/aggressivo212":'
i = t.find(needle)
if i < 0:
    raise SystemExit("aggressivo212 block not found")
j = t.find("return report", i)
if j < 0:
    raise SystemExit("return report not found")
k = t.find(NL, j)
new = (
    '            if command_name == "/aggressivo212":' + NL
    + '                forex_block = _format_forex_aggressive(results or [])' + NL
    + '                return (' + NL
    + '                    "TRADING 212 CFD - PROFILO AGGRESSIVO' + NL + '"' + NL
    + '                    + report' + NL
    + '                    + forex_block' + NL
    + '                    + NL + NL + "Quotazioni: feed Trading 212 CFD non collegato; prezzi mostrati dal provider Gagarin. Verifica il contratto e bid/ask in app prima di operare."' + NL
    + '                    + NL + "PAPER ONLY - nessun ordine inviato."' + NL
    + '                )' + NL
    + '            return report' + NL
)
t = t[:i] + new + t[k+1:]

BOT.write_text(t, encoding="utf-8")
print("PATCHED", len(t))
