import requests
import yaml

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def send_telegram_message(text: str):
    config = load_config()
    tg_cfg = config.get("telegram", {})
    if not tg_cfg.get("enabled", False):
        return

    token = tg_cfg.get("bot_token")
    chat_id = tg_cfg.get("chat_id")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def send_alerts_for_signals(df):
    if df is None or df.empty:
        return

    # Only alert on strong, confirmed signals
    alerts_df = df[(df["mtf_confirmed"] == True) & (df["score"] >= 2)]
    for _, row in alerts_df.iterrows():
        direction = row["direction"].upper()
        msg = (
            f"*{direction} signal*\n"
            f"Exchange: `{row['exchange']}`\n"
            f"Symbol: `{row['symbol']}`\n"
            f"Timeframe: `{row['timeframe']}`\n"
            f"Setups: `{row['setups']}`\n"
            f"Close: `{row['close']}`\n"
            f"Volume: `{row['volume']}`\n"
            f"High Volatility: `{row['high_volatility']}`\n"
            f"Score: `{row['score']}`"
        )
        send_telegram_message(msg)
