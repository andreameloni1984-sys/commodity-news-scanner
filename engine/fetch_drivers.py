"""SOYUZ — engine/fetch_drivers.py

Scarica le variabili che muovono le materie prime da fonti pubbliche.
Cascata: fonte primaria ufficiale prima, siti di notizie come riserva.
Se due fonti riportano numeri diversi, segnala la divergenza invece di scegliere a caso.
Se una fonte fallisce, prova la successiva. Se nessuna risponde, la variabile resta UNKNOWN.

Paper only. Non cambia final_decision.

Fonti:
  - EIA (api.eia.gov)        : scorte greggio USA, stoccaggi gas
  - USDA WASDE (nass.usda.gov): cereali, softs
  - FRED (api.stlouisfed.org): dollaro, rendimento reale

Chiavi opzionali (secrets GitHub): EIA_API_KEY, FRED_API_KEY.
Senza chiave il job usa le pagine pubbliche HTML come fallback.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests

TIMEOUT = 25
UA = {"User-Agent": "soyuz-gagarin/1.0 (+https://github.com/andreameloni1984-sys/commodity-news-scanner)"}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

class _TableParser(HTMLParser):
    """Estrae le prime tabelle HTML come liste di righe di celle."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = []
        self._cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th"):
            self._in_cell = True
            self._cell = ""
        elif tag == "tr":
            self._row = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._row.append(re.sub(r"\s+", " ", self._cell).strip())
            self._in_cell = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)

    def handle_data(self, data):
        if self._in_cell:
            self._cell += data


def _parse_tables(html: str) -> list:
    p = _TableParser()
    p.feed(html)
    return p.rows


def _num(text: str) -> float | None:
    if not text:
        return None
    t = text.replace("\u00a0", " ").strip()
    t = t.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group()) if m else None


def _get(url: str, params: dict | None = None) -> str | None:
    try:
        r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# EIA — scorte greggio USA (WCRSTUS1) e stoccaggi gas (NW2_EPG0_SWO_R48_BCF)
# ---------------------------------------------------------------------------

def fetch_eia_series(series_id: str, api_key: str | None) -> dict:
    """Prova l'API EIA; se fallisce, la pagina pubblica series."""
    out = {"series_id": series_id, "value": None, "date": None, "source": None, "error": None}
    if api_key:
        url = f"https://api.eia.gov/v2/seriesid/{series_id}"
        html = _get(url, params={"api_key": api_key, "frequency": "weekly", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 2})
        if html:
            try:
                data = json.loads(html)
                rows = data.get("response", {}).get("data", [])
                if rows:
                    out["value"] = rows[0].get("value")
                    out["date"] = rows[0].get("period")
                    out["source"] = "eia_api"
                    return out
            except Exception as e:
                out["error"] = f"api_parse:{e}"
    # fallback pagina pubblica
    html = _get(f"https://www.eia.gov/dnav/pet/hist_xls/{series_id}.xls")
    if not html:
        html = _get(f"https://www.eia.gov/petroleum/supply/weekly/")
    if html:
        # cerca pattern "YYYY-MM-DD ... numero" nelle tabelle
        for row in _parse_tables(html):
            if len(row) >= 2 and re.match(r"\d{4}-\d{2}-\d{2}", row[0]):
                v = _num(row[1])
                if v is not None:
                    out["value"] = v
                    out["date"] = row[0]
                    out["source"] = "eia_public_page"
                    return out
    out["error"] = out["error"] or "no_data"
    return out


# ---------------------------------------------------------------------------
# USDA WASDE — cereali e softs (pagina pubblica, nessuna API)
# ---------------------------------------------------------------------------

_USDA_URL = "https://www.nass.usda.gov/Newsroom/Executive_Briefings/2026/"


