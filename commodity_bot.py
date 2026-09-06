# ============================================================
# TELEGRAM — INVIO E VERIFICA
# ============================================================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN mancante nei GitHub Secrets."
        )

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID mancante."
        )

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    print("📨 Invio messaggio Telegram...")

    response = requests.post(
        url,
        json=payload,
        timeout=30
    )

    print(f"📡 Telegram HTTP: {response.status_code}")

    try:
        data = response.json()
    except Exception:
        data = {}

    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram errore HTTP {response.status_code}: "
            f"{response.text}"
        )

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram ha rifiutato il messaggio: {data}"
        )

    print("✅ Messaggio Telegram inviato correttamente.")