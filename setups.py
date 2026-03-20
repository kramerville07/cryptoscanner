import pandas as pd

def detect_engulfing(df: pd.DataFrame):
    if df is None or len(df) < 2:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    prev_red = prev["close"] < prev["open"]
    curr_green = last["close"] > last["open"]
    bullish_body = (last["close"] >= prev["open"]) and (last["open"] <= prev["close"])

    prev_green = prev["close"] > prev["open"]
    curr_red = last["close"] < last["open"]
    bearish_body = (last["close"] <= prev["open"]) and (last["open"] >= prev["close"])

    if prev_red and curr_green and bullish_body:
        return "bullish_engulfing"
    if prev_green and curr_red and bearish_body:
        return "bearish_engulfing"
    return None

def detect_rsi_signals(df: pd.DataFrame, overbought: float, oversold: float):
    if df is None or df.empty or "rsi" not in df.columns:
        return []

    last_rsi = df["rsi"].iloc[-1]
    signals = []
    if last_rsi >= overbought:
        signals.append("rsi_overbought")
    if last_rsi <= oversold:
        signals.append("rsi_oversold")
    return signals

def infer_direction(setups: list[str]) -> str:
    if any("bearish" in s for s in setups) and not any("bullish" in s for s in setups):
        return "bearish"
    if any("bullish" in s for s in setups) and not any("bearish" in s for s in setups):
        return "bullish"
    return "mixed"

def multi_timeframe_confirmation(df: pd.DataFrame):
    """
    Adds mtf_confirmed + score per row based on symbol+exchange aggregation.
    """
    if df is None or df.empty:
        df["mtf_confirmed"] = False
        df["score"] = 0
        return df

    df = df.copy()
    df["mtf_confirmed"] = False
    df["score"] = 0

    grouped = df.groupby(["exchange", "symbol"])

    for (ex, sym), g in grouped:
        directions = g["direction"].tolist()
        has_bull = "bullish" in directions
        has_bear = "bearish" in directions

        for idx, row in g.iterrows():
            score = 0
            if row["direction"] == "bullish" and has_bull:
                score += 1
            if row["direction"] == "bearish" and has_bear:
                score += 1
            if "rsi_overbought" in row["setups"]:
                score += 1
            if "rsi_oversold" in row["setups"]:
                score += 1
            if row.get("high_volatility", False):
                score += 1

            df.loc[idx, "score"] = score
            df.loc[idx, "mtf_confirmed"] = score >= 2

    return df
