#!/usr/bin/env python3
"""Restore telegram/bot.py from feat/gagarin-telegram-menu and add
/aggressivo212, /soft212, /prezzo212 with Trading 212 comparison.
Commits via GitHub Contents API."""
import base64, json, os, sys, urllib.request, urllib.error

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

def api(method, path, data=None, ref=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    if ref and "?" not in url:
        url += f"?ref={ref}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "gagarin-bot",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"API {method} {path} failed: {e.code} {e.read().decode()[:500]}")
        raise

# Download real bot.py from feat branch
feat = api("GET", "contents/telegram/bot.py", ref=FEAT)
content = base64.b64decode(feat["content"]).decode("utf-8")
print(f"Downloaded bot.py from {FEAT}: {len(content)} bytes, sha={feat['sha'][:8]}")

# Insert the addition before the last return None
idx = content.rfind("return None")
if idx < 0:
    print("CANNOT_PATCH"); sys.exit(2)
content = content[:idx] + ADDITION + "\n" + content[idx:]
print(f"Patched bot.py: {len(content)} bytes")

for cmd in ["/aggressivo212", "/soft212", "/prezzo212", "engine.trading212", "FOREX_AGGRESSIVE_PORTFOLIO"]:
    assert cmd in content, f"missing {cmd}"
print("Sanity checks passed")

# Get current SHA of bot.py on main (for the update)
try:
    current = api("GET", "contents/telegram/bot.py", ref=BRANCH)
    current_sha = current["sha"]
    print(f"Current bot.py on {BRANCH}: sha={current_sha[:8]}, size={current.get('size')}")
except Exception:
    current_sha = None
    print("bot.py does not exist on main, will create")

# Commit via Contents API
payload = {
    "message": "fix(telegram): restore bot.py and wire /aggressivo212 Trading 212 reparto",
    "content": base64.b64encode(content.encode("utf-8")).decode(),
    "branch": BRANCH,
}
if current_sha:
    payload["sha"] = current_sha

result = api("PUT", "contents/telegram/bot.py", payload)
print(f"COMMIT_OK sha={result.get('commit', {}).get('sha', '?')[:8]}")
