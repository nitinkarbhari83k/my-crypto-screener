import streamlit as st
import ccxt
import pandas as pd
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.graph_objects as go

# ================================
# Streamlit Setup
# ================================
st.set_page_config(page_title="Combined Crypto Screener & TA", layout="wide")
st.title("📊 Combined Bullish Screener + Technical Dashboard")

# ================================
# Timeframe Selection
# ================================
timeframe = st.selectbox("Select timeframe", ["15m", "30m", "1h", "4h", "1d"], index=4)
limit = 200

# =============================
# Exchange Setup
# =============================
exchange = ccxt.kucoin({
    'enableRateLimit': True,
    'headers': {
        'User-Agent': 'Mozilla/5.0 (compatible; StreamlitBot/1.0)'
    }
})

# ================================
# Utility Functions
# ================================
@st.cache_data(ttl=300)
def fetch_ohlcv(symbol, timeframe, limit):
    return exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

def get_support_resistance(df, lookback=20):
    recent = df[-lookback:]
    return round(recent['low'].min(), 4), round(recent['high'].max(), 4)

def format_price(value):
    if value >= 1:
        return f"{value:.4f}"
    elif value >= 0.01:
        return f"{value:.6f}"
    else:
        return f"{value:.8f}"


def plot_price_chart(df, symbol):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name='Price',
        increasing_line_color='green', decreasing_line_color='red'
    ))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema50'], line=dict(color='blue'), name='EMA 50'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema200'], line=dict(color='orange'), name='EMA 200'))
    fig.update_layout(
        title=f"{symbol} Price Chart ({timeframe})",
        template='plotly_dark',
        height=600,
        xaxis_rangeslider_visible=False
    )
    return fig

# ================================
# Symbols List
# ================================
symbols = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "USDC/USDT",
    "XRP/USDT", "DOGE/USDT", "TRX/USDT", "TON/USDT", "ADA/USDT",
    "AVAX/USDT", "SHIB/USDT", "LINK/USDT", "BCH/USDT", "DOT/USDT",
    "NEAR/USDT", "SUI/USDT", "LEO/USDT", "DAI/USDT", "APT/USDT",
    "LTC/USDT", "UNI/USDT", "TAO/USDT", "PEPE/USDT", "ICP/USDT",
    "FET/USDT", "KAS/USDT", "FDUSD/USDT", "XMR/USDT", "RENDER/USDT",
    "ETC/USDT", "POL/USDT", "XLM/USDT", "STX/USDT", "WIF/USDT",
    "IMX/USDT", "OKB/USDT", "AAVE/USDT", "FIL/USDT", "OP/USDT",
    "INJ/USDT", "HBAR/USDT", "FTM/USDT", "MNT/USDT", "CRO/USDT",
    "ARB/USDT", "VET/USDT", "SEI/USDT", "ATOM/USDT", "RUNE/USDT",
    "GRT/USDT", "BONK/USDT", "BGB/USDT", "FLOKI/USDT", "TIA/USDT",
    "THETA/USDT", "WLD/USDT", "OM/USDT", "POPCAT/USDT", "AR/USDT",
    "PYTH/USDT", "MKR/USDT", "ENA/USDT", "JUP/USDT", "BRETT/USDT",
    "HNT/USDT", "ALGO/USDT", "ONDO/USDT", "LDO/USDT", "KCS/USDT",
    "MATIC/USDT", "JASMY/USDT", "BSV/USDT", "CORE/USDT", "AERO/USDT",
    "BTT/USDT", "NOT/USDT", "FLOW/USDT", "GT/USDT", "W/USDT",
    "STRK/USDT", "NEIRO/USDT", "BEAM/USDT", "QNT/USDT", "GALA/USDT",
    "ORDI/USDT", "CFX/USDT", "FLR/USDT", "USDD/USDT", "EGLD/USDT",
    "NEO/USDT", "AXS/USDT", "EOS/USDT", "MOG/USDT", "XEC/USDT",
    "CHZ/USDT", "MEW/USDT", "XTZ/USDT", "CKB/USDT"
]
stablecoins = ["USDC/USDT", "DAI/USDT", "USDD/USDT", "FDUSD/USDT", "TUSD/USDT", "BUSD/USDT"]
symbols = [s for s in symbols if s not in stablecoins]

# ================================
# Bullish Screener
# ================================
st.subheader("📈 Bullish Coin Screener")
bullish_coins = []
progress = st.progress(0)

