from datetime import datetime, timedelta, timezone

from cfdbot import briefing

from .cfd_helpers import bars_from

# Martedì 24/11/2026 08:40 ora di Roma
NOW = datetime(2026, 11, 24, 7, 40, tzinfo=timezone.utc)
CPI = {"title": "CPI m/m", "country": "USD", "date": "2026-11-24T08:30:00-05:00", "impact": "High",
       "forecast": "0.3%", "previous": "0.2%"}
OIL = {"title": "Crude Oil Inventories", "country": "USD", "date": "2026-11-24T10:30:00-05:00", "impact": "Medium",
       "forecast": "-1.2M", "previous": "2.1M"}
NOISE = [{"title": "Low thing", "country": "USD", "date": "2026-11-24T09:00:00-05:00", "impact": "Low"},
         {"title": "ECB talk", "country": "EUR", "date": "2026-11-24T09:00:00-05:00", "impact": "High"}]


def fetcher(symbol, range_="2y", interval="1d"):
    return bars_from([100 * 1.002 ** i for i in range(300)])


CTX = {"trump": [{"title": "Trump announces tariffs", "bias": [{"instrument": "GOLD", "bias": "LONG_BIAS"}]}]}


def test_morning_brief_once_with_events_and_trump():
    sent = []
    st = briefing.run(NOW, fetcher=fetcher, calendar_fetcher=lambda: [CPI, OIL] + NOISE,
                      context_fetcher=lambda: CTX, send=lambda t: sent.append(t) or True, st={})
    brief = next(t for t in sent if "BOLLETTINO" in t)
    assert "martedì 24/11" in brief
    assert "14:30 CPI m/m" in brief and "16:30 Crude Oil Inventories" in brief
    assert "Low thing" not in brief and "ECB" not in brief
    assert "• Trump announces tariffs\n   → Oro ⬆️" in brief
    assert "Zone pericolose: 14:15–14:45, 16:15–16:45" in brief
    sent.clear()
    briefing.run(NOW + timedelta(minutes=15), fetcher=fetcher, calendar_fetcher=lambda: [CPI],
                 context_fetcher=lambda: CTX, send=lambda t: sent.append(t) or True, st=st)
    assert not any("BOLLETTINO" in t for t in sent)


def test_danger_alert_once_before_event():
    st = {"brief_date": "2026-11-24"}
    sent = []
    before = datetime(2026, 11, 24, 13, 0, tzinfo=timezone.utc)  # 14:00 a Roma, CPI alle 14:30
    briefing.run(before, fetcher=fetcher, calendar_fetcher=lambda: [CPI, OIL], send=lambda t: sent.append(t) or True, st=st)
    assert len(sent) == 1 and "ZONA PERICOLOSA" in sent[0] and "tra 30 minuti" in sent[0]
    assert "Oro" in sent[0] and "14:15 alle 14:45" in sent[0]
    briefing.run(before + timedelta(minutes=15), fetcher=fetcher, calendar_fetcher=lambda: [CPI, OIL],
                 send=lambda t: sent.append(t) or True, st=st)
    assert len(sent) == 1


def test_oil_data_affects_only_oil_and_weekend_is_quiet():
    assert briefing.affected("Crude Oil Inventories") == ("wti",)
    sent = []
    saturday = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)
    briefing.run(saturday, fetcher=fetcher, calendar_fetcher=lambda: [CPI], send=lambda t: sent.append(t) or True, st={})
    assert sent == []


