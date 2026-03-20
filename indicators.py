import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

def add_rsi(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df = df.copy()
    rsi = RSIIndicator(close=df["close"], window=period)
    df["rsi"] = rsi.rsi()
    return df
from ta.volatility import AverageTrueRange

def add_atr(df, window=14):
    # Not enough candles to compute ATR
    if len(df) < window:
        df["atr"] = 0
        return df

    try:
        atr = AverageTrueRange(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=window,
            fillna=True
        ).average_true_range()
        df["atr"] = atr
    except Exception:
        df["atr"] = 0

    return df


def add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["returns"] = df["close"].pct_change()
    df["volatility"] = df["returns"].rolling(20).std() * 100
    return df
