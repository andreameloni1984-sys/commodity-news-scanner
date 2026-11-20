"""Trading 212 INVEST Demo reads with an explicit endpoint allowlist."""
import base64
import json
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://demo.trading212.com/api/v0"
READ_PATHS = {
    "instrumenti": "/equity/metadata/instruments",
    "saldo": "/equity/account/summary",
    "posizioni": "/equity/positions",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Demo:
    def __init__(self, key, secret):
        if not key or not secret:
            raise ValueError("Secret Trading 212 Demo mancanti")
        self.authorization = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
        self.opener = build_opener(NoRedirect())

    def read(self, resource):
        request = Request(BASE + READ_PATHS[resource], method="GET",
                          headers={"Authorization": self.authorization, "Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"Trading 212 Demo {resource}: HTTP {exc.code}") from None

    def universe(self):
        rows = self.read("instrumenti")
        if not isinstance(rows, list):
            raise ValueError("Catalogo Demo non valido")
        result = {}
        ambiguous = set()
        for row in rows:
            ticker = row.get("ticker", "")
            symbol = row.get("shortName", "")
            kind = row.get("type")
            if (kind not in ("STOCK", "ETF") or not symbol or row.get("currencyCode") != "USD"
                    or ticker != symbol + "_US_EQ"):
                continue
            if symbol in result:
                ambiguous.add(symbol)
            result[symbol] = (kind, row.get("name") or symbol, ticker)
        return {symbol: value for symbol, value in result.items() if symbol not in ambiguous}

    def check_account(self):
        balance, positions = self.read("saldo"), self.read("posizioni")
        if not isinstance(balance, dict) or not isinstance(positions, list):
            raise ValueError("Risposte account Demo non valide")
        return len(positions)
