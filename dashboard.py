import time
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yaml

from scanner import main as run_scanner
from data_sources import get_exchange, fetch_ohlcv_safe

# ---------------- Basic setup ---------------- #

st.set_page_config(page_title="Crypto Scanner", layout="wide")

@st.cache_resource
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

cfg = load_config()

# ---------------- Caching for OHLCV ---------------- #

@st.cache_data(ttl=60)
def load_ohlcv(exchange_name: str, symbol: str, timeframe: str, limit: int = 200):
    ex = get_exchange(exchange_name)
    return fetch_ohlcv_safe(ex, symbol, timeframe, limit=limit)

# ---------------- Helpers ---------------- #

def compute_change_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "close" in df.columns and "open" in df.columns:
        df["change_abs"] = df["close"] - df["open"]
        df["change_pct"] = (df["change_abs"] / df["open"]) * 100
    return df

def generate_signal_explanation(row: pd.Series) -> str:
    direction = row.get("direction", "unknown")
    vol = row.get("volume", None)
    hv = row.get("high_volatility", False)
    parts = []

    if direction == "bullish":
        parts.append("Price action is leaning bullish, suggesting upward momentum.")
    elif direction == "bearish":
        parts.append("Price action is leaning bearish, suggesting downward pressure.")
    elif direction == "mixed":
        parts.append("Signals are mixed, indicating indecision or choppy conditions.")
    else:
        parts.append("Direction is unclear from the current signal set.")

    if hv:
        parts.append("Volatility is elevated, so moves may be fast and wide.")
    else:
        parts.append("Volatility appears relatively contained.")

    if vol is not None:
        parts.append(f"Current volume is around {int(vol):,}, above your minimum filter.")

    return " ".join(parts)

def detect_new_signals(df: pd.DataFrame, key: str = "seen_signals"):
    if key not in st.session_state:
        st.session_state[key] = set()

    current_keys = set(
        df.apply(lambda r: f"{r.get('exchange','')}|{r.get('symbol','')}|{r.get('direction','')}", axis=1)
    )
    new = current_keys - st.session_state[key]
    st.session_state[key] = current_keys
    return new

# ---------------- Title & Sidebar ---------------- #

st.title("📡 Real-Time Multi-Exchange Crypto Scanner")

with st.sidebar:
    st.header("Controls")

    refresh_seconds = st.slider(
        "Refresh every (seconds)",
        5, 120, 20,
        key="refresh_slider"
    )

    min_volume_filter = st.number_input(
        "Min Volume Filter",
        value=cfg["min_volume"],
        step=100000,
        key="vol_filter"
    )

    high_vol_only = st.checkbox(
        "Show only high-volatility symbols",
        value=False,
        key="high_vol"
    )

    st.markdown("---")

    exchange_filter = st.multiselect(
        "Filter by exchange",
        options=cfg.get("exchanges", []),
        default=cfg.get("exchanges", []),
        key="exchange_filter"
    )

    direction_filter = st.multiselect(
        "Filter by direction",
        options=["bullish", "bearish", "mixed"],
        default=["bullish", "bearish", "mixed"],
        key="direction_filter"
    )

    st.markdown("---")

    live_mode = st.checkbox(
        "Live mode (auto-refresh)",
        value=True,
        key="live_mode"
    )

# ---------------- Auto-refresh (simulated live) ---------------- #

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if live_mode and (time.time() - st.session_state.last_refresh >= refresh_seconds):
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# ---------------- Placeholders ---------------- #

placeholder_table = st.empty()

# ---------------- Scanner run ---------------- #

with st.spinner("Scanning exchanges..."):
    df = run_scanner(return_df=True)

if df is None or df.empty:
    with placeholder_table.container():
        st.subheader("Latest Signals")
        st.write("No setups detected.")
    st.stop()

df = compute_change_cols(df)

# ---------------- Filters ---------------- #

filtered = df[df["volume"] >= min_volume_filter].copy()

if high_vol_only and "high_volatility" in filtered.columns:
    filtered = filtered[filtered["high_volatility"] == True]

if exchange_filter:
    filtered = filtered[filtered["exchange"].isin(exchange_filter)]

if direction_filter and "direction" in filtered.columns:
    filtered = filtered[filtered["direction"].isin(direction_filter)]

# ---------------- Alerts for new signals ---------------- #

new_signals = detect_new_signals(filtered)
if new_signals:
    st.toast(f"🔔 {len(new_signals)} new signal(s) detected", icon="🔔")

# ---------------- Layout: tabs ---------------- #

tab_signals, tab_charts, tab_overview, tab_settings = st.tabs(
    ["📋 Signals", "📈 Charts", "📊 Overview", "⚙️ Settings"]
)

# ---------------- Signals tab ---------------- #

