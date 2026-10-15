# ============================================================
# TELEGRAM COMMANDS — Sezione INVEST
# ============================================================

from engine.invest import analyze_invest_universe, format_invest_report, get_trading212_demo_status

def handle_invest_command(argument: str = "") -> str:
    """
    Gestisce /invest e /invest_demo.
    """
    arg = (argument or "").strip().lower()

    if arg in {"status", "demo", "t212"}:
        return get_trading212_demo_status()

    signals = analyze_invest_universe()
    report = format_invest_report(signals)

    if arg == "demo":
        report += "\n\n" + get_trading212_demo_status()

    return report
