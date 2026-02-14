import yfinance as yf
import pandas as pd
import numpy as np
import logging
import datetime

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

capital = 10000
risk_per_trade = 200

def market_trend_ok():
    nifty = yf.download("^NSEI", period="3mo", interval="1d", auto_adjust=True, progress=False)
    nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
    nifty['EMA50'] = nifty['Close'].ewm(span=50).mean()
    latest = nifty.iloc[-1]

    return latest['Close'] > latest['EMA50'] and latest['EMA20'] > latest['EMA50']


stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
    "ICICIBANK.NS","SBIN.NS","LT.NS","ITC.NS",
    "BHARTIARTL.NS","AXISBANK.NS","MARUTI.NS",
    "BAJFINANCE.NS","SUNPHARMA.NS","TITAN.NS"
]

results = []

if market_trend_ok():
    print("Market Trend: Bullish ✅")

    for stock in stocks:
        try:
            data = yf.download(stock, period="3mo", interval="1d", auto_adjust=True, progress=False)

            if data.empty or len(data) < 60:
                continue

            data['EMA20'] = data['Close'].ewm(span=20).mean()
            data['EMA50'] = data['Close'].ewm(span=50).mean()
            data['AvgVolume'] = data['Volume'].rolling(20).mean()

            delta = data['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            rs = avg_gain / avg_loss
            data['RSI'] = 100 - (100 / (1 + rs))

            data.dropna(inplace=True)
            latest = data.iloc[-1]
            high_20 = data['High'].rolling(20).max().iloc[-1]

            if (latest['Close'] > latest['EMA50'] and
                latest['EMA20'] > latest['EMA50'] and
                latest['Volume'] > latest['AvgVolume'] and
                50 < latest['RSI'] < 70 and
                latest['Close'] >= 0.93 * high_20):

                entry = round(float(latest['Close']),2)
                stoploss = round(entry * 0.97,2)
                risk = entry - stoploss

                if risk <= 0:
                    continue

                position_size = int(risk_per_trade / risk)
                target = round(entry + (risk * 2),2)

                results.append({
                    "Stock": stock,
                    "Entry": entry,
                    "Stoploss": stoploss,
                    "Target": target,
                    "Position Size": position_size
                })

        except:
            continue

else:
    print("Market Trend: Not Bullish ❌ Avoid aggressive swing trades.")

if results:
    print("\nTop Swing Setups:\n")
    for r in results:
        print(r)
else:
    print("\nNo strong swing setups today.")

