import ccxt
import yaml

EXCHANGES = ["BYBIT", "KUCOIN", "BINGX", "OKX"]

def get_exchange(name):
    name = name.upper()
    if name == "BYBIT":
        return ccxt.bybit()
    if name == "KUCOIN":
        return ccxt.kucoin()
    if name == "BINGX":
        return ccxt.bingx()
    if name == "OKX":
        return ccxt.okx()
    raise ValueError(f"Unsupported exchange: {name}")

def fetch_top_usdt_pairs(exchange, limit=100):
    markets = exchange.load_markets()
    usdt_pairs = []

    for symbol, data in markets.items():
        if "USDT" in symbol and data.get("active", True):
            usdt_pairs.append(symbol)

    # Sort alphabetically for consistency
    usdt_pairs = sorted(usdt_pairs)

    return usdt_pairs[:limit]

def update_config():
    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    cfg["exchanges"] = {}

    for ex_name in EXCHANGES:
        ex = get_exchange(ex_name)
        print(f"Fetching top USDT pairs for {ex_name}...")
        pairs = fetch_top_usdt_pairs(ex, limit=100)
        cfg["exchanges"][ex_name] = pairs
        print(f"{ex_name}: {len(pairs)} pairs loaded.")

    with open("config.yaml", "w") as f:
        yaml.dump(cfg, f)

    print("\nconfig.yaml updated with top 100 USDT pairs per exchange.")

if __name__ == "__main__":
    update_config()
