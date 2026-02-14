import yfinance as yf
import pandas as pd
import numpy as np
import logging
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

risk_per_trade = 200
today = str(datetime.date.today())

def market_trend_ok():
    nifty = yf.download("^NSEI", period="3mo", interval="1d", auto_adjust=True, progress=False)

    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)

    nifty = nifty[['Close']]
    nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
    nifty['EMA50'] = nifty['Close'].ewm(span=50).mean()
    nifty.dropna(inplace=True)

    latest = nifty.iloc[-1]

    return float(latest['Close']) > float(latest['EMA50']) and float(latest['EMA20']) > float(latest['EMA50'])

stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
    "ICICIBANK.NS","SBIN.NS","LT.NS","ITC.NS"
]

results = []

market_bullish = market_trend_ok()

if market_bullish:
    for stock in stocks:
        try:
            data = yf.download(stock, period="3mo", interval="1d", auto_adjust=True, progress=False)

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if data.empty or len(data) < 60:
                continue

            data['EMA20'] = data['Close'].ewm(span=20).mean()
            data['EMA50'] = data['Close'].ewm(span=50).mean()
            data.dropna(inplace=True)

            latest = data.iloc[-1]
            high_20 = float(data['High'].rolling(20).max().iloc[-1])

            close = float(latest['Close'])
            ema20 = float(latest['EMA20'])
            ema50 = float(latest['EMA50'])

            if close > ema50 and ema20 > ema50 and close >= 0.93 * high_20:

                entry = round(close, 2)
                stoploss = round(entry * 0.97, 2)
                risk = entry - stoploss

                if risk <= 0:
                    continue

                position_size = int(risk_per_trade / risk)
                target = round(entry + (risk * 2), 2)

                results.append([
                    today,
                    stock,
                    entry,
                    stoploss,
                    target,
                    position_size
                ])

        except:
            continue

# Google Sheet Save
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Swing Scanner Results").sheet1

if market_bullish:
    market_status = "BULLISH"
else:
    market_status = "NOT BULLISH"

if results:
    for trade in results:
        sheet.append_row([
            today,             # Date
            market_status,     # Market Status
            trade[1],          # Stock
            trade[2],          # Entry
            trade[3],          # Stoploss
            trade[4],          # Target
            trade[5],          # Position Size
            "OPEN",            # Trade Status
            ""                 # P&L (empty initially)
        ])
    print("Trades recorded.")
else:
    sheet.append_row([
        today,
        market_status,
        "NO TRADE",
        "-",
        "-",
        "-",
        "-",
        "NO TRADE",
        ""
    ])
    print("No trade day recorded.")
