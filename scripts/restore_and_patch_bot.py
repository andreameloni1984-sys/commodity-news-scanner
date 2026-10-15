#!/usr/bin/env python3
"""Restore telegram/bot.py from feat/gagarin-telegram-menu and add
/aggressivo212, /soft212, /prezzo212 with Trading 212 comparison.
Run by GitHub Actions workflow."""
import base64, json, os, subprocess, sys, urllib.request

OWNER, REPO, BRANCH = "andreameloni1984-sys", "commodity-news-scanner", "main"
FEAT = "feat/gagarin-telegram-menu"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("TOKEN")
if not TOKEN:
    print("NO_TOKEN"); sys.exit(1)

ADDITION = r'''
    # --------------------------------------------------------
    # AGGRESSIVE / SOFT / PREZZO212 (Trading 212 reparto)
    # --------------------------------------------------------

    if command_name in {"/aggressivo212", "/aggressive212"}:
        try:
            from soyuz_gagarin.aggressive_desk import format_aggressive_desk
            from soyuz_gagarin.trading_profiles import get_profile
            from engine.trading212 import compare_price, format_comparison, parse_bid_ask
            profile = get_profile("AGGRESSIVE")
            results = _run_analysis()
            if results is None:
                return "Nessun risultato. Riprova con /analisi."
            set_last_results(results)
            desk = format_aggressive_desk(results)
            try:
                from cloud_api import FOREX_AGGRESSIVE_PORTFOLIO
                fx = FOREX_AGGRESSIVE_PORTFOLIO.snapshot()
                fx_lines = ["", "FX AGGRESSIVE", "Capitale: " + str(round(fx.get("equity", 100), 2)), "Aperte: " + str(len(fx.get("open_positions", [])))]
                for p in fx.get("open_positions", [])[:5]:
                    fx_lines.append(str(p.get("symbol")) + " " + str(p.get("direction")) + " entry " + str(p.get("entry")))
                desk = desk + "\n" + "\n".join(fx_lines)
            except Exception:
                pass
            if argument:
                bid, ask = parse_bid_ask(argument)
                if bid is not None:
                    sym = None
                    for part in argument.replace(",", ".").split():
                        up = part.upper()
                        if up in {"WTI", "BRENT", "ORO", "ARGENTO", "SPY", "QQQ", "EURUSD", "GBPUSD"}:
                            sym = up
                            break
                    if sym:
                        gprice = None
                        for st in results:
                            if str(getattr(st, "symbol", "")).upper() == sym:
                                gprice = getattr(st, "price", None)
                                break
                        comp = compare_price(sym, gprice, bid, ask)
                        desk = desk + "\n\n" + format_comparison(comp)
                    else:
                        desk = desk + "\n\n212: incolla anche il simbolo, es. /aggressivo212 WTI 78.10 78.13"
                else:
                    desk = desk + "\n\n212: per il confronto incolla bid e ask, es. /aggressivo212 WTI 78.10 78.13"
            else:
                desk = desk + "\n\n212: per confrontare i prezzi Trading 212 incolla bid e ask dopo il comando."
            desk = desk + "\n\nProfilo: probabilita >= " + str(profile.min_probability) + ", qualita >= " + str(profile.min_quality) + ", rischio " + str(profile.risk_per_trade_pct) + "%% per operazione, max " + str(profile.max_open_positions) + " posizioni."
            return desk
        except Exception as exc:
            return "Errore reparto aggressive: " + type(exc).__name__ + ": " + str(exc)

    if command_name in {"/soft212", "/soft"}:
        try:
            from soyuz_gagarin.trading_profiles import get_profile
            profile = get_profile("SOFT")
            results = _run_analysis()
            if results is None:
                return "Nessun risultato. Riprova con /analisi."
            set_last_results(results)
            return _format_classifica(results) + "\n\nProfilo SOFT: probabilita >= " + str(profile.min_probability) + ", qualita >= " + str(profile.min_quality) + ", rischio " + str(profile.risk_per_trade_pct) + "%%."
        except Exception as exc:
            return "Errore soft: " + type(exc).__name__ + ": " + str(exc)

    if command_name == "/prezzo212":
        try:
            from engine.trading212 import compare_price, format_comparison, parse_bid_ask
            if not argument:
                return "212 PREZZI\nIncolla: simbolo bid ask\nEs: /prezzo212 WTI 78.10 78.13"
            parts = argument.split()
            sym = parts[0].upper()
            bid, ask = parse_bid_ask(" ".join(parts[1:]))
            gprice = None
            results = get_last_results()
            if results:
                for st in results:
                    if str(getattr(st, "symbol", "")).upper() == sym:
                        gprice = getattr(st, "price", None)
                        break
            if gprice is None:
                try:
                    results = _run_analysis()
                    if results:
                        set_last_results(results)
                        for st in results:
                            if str(getattr(st, "symbol", "")).upper() == sym:
                                gprice = getattr(st, "price", None)
                                break
                except Exception:
                    pass
            return format_comparison(compare_price(sym, gprice, bid, ask))
        except Exception as exc:
            return "Errore 212: " + type(exc).__name__ + ": " + str(exc)
'''

def gh(path, ref=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
    if ref: url += f"?ref={ref}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "gagarin-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

data = gh("telegram/bot.py", FEAT)
content = base64.b64decode(data["content"]).decode("utf-8")
print(f"Downloaded bot.py from {FEAT}: {len(content)} bytes, sha={data['sha'][:8]}")

needle = '        return None\n\n\n# ============================================================\n# POLLING'
if needle not in content:
    # try alternate ending
    idx = content.rfind("return None")
    print(f"Needle not found, last return None at index {idx}")
    if idx < 0:
        print("CANNOT_PATCH"); sys.exit(2)
    # insert before the last return None
    content = content[:idx] + ADDITION + "\n" + content[idx:]
else:
    content = content.replace(needle, ADDITION + "\n" + needle, 1)

print(f"Patched bot.py: {len(content)} bytes")
# sanity: must contain the new commands
for cmd in ["/aggressivo212", "/soft212", "/prezzo212", "engine.trading212", "FOREX_AGGRESSIVE_PORTFOLIO"]:
    assert cmd in content, f"missing {cmd}"
print("Sanity checks passed")

# commit via git
subprocess.run(["git", "config", "user.name", "gagarin-bot"], check=True)
subprocess.run(["git", "config", "user.email", "bot@gagarin.local"], check=True)
with open("telegram/bot.py", "w", encoding="utf-8") as f:
    f.write(content)
subprocess.run(["git", "add", "telegram/bot.py"], check=True)
r = subprocess.run(["git", "diff", "--cached", "--quiet"])
if r.returncode == 0:
    print("No changes"); sys.exit(0)
subprocess.run(["git", "commit", "-m", "fix(telegram): restore bot.py and wire /aggressivo212 Trading 212 reparto"], check=True)
subprocess.run(["git", "push"], check=True)
print("PUSH_OK")
