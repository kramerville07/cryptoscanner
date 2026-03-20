import yaml
import pandas as pd
from datetime import datetime, timezone

from data_sources import get_exchange, fetch_ohlcv_safe
from indicators import add_rsi, add_atr, add_volatility_features
from setups import (
    detect_engulfing,
    detect_rsi_signals,
    infer_direction,
    multi_timeframe_confirmation,
)
from alerts import send_alerts_for_signals

OUTPUT_CSV = "scanner_results.csv"


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def scan_symbol_tf(exchange_name, exchange, symbol, timeframe, cfg):
    df = fetch_ohlcv_safe(exchange, symbol, timeframe)
    if df is None or df.empty:
        return None

    # Indicators
    df = add_rsi(df, cfg["rsi_period"])
    df = add_atr(df)
    df = add_volatility_features(df)

    setups = []

    # Engulfing
    engulf = detect_engulfing(df)
    if engulf:
        setups.append(engulf)

    # RSI signals
    rsi_signals = detect_rsi_signals(
        df, cfg["rsi_overbought"], cfg["rsi_oversold"]
    )
    setups.extend(rsi_signals)

    # If no setups, skip
    if not setups:
        return None

    last = df.iloc[-1]

    # Volume filter
    if last["volume"] < cfg["min_volume"]:
        return None

    # Volatility (ATR%)
    atr_pct = (
        (last["atr"] / last["close"]) * 100
        if last["atr"] and last["close"]
        else 0
    )
    high_vol = atr_pct >= cfg["high_volatility_atr_pct"]

    # Direction
    direction = infer_direction(setups)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exchange": exchange_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "setups": ",".join(setups),
        "direction": direction,
        "close": float(last["close"]),
        "volume": float(last["volume"]),
        "atr_pct": float(atr_pct),
        "high_volatility": bool(high_vol),
    }


def main(return_df: bool = False):
    cfg = load_config()

    rows = []

    # Loop exchanges + their symbols
    for ex_name, symbols in cfg["exchanges"].items():
        exchange = get_exchange(ex_name)

        for symbol in symbols:
            for tf in cfg["timeframes"]:
                result = scan_symbol_tf(ex_name, exchange, symbol, tf, cfg)
                if result:
                    rows.append(result)

    # Build DataFrame
    if not rows:
        df = pd.DataFrame(
            columns=[
                "timestamp",
                "exchange",
                "symbol",
                "timeframe",
                "setups",
                "direction",
                "close",
                "volume",
                "atr_pct",
                "high_volatility",
                "mtf_confirmed",
                "score",
            ]
        )
    else:
        df = pd.DataFrame(rows)
        df = multi_timeframe_confirmation(df)

    # Save results
    df.to_csv(OUTPUT_CSV, index=False)
    print(df)
    print(f"Saved results to {OUTPUT_CSV}")

    # Telegram alerts
    send_alerts_for_signals(df)

    if return_df:
        return df


if __name__ == "__main__":
    main()
