import yfinance as yf
import pandas as pd
import logging
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

risk_per_trade = 200
today = str(datetime.date.today())

# =====================================
# FETCH NIFTY 200 STOCKS DYNAMICALLY
# =====================================
def get_nifty200_stocks():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    try:
        df = pd.read_csv(url)
        symbols = df["Symbol"].tolist()
        return [symbol + ".NS" for symbol in symbols]
    except:
        return []

stocks = get_nifty200_stocks()

if not stocks:
    print("Failed to fetch NIFTY 200 list.")
    exit()


# =====================================
# MARKET TREND FILTER (NIFTY)
# =====================================
def market_trend_ok():
    nifty = yf.download("^NSEI", period="4mo", interval="1d", auto_adjust=True, progress=False)

    if nifty.empty:
        return False

    nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
    nifty['EMA50'] = nifty['Close'].ewm(span=50).mean()
    nifty.dropna(inplace=True)

    latest = nifty.iloc[-1]

    return float(latest['Close']) > float(latest['EMA50']) and float(latest['EMA20']) > float(latest['EMA50'])


# =====================================
# AUTO UPDATE OPEN TRADES
# =====================================
def update_open_trades(sheet):
    records = sheet.get_all_records()

    for idx, row in enumerate(records):
        if row["Trade Status"] == "OPEN":

            try:
                stock = row["Stock"]
                entry = float(row["Entry"])
                stoploss = float(row["Stoploss"])
                target = float(row["Target"])
                position_size = float(row["Position Size"])

                data = yf.download(stock, period="5d", interval="1d", auto_adjust=True, progress=False)

                if data.empty:
                    continue

                latest = data.iloc[-1]
                high = float(latest["High"])
                low = float(latest["Low"])

                sheet_row = idx + 2  # header offset

                if high >= target:
                    pnl = round((target - entry) * position_size, 2)
                    sheet.update(f"H{sheet_row}", "WIN")
                    sheet.update(f"I{sheet_row}", pnl)
                    sheet.update(f"J{sheet_row}", target)

                elif low <= stoploss:
                    pnl = round((stoploss - entry) * position_size, 2)
                    sheet.update(f"H{sheet_row}", "LOSS")
                    sheet.update(f"I{sheet_row}", pnl)
                    sheet.update(f"J{sheet_row}", stoploss)

            except:
                continue


# =====================================
# SCAN FOR NEW TRADES
# =====================================
results = []
market_bullish = market_trend_ok()

if market_bullish:

    for stock in stocks:
        try:
            data = yf.download(stock, period="4mo", interval="1d", auto_adjust=True, progress=False)

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

            # Breakout condition
            if close > ema50 and ema20 > ema50 and close >= 0.95 * high_20:

                entry = round(close, 2)
                stoploss = round(entry * 0.97, 2)
                risk = entry - stoploss

                if risk <= 0:
                    continue

                position_size = int(risk_per_trade / risk)
                target = round(entry + (risk * 2), 2)

                results.append([
                    stock,
                    entry,
                    stoploss,
                    target,
                    position_size
                ])

        except:
            continue


# =====================================
# GOOGLE SHEET CONNECTION
# =====================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Swing Scanner Results").sheet1

# Update open trades first
update_open_trades(sheet)

# =====================================
# SAVE NEW TRADES
# =====================================
market_status = "BULLISH" if market_bullish else "NOT BULLISH"

if results:
    for trade in results:
        sheet.append_row([
            today,          # Date
            market_status,  # Market Status
            trade[0],       # Stock
            trade[1],       # Entry
            trade[2],       # Stoploss
            trade[3],       # Target
            trade[4],       # Position Size
            "OPEN",         # Trade Status
            "",             # P&L
            ""              # Exit Price
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
        "",
        ""
    ])
    print("No trade day recorded.")