with tab_signals:
    st.subheader("Latest Signals")

    if filtered.empty:
        st.write("No setups match your current filters.")
    else:
        st.dataframe(
            filtered.sort_values("timestamp", ascending=False),
            use_container_width=True
        )

        st.markdown("### Signal Insight")

        row_idx = st.number_input(
            "Select row index for explanation",
            min_value=0,
            max_value=len(filtered) - 1,
            value=0,
            step=1,
            key="explain_row_idx"
        )

        row = filtered.iloc[int(row_idx)]
        explanation = generate_signal_explanation(row)

        st.info(
            f"**{row['exchange']} - {row['symbol']} ({row.get('direction','n/a')})**\n\n"
            f"{explanation}"
        )

# ---------------- Charts tab ---------------- #

with tab_charts:
    st.subheader("Price Charts")

    if filtered.empty:
        st.write("No symbols available for charting.")
    else:
        symbols = sorted(filtered["symbol"].unique().tolist())
        exchanges = sorted(filtered["exchange"].unique().tolist())

        col1, col2 = st.columns(2)

        with col1:
            sel_exchange = st.selectbox(
                "Exchange",
                exchanges,
                key="chart_exchange"
            )

            sel_timeframe = st.selectbox(
                "Timeframe",
                cfg["timeframes"],
                key="chart_timeframe"
            )

        with col2:
            multi_symbols = st.multiselect(
                "Symbols (multi-select for overlay)",
                symbols,
                default=symbols[:3],
                key="chart_symbols"
            )

        if not multi_symbols:
            st.write("Select at least one symbol to display a chart.")
        else:
            fig = go.Figure()

            for sym in multi_symbols:
                ohlcv_df = load_ohlcv(sel_exchange, sym, sel_timeframe, limit=200)
                if ohlcv_df is None or ohlcv_df.empty:
                    continue

                ohlcv_df = ohlcv_df.sort_values("timestamp")
                base = ohlcv_df["close"].iloc[0]
                ohlcv_df["norm_pct"] = (ohlcv_df["close"] / base - 1) * 100

                fig.add_trace(
                    go.Scatter(
                        x=ohlcv_df["timestamp"],
                        y=ohlcv_df["norm_pct"],
                        mode="lines",
                        name=sym
                    )
                )

            if not fig.data:
                st.write("No data available for the selected combination.")
            else:
                fig.update_layout(
                    title=f"Normalized % Change - {sel_exchange} ({sel_timeframe})",
                    xaxis_title="Time",
                    yaxis_title="% Change",
                    legend_title="Symbol",
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Single-Symbol Raw Price")

        single_symbol = st.selectbox(
            "Symbol for raw price chart",
            symbols,
            key="single_symbol_chart"
        )

        ohlcv_single = load_ohlcv(sel_exchange, single_symbol, sel_timeframe, limit=200)
        if ohlcv_single is not None and not ohlcv_single.empty:
            ohlcv_single = ohlcv_single.sort_values("timestamp")
            fig_price = px.line(
                ohlcv_single,
                x="timestamp",
                y="close",
                title=f"{sel_exchange} {single_symbol} {sel_timeframe} Close Price"
            )
            st.plotly_chart(fig_price, use_container_width=True)
        else:
            st.write("No data available for raw price chart.")

# ---------------- Overview tab ---------------- #

with tab_overview:
    st.subheader("Market Overview")

    if filtered.empty:
        st.write("No data available for overview.")
    else:
        latest = (
            filtered.sort_values("timestamp")
            .groupby(["exchange", "symbol"], as_index=False)
            .last()
        )

        if "change_pct" in latest.columns:
            top_gainers = latest.sort_values("change_pct", ascending=False).head(10)
            top_losers = latest.sort_values("change_pct", ascending=True).head(10)
        else:
            top_gainers = latest.head(10)
            top_losers = latest.head(10)

        top_volume = latest.sort_values("volume", ascending=False).head(10)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Top Gainers")
            st.dataframe(
                top_gainers[["exchange", "symbol", "change_pct", "volume"]],
                use_container_width=True
            )

        with col2:
            st.markdown("### Top Losers")
            st.dataframe(
                top_losers[["exchange", "symbol", "change_pct", "volume"]],
                use_container_width=True
            )

        with col3:
            st.markdown("### Highest Volume")
            st.dataframe(
                top_volume[["exchange", "symbol", "volume", "change_pct"]],
                use_container_width=True
            )

# ---------------- Settings / Info tab ---------------- #

with tab_settings:
    st.subheader("Settings & Info")
    st.write(
        "This dashboard includes:\n"
        "- Cached OHLCV data (60s TTL) per exchange/symbol/timeframe\n"
        "- Auto-refresh via 'Live mode' and refresh interval\n"
        "- Rule-based signal explanations\n"
        "- Multi-symbol normalized charts and single-symbol raw price charts\n"
        "- Market overview (gainers, losers, volume)\n"
        "- Basic alerting for new signals via toast notifications\n"
    )
    st.write("Tune `config.yaml` to adjust exchanges, timeframes, and defaults.")