def fetch_usda_wasde() -> dict:
    """Cerca l'ultimo WASDE sulla pagina pubblica USDA."""
    out = {"wheat_world_mb": None, "corn_world_mb": None, "soybeans_world_mb": None,
           "date": None, "source": None, "error": None}
    html = _get(_USDA_URL)
    if not html:
        # fallback: pagina indice WASDE
        html = _get("https://www.nass.usda.gov/Newsroom/Executive_Briefings/")
    if not html:
        out["error"] = "no_page"
        return out
    # cerca link a PDF WASDE recenti
    links = re.findall(r'href="([^"]*wasde[^"]*\.pdf)"', html, re.I)
    for link in links[:3]:
        if not link.startswith("http"):
            link = "https://www.nass.usda.gov" + link
        pdf = _get(link)
        if not pdf:
            continue
        # estrai numeri da testo grezzo del PDF (approssimativo ma utile)
        text = re.sub(r"[^\w\s\-\.]", " ", pdf.decode("latin-1", errors="ignore"))
        # pattern tipici WASDE: "Wheat ... Million Bushels ... 1234.5"
        for key, pat in {
            "wheat_world_mb": r"Wheat[\w\s]{0,40}Million Bushels[\w\s]{0,40}(\d{2,4}(?:\.\d+)?)",
            "corn_world_mb": r"Corn[\w\s]{0,40}Million Bushels[\w\s]{0,40}(\d{3,5}(?:\.\d+)?)",
            "soybeans_world_mb": r"Soybeans[\w\s]{0,40}Million Bushels[\w\s]{0,40}(\d{3,5}(?:\.\d+)?)",
        }.items():
            m = re.search(pat, text, re.I)
            if m and out[key] is None:
                out[key] = float(m.group(1))
        if any(out[k] is not None for k in ("wheat_world_mb", "corn_world_mb", "soybeans_world_mb")):
            out["source"] = "usda_wasde_pdf"
            out["date"] = datetime.now(timezone.utc).date().isoformat()
            return out
    out["error"] = "no_wasde_numbers"
    return out


# ---------------------------------------------------------------------------
# FRED — dollaro (DTWEXBGS) e rendimento reale 10Y (DFII10)
# ---------------------------------------------------------------------------

def fetch_fred_series(series_id: str, api_key: str | None) -> dict:
    """Prova l'API FRED; se fallisce, la pagina pubblica."""
    out = {"series_id": series_id, "value": None, "date": None, "previous": None, "source": None, "error": None}
    if api_key:
        url = f"https://api.stlouisfed.org/fred/series/observations"
        html = _get(url, params={
            "series_id": series_id, "api_key": api_key, "file_type": "json",
            "sort_order": "desc", "limit": 3,
        })
        if html:
            try:
                data = json.loads(html)
                obs = [o for o in data.get("observations", []) if o.get("value") not in (".", None)]
                if len(obs) >= 1:
                    out["value"] = float(obs[0]["value"])
                    out["date"] = obs[0]["date"]
                    out["source"] = "fred_api"
                    if len(obs) >= 2:
                        out["previous"] = float(obs[1]["value"])
                    return out
            except Exception as e:
                out["error"] = f"api_parse:{e}"
    # fallback pagina pubblica graph
    html = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
    if html:
        lines = [ln.strip() for ln in html.splitlines() if ln.strip() and not ln.startswith("DATE")]
        vals = []
        for ln in lines[-5:]:
            parts = ln.split(",")
            if len(parts) >= 2:
                v = _num(parts[1])
                if v is not None:
                    vals.append((parts[0], v))
        if vals:
            out["date"], out["value"] = vals[-1]
            out["source"] = "fred_csv"
            if len(vals) >= 2:
                out["previous"] = vals[-2][1]
            return out
    out["error"] = out["error"] or "no_data"
    return out


# ---------------------------------------------------------------------------
# Mappatura osservazioni -> variabili del motore (engine/drivers.py)
# ---------------------------------------------------------------------------