def test_trump_lines_skip_empty_posts_tag_topics_and_cut_on_sentence():
    now = datetime(2026, 11, 23, 7, 30, tzinfo=timezone.utc)
    ctx = {"trump": [
        {"title": "Quote post from November 23, 2026", "published": "2026-11-23T05:08:30+00:00", "bias": []},
        {"title": "It is incredible what happened in Minnesota, they own it and almost all are on some form of "
                  "welfare and nobody does anything about it, which is a disgrace for the once great State. MAKE AMERIC",
         "published": "2026-11-22T21:53:08+00:00", "bias": []},
        {"title": "Isn’t it interesting that Oil prices have dropped precipitously after the Midterm Elections? "
                  "I said that was going to happen.", "published": "2026-11-22T21:49:11+00:00", "bias": []},
        {"title": "Tariffs on gold imports", "published": "2026-11-22T20:00:00+00:00",
         "bias": [{"instrument": "GOLD", "bias": "LONG_BIAS"}]},
        {"title": "Old post about oil", "published": "2026-11-20T20:00:00+00:00", "bias": []},
    ]}
    lines = briefing.trump_lines(ctx, now)
    text = "\n".join(lines)
    assert "Quote post" not in text and "Old post" not in text
    assert lines[0].startswith("• Isn’t it interesting that Oil") and "→ Petrolio WTI" in lines[0]
    assert "→ Oro ⬆️" in lines[1]
    assert "MAKE AMERIC" not in text and lines[2].endswith("great State.")


def test_short_text_cuts_on_word_when_no_sentence_end():
    out = briefing.short_text("word " * 80)
    assert out.endswith("…") and len(out) <= briefing.MAX_TRUMP_CHARS + 1


PMI = {"title": "Flash Manufacturing PMI", "country": "USD", "date": "2026-11-24T09:45:00-05:00",
       "impact": "Medium", "forecast": "54.5", "previous": "56.0"}
SPEECH = {"title": "FOMC Member Williams Speaks", "country": "USD", "date": "2026-11-24T16:00:00-05:00",
          "impact": "Medium"}


def test_medium_events_in_brief_and_light_alert_15_minutes_before():
    sent = []
    st = briefing.run(NOW, fetcher=fetcher, calendar_fetcher=lambda: [CPI, PMI, SPEECH],
                      context_fetcher=lambda: CTX, send=lambda t: sent.append(t) or True, st={})
    brief = next(t for t in sent if "BOLLETTINO" in t)
    assert "🟡 15:45 Flash Manufacturing PMI [importanza media]" in brief and "Williams" not in brief
    assert "Zone pericolose: 14:15–14:45." in brief and "🟡 Dati di importanza media" in brief
    sent.clear()
    at = datetime(2026, 11, 24, 14, 30, tzinfo=timezone.utc)      # 15:30 a Roma
    briefing.run(at, fetcher=fetcher, calendar_fetcher=lambda: [CPI, PMI], context_fetcher=lambda: CTX,
                 send=lambda t: sent.append(t) or True, st=st)
    assert len(sent) == 1 and sent[0].startswith("🟡 ATTENZIONE — tra 15 minuti (15:45): Flash Manufacturing PMI (previsto 54.5")
    assert "dalle 15:40 alle 15:50" in sent[0]
    sent.clear()
    briefing.run(at + timedelta(minutes=5), fetcher=fetcher, calendar_fetcher=lambda: [CPI, PMI],
                 context_fetcher=lambda: CTX, send=lambda t: sent.append(t) or True, st=st)
    assert sent == []


def test_medium_alert_not_sent_too_early():
    sent = []
    early = datetime(2026, 11, 24, 14, 0, tzinfo=timezone.utc)     # 45 minuti prima
    briefing.run(early, fetcher=fetcher, calendar_fetcher=lambda: [PMI], context_fetcher=lambda: CTX,
                 send=lambda t: sent.append(t) or True, st={"brief_date": "2026-11-24"})
    assert sent == []


def test_macro_lines_dollar_yields_and_opec():
    def f(symbol, **_):
        closes = [100.0] * 20 + [102.0] if symbol == "DX-Y.NYB" else [4.5] * 20 + [4.8]
        return bars_from(closes)
    opec = {"title": "OPEC-JMMC Meetings", "country": "ALL", "date": "2026-11-26T08:00:00-05:00", "impact": "Medium"}
    lines = briefing.macro_lines(f, [opec], NOW)
    assert lines[0].startswith("• Dollaro (indice DXY): 102,0, +2,0% in una settimana → pressione sull'oro")
    assert "+30 punti base in una settimana → pressione su oro e Nasdaq" in lines[1]
    assert lines[2].startswith("• 🛢️ OPEC-JMMC Meetings: gio 26/11 14:00")
