"""Runner that preserves commodity_bot.py and adds the live-price execution layer."""
import commodity_bot as bot
from live_price_engine import apply_live_quote


_original_analyze = bot.analyze


def analyze_with_live_price(*args, **kwargs):
    analysis = _original_analyze(*args, **kwargs)
    if analysis is None:
        return None
    name = kwargs.get("commodity_name")
    if name is None and len(args) >= 6:
        # commodity_name is normally passed by keyword in the current engine.
        name = None
    symbol = kwargs.get("symbol")
    # main() owns the resolved symbol, so we derive it from the commodity map.
    if name:
        symbol = symbol or bot.resolve_commodity_symbols().get(name, bot.COMMODITIES.get(name, name))
        apply_live_quote(analysis, name, symbol)
    return analysis


bot.analyze = analyze_with_live_price

# Keep Telegram concise but explicitly expose the live quote source and BID/ASK.
_original_detail = getattr(bot, "_telegram_commodity_detail", None)
if _original_detail:
    def _telegram_detail_live(item):
        text = _original_detail(item)
        a = (item or {}).get("analysis", {}) or {}
        q = a.get("live_quote", {}) or {}
        if q.get("available"):
            lines = []
            lines.append(f"📡 LIVE {q.get('provider','N/D')} | {a.get('live_price_basis','N/D')}")
            if q.get("bid") is not None and q.get("ask") is not None:
                lines.append(f"📈 BID: {bot._fmt_price(q['bid'])} | ASK: {bot._fmt_price(q['ask'])}")
            if q.get("timestamp"):
                lines.append(f"🕒 Quote: {q['timestamp']}")
            block = "\n".join(lines)
            marker = f"💰 Prezzo:"
            if marker in text:
                text = text.replace(marker, block + "\n" + marker, 1)
            else:
                text = text + "\n\n" + block
        else:
            text = text.replace("💰 Prezzo:", "⚠️ Prezzo live non disponibile\n💰 Prezzo:", 1)
        return text
    bot._telegram_commodity_detail = _telegram_detail_live

# Refuse demo execution when no fresh live quote exists. This prevents a stale
# candle price from ever becoming the entry price of the future demo adapter.
_original_demo = bot.demo_execution_adapter

def demo_execution_live_guard(results, position):
    eligible = []
    for item in results:
        a = item.get("analysis", {}) or {}
        if item.get("available") and a.get("live_price_status") == "LIVE":
            eligible.append(item)
    if not eligible:
        return {"enabled": bool(bot.DEMO_TRADING_ENABLED), "executed": False, "reason": "NESSUN PREZZO LIVE DISPONIBILE"}
    return _original_demo(results, position)


bot.demo_execution_adapter = demo_execution_live_guard


if __name__ == "__main__":
    bot.main()
