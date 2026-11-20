"""Official US macro releases and timestamped, like-for-like expectations."""
from datetime import datetime
from html import unescape
from math import isfinite
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BLS_RELEASES = {
    "BLS CPI": "https://www.bls.gov/news.release/cpi.nr0.htm",
    "BLS Employment Situation": "https://www.bls.gov/news.release/empsit.nr0.htm",
}
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
RATE = r"\d+(?:\.\d+)?"
NUMBER = r"[+−-]?\d[\d,]*(?:\.\d+)?"


def number(value):
    return float(value.replace(",", "").replace("−", "-"))


def reading(series, period, unit, actual, revisions=()):
    return {"series": series, "period": period, "unit": unit,
            "actual": actual, "revisions": list(revisions)}


def month_period(text, year):
    return datetime.strptime(f"{text.title()} {year}", "%B %Y").strftime("%Y-%m")


def bls_release(data, *, cpi):
    text = " ".join(unescape(re.sub(r"<[^>]*>", " ", data.decode(errors="replace"))).split())
    stamp = re.search(r"embargoed until\s+(?:USDL-\d+-\d+\s+)?(\d+:\d+ [ap]\.m\.)\s*\(ET\)\s*\w+,\s*(" + MONTH + r" \d{1,2}, \d{4})", text, re.I)
    heading = re.search(r"(?:CONSUMER PRICE INDEX|THE EMPLOYMENT SITUATION)\s*[-–—]\s*(" + MONTH + r") (\d{4})", text, re.I)
    if not stamp or not heading:
        raise ValueError("Periodo o orario ufficiale BLS assente")
    published = datetime.strptime(stamp[1].replace(".", "").upper() + " " + stamp[2], "%I:%M %p %B %d, %Y")
    published = published.replace(tzinfo=ZoneInfo("America/New_York"))
    period = month_period(*heading.groups())
    readings = []
    if cpi:
        match = re.search(r"CPI-U\)\s+(increased|rose|decreased|fell|declined)\s+(" + RATE + r") percent on a seasonally adjusted basis", text, re.I)
        unchanged = re.search(r"CPI-U\)\s+(?:was unchanged|was flat) on a seasonally adjusted basis", text, re.I)
        if match or unchanged:
            actual = (number(match[2]) * (-1 if match[1].lower() in {"decreased", "fell", "declined"} else 1)) if match else 0.0
            readings.append(reading("CPI", period, "pct_mom_sa", actual))
    else:
        payroll = re.search(r"Total nonfarm payroll employment\s+(rose|increased|fell|decreased|declined) by (" + NUMBER + r") in", text, re.I)
        jobless = re.search(r"the unemployment rate\s+[^.]{0,60}?\b(?:at|to) (" + RATE + r") percent", text, re.I)
        if payroll:
            sign = -1 if payroll[1].lower() in {"fell", "decreased", "declined"} else 1
            revisions = []
            sentence = re.search(r"The change in total nonfarm payroll employment for (.*?)(?:\.\s|$)", text, re.I)
            if sentence:
                for month, old, new in re.findall(r"\b(" + MONTH + r")\s+was revised\b.{0,42}?\bfrom (" + NUMBER + r")\s+to (" + NUMBER + r")", sentence[1], re.I):
                    revised_period = month_period(month, heading[2])
                    if revised_period >= period:
                        revised_period = month_period(month, int(heading[2]) - 1)
                    revisions.append({"period": revised_period, "previous": number(old), "revised": number(new)})
            readings.append(reading("NFP", period, "jobs", sign * number(payroll[2]), revisions))
        if jobless:
            readings.append(reading("UNEMPLOYMENT", period, "pct_sa", number(jobless[1])))
    if not readings:
        raise ValueError("Valore ufficiale BLS non riconosciuto")
    return published, readings


def gdp_reading(title, summary):
    heading = re.search(r"\bGDP\s*\(([^)]+)\),\s*([1-4])(?:st|nd|rd|th) Quarter (\d{4})", title, re.I)
    actual = re.search(r"Real gross domestic product \(GDP\)\s+(increased|decreased) at an annual rate of (" + RATE + r") percent", summary, re.I)
    if not heading or not actual:
        return None
    period = f"{heading[3]}-Q{heading[2]}"
    value = number(actual[2]) * (-1 if actual[1].lower() == "decreased" else 1)
    change = re.search(r"(?:the increase in (?:real )?GDP|real GDP|the headline GDP estimate) (?:was |has been )?revised\s+(up|down)(?:ward)?\s+(?:by\s+)?(" + RATE + r") percentage point", summary, re.I)
    revisions = []
    if change and re.search(r"second estimate|third estimate|updated estimate", heading[1], re.I):
        delta = number(change[2]) * (-1 if change[1].lower() == "down" else 1)
        revisions.append({"period": period, "previous": round(value - delta, 6), "revised": value})
    result = reading("GDP", period, "pct_qoq_annualized", value, revisions)
    result["edition"] = heading[1].lower()
    return result


def rate_readings(data, published):
    text = " ".join(unescape(re.sub(r"<[^>]*>", " ", data.decode(errors="replace"))).split())
    fraction = r"\d+(?:[- ]\d+/\d+|\.\d+)?"
    match = re.search(r"target range for the federal funds rate\s+(?:at|to)\s+(" + fraction + r")\s+to\s+(" + fraction + r")\s+percent", text, re.I)
    if not match:
        raise ValueError("Range ufficiale FOMC non riconosciuto")
    values = []
    for bound in match.groups():
        whole, _, part = bound.replace("-", " ").partition(" ")
        numerator, _, denominator = part.partition("/")
        values.append(number(whole) + (number(numerator) / number(denominator) if part else 0))
    if not 0 <= values[0] < values[1] <= 30:
        raise ValueError("Range FOMC non valido")
    period = published.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    return [reading("FED_TARGET_LOWER", period, "pct", values[0]),
            reading("FED_TARGET_UPPER", period, "pct", values[1])]


def compare(data, published, expectations):
    expected = None
    for row in expectations:
        if not isinstance(row, dict) or any(row.get(key) != data.get(key) for key in ("series", "period", "unit", "edition")):
            continue
        try:
            as_of = datetime.fromisoformat(row["as_of"])
            source = urlsplit(row["source"])
            value = row["value"]
            if (as_of.utcoffset() is None or not as_of < published or source.scheme != "https"
                    or not source.hostname or type(value) not in (int, float) or not isfinite(value)):
                continue
            if expected is None or as_of > datetime.fromisoformat(expected["as_of"]):
                expected = {"value": value, "as_of": row["as_of"], "source": row["source"]}
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    data = {**data, "expected": expected, "surprise": None, "impact": "attesa comparabile non disponibile"}
    if expected is not None:
        surprise = round(data["actual"] - expected["value"], 6)
        data.update(surprise=surprise, impact="in linea" if surprise == 0 else
                    "dato superiore alle attese" if surprise > 0 else "dato inferiore alle attese")
    data["revision_deltas"] = [
        {**revision, "delta": round(revision["revised"] - revision["previous"], 6)}
        for revision in data["revisions"]
    ]
    data["channel"] = {
        "CPI": "inflazione", "GDP": "crescita", "NFP": "occupazione",
        "UNEMPLOYMENT": "disoccupazione", "FED_TARGET_LOWER": "politica monetaria",
        "FED_TARGET_UPPER": "politica monetaria",
    }.get(data["series"])
    data["direction"] = None
    return data
