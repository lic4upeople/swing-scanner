import yfinance as yf
import pandas as pd
import numpy as np
import logging
import datetime

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

capital = 10000
risk_per_trade = 200

# ---------------------------
# MARKET TREND FILTER (FIXED)
# ---------------------------

def market_trend_ok():
    nifty = yf.download("^NSEI", period="3mo", interval="1d", auto_adjust=True, progress=False)

    # 🔥 FIX: flatten multi-index columns
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)

    nifty = nifty[['Close']]

    nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
    nifty['EMA50'] = nifty['Close'].ewm(span=50).mean()

    nifty.dropna(inplace=True)
    latest = nifty.iloc[-1]

    close = float(latest['Close'])
    ema20 = float(latest['EMA20'])
    ema50 = float(latest['EMA50'])

    return close > ema50 and ema20 > ema50


# ---------------------------
# STOCK UNIVERSE
# ---------------------------

stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
    "ICICIBANK.NS","SBIN.NS","LT.NS","ITC.NS",
    "BHARTIARTL.NS","AXISBANK.NS","MARUTI.NS",
    "BAJFINANCE.NS","SUNPHARMA.NS","TITAN.NS"
]

results = []

# ---------------------------
# SCANNER
# ---------------------------

if market_trend_ok():
    print("📈 Market Trend: BULLISH")

    for stock in stocks:
        try:
            data = yf.download(stock, period="3mo", interval="1d", auto_adjust=True, progress=False)

            if data.empty or len(data) < 60:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            data = data[['High','Close','Volume']]

            data['EMA20'] = data['Close'].ewm(span=20).mean()
            data['EMA50'] = data['Close'].ewm(span=50).mean()
            data['AvgVolume'] = data['Volume'].rolling(20).mean()

            # RSI
            delta = data['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            rs = avg_gain / avg_loss
            data['RSI'] = 100 - (100 / (1 + rs))

            data.dropna(inplace=True)
            latest = data.iloc[-1]

            close = float(latest['Close'])
            ema20 = float(latest['EMA20'])
            ema50 = float(latest['EMA50'])
            rsi = float(latest['RSI'])
            volume = float(latest['Volume'])
            avg_volume = float(latest['AvgVolume'])

            high_20 = float(data['High'].rolling(20).max().iloc[-1])

            if (
                close > ema50 and
                ema20 > ema50 and
                volume > avg_volume and
                50 < rsi < 70 and
                close >= 0.93 * high_20
            ):
                entry = round(close, 2)
                stoploss = round(entry * 0.97, 2)
                risk = entry - stoploss

                if risk <= 0:
                    continue

                position_size = int(risk_per_trade / risk)
                target = round(entry + (risk * 2), 2)

                results.append({
                    "Stock": stock,
                    "Entry": entry,
                    "Stoploss": stoploss,
                    "Target": target,
                    "Position Size": position_size
                })

        except Exception as e:
            continue

else:
    print("📉 Market Trend: NOT BULLISH — No aggressive swing trades today")

# ---------------------------
# OUTPUT
# ---------------------------

if results:
    print("\n🔥 Top Swing Setups:\n")
    for r in results:
        print(r)
else:
    print("\n⚠️ No strong swing setups today.")
