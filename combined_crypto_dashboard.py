from pathlib import Path

script = r'''import streamlit as st
import ccxt
import pandas as pd
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go

# ============================================================
# Combined Crypto Screener + Technical Dashboard
# Exchange: KuCoin spot public market data (no trading/orders)
# Indicators: EMA 9/20/200, RSI 14, MACD, ADX
# ============================================================

st.set_page_config(page_title="Crypto Screener + Technical Dashboard", layout="wide")
st.title("📊 Crypto Screener + Technical Dashboard")
st.caption("Public market data only. This app does not place trades. Signals are for testing, not financial advice.")

TIMEFRAMES = ["15m", "30m", "1h", "4h", "1d"]
timeframe = st.selectbox("Select timeframe", TIMEFRAMES, index=4)
limit = 250  # enough candles for EMA 200

# ----------------------------
# Exchange and market list
# ----------------------------
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({
        "enableRateLimit": True,
        "timeout": 20000,
        "options": {"defaultType": "spot"},
    })

exchange = get_exchange()

@st.cache_data(ttl=3600, show_spinner=False)
def load_usdt_symbols():
    ex = get_exchange()
    markets = ex.load_markets()
    result = []
    for symbol, market in markets.items():
        if (
            market.get("spot")
            and market.get("active", True) is not False
            and market.get("quote") == "USDT"
            and "/" in symbol
        ):
            result.append(symbol)
    # Prefer common pairs at the top, then sort remaining symbols
    preferred = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "PEPE/USDT"]
    result = sorted(set(result))
    ordered = [s for s in preferred if s in result]
    ordered += [s for s in result if s not in ordered]
    return ordered

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlcv(symbol, timeframe, limit):
    ex = get_exchange()
    rows = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not rows:
        raise ValueError(f"No candle data returned for {symbol}")
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    return df

def add_indicators(df):
    df = df.copy()
    df["ema9"] = EMAIndicator(close=df["close"], window=9).ema_indicator()
    df["ema20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(close=df["close"], window=50).ema_indicator()
    df["ema200"] = EMAIndicator(close=df["close"], window=200).ema_indicator()
    macd = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()
    df["rsi14"] = RSIIndicator(close=df["close"], window=14).rsi()
    df["adx14"] = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14).adx()
    return df

def format_price(value):
    try:
        value = float(value)
        if value >= 1000:
            return f"{value:,.2f}"
        if value >= 1:
            return f"{value:.4f}"
        if value >= 0.01:
            return f"{value:.6f}"
        return f"{value:.10f}"
    except (TypeError, ValueError):
        return "N/A"

def price_chart(df, symbol, timeframe):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price"
    ))
    for col, name in [
        ("ema9", "EMA 9"), ("ema20", "EMA 20"), ("ema50", "EMA 50"), ("ema200", "EMA 200")
    ]:
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df[col], mode="lines", name=name))
    fig.update_layout(
        title=f"{symbol} — {timeframe}",
        template="plotly_dark",
        height=620,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h")
    )
    return fig

# ----------------------------
# Load supported symbols
# ----------------------------
try:
    with st.spinner("Loading KuCoin spot markets..."):
        symbols = load_usdt_symbols()
except Exception as exc:
    st.error(f"Could not load KuCoin market list: {exc}")
    st.info("Refresh the app and try again. If this persists, check the app logs or exchange availability.")
    st.stop()

if not symbols:
    st.error("KuCoin did not return any active USDT spot pairs.")
    st.stop()

st.success(f"Loaded {len(symbols)} active KuCoin USDT spot pairs.")

# User can select ANY listed market; selection is not limited to bullish coins
preferred_default = "BTC/USDT" if "BTC/USDT" in symbols else symbols[0]
selected_symbol = st.selectbox(
    "Choose any coin to analyze:",
    options=symbols,
    index=symbols.index(preferred_default),
    key="coin_selector"
)

# ----------------------------
# Scan selected coin
# ----------------------------
try:
    with st.spinner(f"Fetching {selected_symbol} candles..."):
        raw_df = fetch_ohlcv(selected_symbol, timeframe, limit)
        df = add_indicators(raw_df)
except Exception as exc:
    st.error(f"Could not load candles for {selected_symbol}: {exc}")
    st.stop()

if len(df) < 200:
    st.warning(f"Only {len(df)} candles are available. EMA 200 may be incomplete or unavailable for this pair/timeframe.")

latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) >= 2 else latest
valid = pd.notna(latest["ema200"]) and pd.notna(latest["rsi14"]) and pd.notna(latest["macd_signal"])

st.subheader(f"📈 Technical Dashboard: {selected_symbol}")
try:
    updated = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M:%S %p IST")
except Exception:
    updated = datetime.now().strftime("%Y-%m-%d %I:%M:%S")
st.caption(f"Updated: {updated} • Data source: KuCoin spot public API")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Price (USDT)", format_price(latest["close"]))
c2.metric("EMA 9", format_price(latest["ema9"]))
c3.metric("EMA 20", format_price(latest["ema20"]))
c4.metric("EMA 200", format_price(latest["ema200"]))

c5, c6, c7 = st.columns(3)
c5.metric("RSI (14)", f'{latest["rsi14"]:.2f}' if pd.notna(latest["rsi14"]) else "N/A")
c6.metric("MACD", format_price(latest["macd"]))
c7.metric("MACD Signal", format_price(latest["macd_signal"]))

macd_bullish = pd.notna(latest["macd"]) and pd.notna(latest["macd_signal"]) and latest["macd"] > latest["macd_signal"]
ema_bullish = pd.notna(latest["ema9"]) and pd.notna(latest["ema20"]) and pd.notna(latest["ema200"]) and latest["ema9"] > latest["ema20"] > latest["ema200"]
rsi_value = latest["rsi14"]
adx_value = latest["adx14"]

st.markdown("### Signal summary")
if not valid:
    st.warning("Not enough historical candles to calculate all indicators reliably.")
elif ema_bullish and macd_bullish and pd.notna(rsi_value) and 50 < rsi_value < 70:
    st.success("Bullish setup: EMA 9 > EMA 20 > EMA 200, MACD > Signal, and RSI is between 50 and 70. This is an indicator condition, not a guaranteed buy signal.")
else:
    st.info("Full bullish conditions are not met right now. Check the individual indicators; this does not necessarily mean the coin will fall.")

if pd.notna(adx_value):
    st.write(f"ADX (14): **{adx_value:.2f}** — {'stronger trend' if adx_value > 25 else 'weak or developing trend'}")
st.write(f"MACD histogram: **{format_price(latest['macd_hist'])}**")

# ----------------------------
# Price chart and recent data
# ----------------------------
st.plotly_chart(price_chart(df, selected_symbol, timeframe), use_container_width=True)

with st.expander("Show recent candles and indicators"):
    cols = ["timestamp", "open", "high", "low", "close", "volume", "ema9", "ema20", "ema200", "rsi14", "macd", "macd_signal", "adx14"]
    st.dataframe(df[cols].tail(30).sort_values("timestamp", ascending=False), use_container_width=True)

# ----------------------------
# Optional bullish scan across all loaded markets
# ----------------------------
with st.expander("Run bullish scan across all listed USDT pairs"):
    scan_limit = st.slider("Candles per coin (scan)", min_value=210, max_value=250, value=210, step=10)
    max_scan = st.slider("Maximum number of coins to scan", min_value=5, max_value=min(100, len(symbols)), value=min(20, len(symbols)), step=5)
    if st.button("Scan for bullish setups"):
        matches = []
        progress = st.progress(0)
        status = st.empty()
        scan_symbols = symbols[:max_scan]
        for i, sym in enumerate(scan_symbols):
            try:
                scan_df = add_indicators(fetch_ohlcv(sym, timeframe, scan_limit))
                row = scan_df.iloc[-1]
                if (
                    pd.notna(row["ema200"])
                    and row["ema9"] > row["ema20"] > row["ema200"]
                    and row["macd"] > row["macd_signal"]
                    and 50 < row["rsi14"] < 70
                ):
                    matches.append({
                        "Coin": sym,
                        "Price (USDT)": format_price(row["close"]),
                        "EMA 9": format_price(row["ema9"]),
                        "EMA 20": format_price(row["ema20"]),
                        "EMA 200": format_price(row["ema200"]),
                        "RSI 14": round(float(row["rsi14"]), 2),
                        "MACD": format_price(row["macd"]),
                        "MACD Signal": format_price(row["macd_signal"]),
                        "ADX 14": round(float(row["adx14"]), 2),
                    })
            except Exception:
                pass
            progress.progress((i + 1) / len(scan_symbols))
            status.write(f"Scanned {i + 1}/{len(scan_symbols)}: {sym}")
        progress.empty()
        status.empty()
        if matches:
            st.success(f"Found {len(matches)} bullish setup(s).")
            st.dataframe(pd.DataFrame(matches), use_container_width=True)
        else:
            st.info("No bullish setups found in the selected scan subset.")
'''
path = "/mnt/data/crypto_screener_dashboard_fixed.py"
Path(path).write_text(script, encoding="utf-8")
print(path, len(script.splitlines()))