for i, symbol in enumerate(symbols):
    try:
        ohlcv = fetch_ohlcv(symbol, timeframe, limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema50'] = EMAIndicator(df['close'], window=50).ema_indicator()
        df['ema200'] = EMAIndicator(df['close'], window=200).ema_indicator()
        macd = MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        adx = ADXIndicator(df['high'], df['low'], df['close'])
        df['adx'] = adx.adx()
        df['rsi'] = RSIIndicator(df['close']).rsi()

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        if (
            latest['ema50'] > latest['ema200'] and
            latest['macd'] > latest['macd_signal'] and
            latest['adx'] > 25 and
            50 < latest['rsi'] < 70
        ):
            change_pct = ((latest['close'] - previous['close']) / previous['close']) * 100
            support, resistance = get_support_resistance(df)
            bullish_coins.append({
                "symbol": symbol,
                "price": latest['close'],
                "change": change_pct,
                "adx": latest['adx'],
                "rsi": latest['rsi'],
                "support": support,
                "resistance": resistance
            })
    except Exception:
        # Silently ignore errors to continue processing
        pass
    progress.progress((i + 1) / len(symbols))

# ================================
# Display Bullish Coins
# ================================
if bullish_coins:
    bullish_coins = sorted(bullish_coins, key=lambda x: x["change"], reverse=True)
    selected_symbol = st.selectbox(
        "Choose a coin to analyze in detail:",
        [coin["symbol"] for coin in bullish_coins]
    )
    for coin in bullish_coins:
        if coin["symbol"] == selected_symbol:
            change_symbol = "🟢" if coin["change"] > 0 else "🔴"
            change_arrow = "↑" if coin["change"] > 0 else "↓"
            change_pct = abs(coin["change"])
            st.markdown(
                f"✔️ **{coin['symbol']}** • Price: `${format_price(coin['price'])}` • `{change_symbol} Change: {change_pct:.2f}% {change_arrow}` • ADX: `{coin['adx']:.1f}` • RSI: `{coin['rsi']:.1f}`  \n"
                f" 📌 Support: `${format_price(coin['support'])}` • Resistance: `${format_price(coin['resistance'])}`"
            )
else:
    st.info("No bullish setups found.")
    selected_symbol = None

# ================================
# Deep Technical Analysis Section
# ================================
if selected_symbol:
    ohlcv = fetch_ohlcv(selected_symbol, timeframe, limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['ema50'] = EMAIndicator(df['close'], window=50).ema_indicator()
    df['ema200'] = EMAIndicator(df['close'], window=200).ema_indicator()
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    adx = ADXIndicator(df['high'], df['low'], df['close'])
    df['adx'] = adx.adx()

    latest = df.iloc[-1]
    swing_low = df['low'].min()
    swing_high = df['high'].max()
    fib1 = swing_high + (swing_high - swing_low) * 0.618
    fib2 = swing_high + (swing_high - swing_low) * 1.0

    st.subheader(f"📊 Technical Dashboard: {selected_symbol}")
    time_now = datetime.now(ZoneInfo("Asia/Phnom_Penh")).strftime("%Y-%m-%d %I:%M %p")
    st.caption(f"🕒 Updated at: {time_now}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${format_price(latest['close'])}")
    col2.metric("EMA50", f"${format_price(latest['ema50'])}")
    col3.metric("EMA200", f"${format_price(latest['ema200'])}")

    st.markdown(
        f"**Indicators:**  \n"
        f"- MACD: `{format_price(latest['macd'])}` | Signal: `{format_price(latest['macd_signal'])}`  \n"
        f"- ADX: `{format_price(latest['adx'])}` → *{'Strong trend' if latest['adx'] > 25 else 'Weak trend'}*"
    )

    if latest['ema50'] > latest['ema200'] and latest['macd'] > latest['macd_signal'] and latest['adx'] > 25:
        st.success(
            "✅ **STRONG BUY SIGNAL** based on:\n"
            "- EMA crossover (EMA50 > EMA200)\n"
            "- MACD bullish confirmation (MACD > Signal)\n"
            "- ADX > 25 (strong trend)"
        )
        st.markdown(
            f"🎯 **Target 1 (Fib 0.618):** `${format_price(fib1)}`  \n"
            f"🎯 **Target 2 (Fib 1.000):** `${format_price(fib2)}`"
        )
    else:
        st.warning("🚫 No strong buy signal yet. Wait for further confirmation.")

    st.plotly_chart(plot_price_chart(df, selected_symbol), use_container_width=True)
