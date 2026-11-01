from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "static" / "aggressive.html").read_text(encoding="utf-8")


def test_paper_signal_is_never_rendered_as_authorized_entry():
    assert "action==='PAPER_ENTRY'&&trade==='ENTRY_AUTHORIZED_PAPER_ONLY'&&setup==='CONFIRMED'" in HTML
    assert "action==='PAPER_SIGNAL'||trade==='SIGNAL_ONLY_NOT_EXECUTED'" in HTML
    assert "SIGNAL ONLY · NON ESEGUITO" in HTML
    assert "PAPER AUTORIZZATO · NON ESEGUITO" in HTML


def test_market_price_is_not_used_as_entry_fallback_and_levels_require_fresh_setup():
    assert "const hasFreshSetup=['EARLY_SETUP','CONFIRMED'].includes(setup);" in HTML
    assert "const entry=hasFreshSetup?val(x,'entry'):null;" in HTML
    assert "const marketPrice=hasFreshSetup?val(x,'price'):null;" in HTML
    assert "val(x,'entry','price')" not in HTML
    assert "Prezzo di mercato" in HTML
    assert "Entry/SL/TP omessi: prezzo o ATR freschi non disponibili" in HTML
    assert "'+esc(levelNote)+'" in HTML


def test_dashboard_keeps_bias_setup_and_paper_state_separate():
    assert "<span>BIAS</span>" in HTML
    assert "<span>SETUP</span>" in HTML
    assert "<span>TRADE PAPER</span>" in HTML
    assert "Nessun ordine reale" in HTML
