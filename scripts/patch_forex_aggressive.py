#!/usr/bin/env python3
"""Apply forex aggressive block patch to telegram/bot.py."""
from pathlib import Path

BOT = Path(__file__).resolve().parents[1] / "telegram" / "bot.py"
text = BOT.read_text(encoding="utf-8")

if "_format_forex_aggressive" in text:
    print("already patched")
    raise SystemExit(0)

BLOCK_LINES = [
    "",
    "# " + "=" * 60,
    "# FOREX AGGRESSIVE BLOCK (for /aggressivo212)",
    "# " + "=" * 60,
    "",
    "def _format_forex_aggressive(results) -> str:",
    "    \"\"\"Format aggressive forex desk from same scan results.\"\"\"",
    "    if not results:",
    "        return chr(10).join([\"\", \"FOREX AGGRESSIVE\", \"Nessun dato disponibile.\"]),
    "    forex_states = []",
    "    for state in results:",
    "        cat = str(getattr(getattr(state, \"commodity_obj\", None), \"category\", \"\") or \"\").lower()",
    "        if not cat:",
    "            sym = str(getattr(state, \"symbol\", \"\") or \"\").upper()",
    "            if sym in {\"EURUSD\", \"GBPUSD\", \"USDJPY\", \"USDCHF\", \"AUDUSD\", \"USDCAD\", \"NZDUSD\", \"EURJPY\"}:",
    "                cat = \"forex\"",
    "        if cat == \"forex\":",
    "            forex_states.append(state)",
    "    if not forex_states:",
    "        return chr(10).join([\"\", \"FOREX AGGRESSIVE\", \"Nessuna coppia forex nell'universo analizzato.\"]),
    "    lines = [\"\", \"FOREX AGGRESSIVE\", \"Conto separato capitale 100, probabilita >= 45, rischio 1.5%\", \"\"]",
    "    ranked = sorted(forex_states, key=lambda s: (-(float(getattr(s, \"opportunity_score\", 0) or 0)), -(float(getattr(s, \"probability\", 0) or 0)), -(float(getattr(s, \"quality\", 0) or 0))))",
    "    found = False",
    "    for index, state in enumerate(ranked[:3], 1):",
    "        direction = getattr(state, \"setup_direction\", None) or getattr(state, \"opportunity_direction\", None) or \"\"",
    "        direction = direction.upper() if direction else \"--\"",
    "        prob = float(getattr(state, \"probability\", 0) or 0)",
    "        if prob < 45 and direction == \"--\":",
    "            continue",
    "        found = True",
    "        price = getattr(state, \"price\", None)",
    "        entry = getattr(state, \"entry\", None)",
    "        stop = getattr(state, \"stop\", None)",
    "        tp1 = getattr(state, \"tp1\", None)",
    "        tp2 = getattr(state, \"tp2\", None)",
    "        tp3 = getattr(state, \"tp3\", None)",
    "        alert = getattr(state, \"opportunity_alert\", \"NONE\") or \"NONE\"",
    "        score = float(getattr(state, \"opportunity_score\", 0) or 0)",
    "        quality = float(getattr(state, \"quality\", 0) or 0)",
    "        confidence = float(getattr(state, \"confidence\", 0) or 0)",
    "        trigger = getattr(state, \"trigger_confirmed\", False)",
    "        lines.extend([
    "            (\"SCELTA PRINCIPALE\" if index == 1 else \"Alternativa %d\" % index) + \": \" + str(state.commodity) + \" -- \" + direction,
    "            \"Prezzo: %.6g\" % price if price is not None else \"Prezzo: N/D\",
    "            \"ENTRY: %.6g\" % entry if entry is not None else \"ENTRY: N/D\",
    "            \"STOP: %.6g\" % stop if stop is not None else \"STOP: N/D\",
    "            (\"TP1: %.6g | TP2: %.6g | TP3: %.6g\" % (tp1, tp2, tp3)) if tp1 is not None else \"TP: N/D\",
    "            \"Probabilita: %.0f | Quality: %.0f | Confidence: %.0f\" % (prob, quality, confidence),
    "            \"Opportunita: %s (score %.1f) | Trigger: %s\" % (alert, score, \"CONFERMATO\" if trigger else \"DA CONFERMARE\"),
    "            \"\",
    "        ])",
    "    if not found:",
    "        lines.append(\"Nessuna coppia forex sopra soglia 45.\")",
    "        lines.append(\"\")",
    "    lines.append(\"Solo coppie gia analizzate dal motore Gagarin. ETF e indici esclusi.\")",
    "    return chr(10).join(lines)",
    "",
]
BLOCK = chr(10).join(BLOCK_LINES) + chr(10)

marker = "def _command_response("
if marker not in text:
    raise SystemExit("marker missing")
text = text.replace(marker, BLOCK + marker, 1)

needle = "if command_name == \"/aggressivo212\":"
i = text.find(needle)
if i < 0:
    raise SystemExit("aggressivo212 block not found")
j = text.find("return report", i)
if j < 0:
    raise SystemExit("return report not found")
k = text.find(chr(10), j)
new = (
    "            if command_name == \"/aggressivo212\":" + chr(10)
    + "                forex_block = _format_forex_aggressive(results or [])" + chr(10)
    + "                return (" + chr(10)
    + "                    \"TRADING 212 CFD — PROFILO AGGRESSIVO\\n\"" + chr(10)
    + "                    + report" + chr(10)
    + "                    + forex_block" + chr(10)
    + "                    + \"\\n\\nQuotazioni: feed Trading 212 CFD non collegato; prezzi mostrati dal provider Gagarin. Verifica il contratto e bid/ask in app prima di operare.\"" + chr(10)
    + "                    + \"\\nPAPER ONLY — nessun ordine inviato.\"" + chr(10)
    + "                )" + chr(10)
    + "            return report" + chr(10)
)
text = text[:i] + new + text[k + 1 :]
BOT.write_text(text, encoding="utf-8")
print("PATCHED", len(text))
