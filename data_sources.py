import ccxt
import pandas as pd


def get_exchange(name: str):
    name = name.upper()
    if name == "BYBIT":
        return ccxt.bybit()
    if name == "OKX":
        return ccxt.okx()
    if name == "KUCOIN":
        return ccxt.kucoin()
    if name == "BINGX":
        return ccxt.bingx()
    raise ValueError(f"Unsupported exchange: {name}")


def fetch_ohlcv_safe(exchange, symbol: str, timeframe: str, limit: int = 200):
    try:
        markets = exchange.load_markets()
        if symbol not in markets:
            print(f"{exchange.id} does not have market symbol {symbol}")
            return None

        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return None

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"Error fetching {exchange.id} {symbol} {timeframe}: {e}")
        return None