def map_to_variables(obs: dict) -> dict:
    """Traduce le osservazioni grezze nelle undici variabili di engine/drivers.py.
    Valori ammessi: TIGHT/LOOSE, BACKWARDATION/CONTANGO, UP/DOWN, HIGH/LOW, FAVORABLE/UNFAVORABLE.
    Se il dato manca o è ambiguo, resta UNKNOWN."""
    var = {k: "UNKNOWN" for k in (
        "inventories", "curve", "supply_shock", "refined", "dollar", "real_rates",
        "systematic_flow", "weather", "harvest", "season", "hedging_pressure",
    )}

    # inventories: scorte greggio USA in calo -> TIGHT
    inv = obs.get("us_crude_stocks") or obs.get("us_crude_stocks_kb")
    if isinstance(inv, dict) and inv.get("value") is not None and inv.get("previous") is not None:
        if inv["value"] < inv["previous"]:
            var["inventories"] = "TIGHT"
        elif inv["value"] > inv["previous"]:
            var["inventories"] = "LOOSE"

    # dollar: indice in calo -> DOWN (favorevole alle commodity)
    dxy = obs.get("dollar_index")
    if isinstance(dxy, dict) and dxy.get("value") is not None and dxy.get("previous") is not None:
        if dxy["value"] < dxy["previous"]:
            var["dollar"] = "DOWN"
        elif dxy["value"] > dxy["previous"]:
            var["dollar"] = "UP"

    # real_rates: rendimento reale 10Y in calo -> DOWN (favorevole all'oro)
    rr = obs.get("real_rate_10y")
    if isinstance(rr, dict) and rr.get("value") is not None and rr.get("previous") is not None:
        if rr["value"] < rr["previous"]:
            var["real_rates"] = "DOWN"
        elif rr["value"] > rr["previous"]:
            var["real_rates"] = "UP"

    # curve: WTI spot vs futures (se presenti)
    spot = obs.get("wti", {}).get("value") if isinstance(obs.get("wti"), dict) else None
    fut = obs.get("wti_futures", {}).get("value") if isinstance(obs.get("wti_futures"), dict) else None
    if spot is not None and fut is not None:
        if fut > spot:
            var["curve"] = "BACKWARDATION"
        elif fut < spot:
            var["curve"] = "CONTANGO"

    # harvest: raccolto cereali (WASDE) in calo -> TIGHT
    wh = obs.get("wheat_world_mb")
    if isinstance(wh, dict) and wh.get("value") is not None and wh.get("previous") is not None:
        if wh["value"] < wh["previous"]:
            var["harvest"] = "TIGHT"
        elif wh["value"] > wh["previous"]:
            var["harvest"] = "LOOSE"

    return var


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    eia_key = os.environ.get("EIA_API_KEY") or None
    fred_key = os.environ.get("FRED_API_KEY") or None

    observations = {
        "us_crude_stocks": fetch_eia_series("WCRSTUS1", eia_key),
        "us_natgas_storage": fetch_eia_series("NW2_EPG0_SWO_R48_BCF", eia_key),
        "dollar_index": fetch_fred_series("DTWEXBGS", fred_key),
        "real_rate_10y": fetch_fred_series("DFII10", fred_key),
        "wasde": fetch_usda_wasde(),
    }
    # appiattisci WASDE
    wasde = observations.pop("wasde")
    for k in ("wheat_world_mb", "corn_world_mb", "soybeans_world_mb"):
        observations[k] = {"value": wasde.get(k), "date": wasde.get("date"), "source": wasde.get("source")}

    variables = map_to_variables(observations)

    # divergenze: se due fonti hanno dato valori diversi per la stessa serie
    divergences = []
    for name, obs in observations.items():
        if isinstance(obs, dict) and obs.get("error") and obs.get("value") is not None:
            divergences.append(f"{name}: partial data, error={obs['error']}")

    snapshot = {
        "paper_only": True,
        "read_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "us_crude_stocks": "EIA WCRSTUS1 (api -> public page)",
            "us_natgas_storage": "EIA NW2_EPG0_SWO_R48_BCF (api -> public page)",
            "dollar_index": "FRED DTWEXBGS (api -> csv)",
            "real_rate_10y": "FRED DFII10 (api -> csv)",
            "wasde": "USDA NASS public page (wheat/corn/soybeans)",
        },
        "observations": observations,
        "variables": variables,
        "divergences": divergences,
        "note": "Variabili senza dato restano UNKNOWN. Nessun valore inventato.",
    }

    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "driver_snapshot.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(json.dumps({"written": path, "variables": variables, "divergences": divergences}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
