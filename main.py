import yfinance as yf
import pandas_ta as ta
import pandas as pd
from backtesting import Strategy, Backtest

def get_data():
    df = yf.download('TCS.NS', period='7d', interval='5m')
    if df.empty:
        print("Data is empty")
        return df

    # Flatten MultiIndex columns if yfinance returns them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df.dropna(inplace=True)

    # Calculate Indicators
    df['EMA_9'] = ta.ema(df['Close'], length=9)
    bb = ta.bbands(df['Close'], length=20, std=2)
    df['BBL'] = bb.iloc[:, 0]  # Lower Bollinger Band

    # VWAP requires a proper index (DatetimeIndex). yfinance usually sets Date/Time as index.
    # Check if index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df['VWAP'] = ta.vwap(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'])

    df.dropna(inplace=True)
    return df


class IntradayStrategy(Strategy):
    def init(self):
        self.hit_bbl = False

    def next(self):
        if len(self.data.Close) < 2:
            return

        current_low = self.data.Low[-1]
        current_bbl = self.data.BBL[-1]

        current_close = self.data.Close[-1]
        current_ema = self.data.EMA_9[-1]

        prev_close = self.data.Close[-2]
        prev_ema = self.data.EMA_9[-2]

        # Check if price hits the lower Bollinger Band
        if current_low <= current_bbl:
            self.hit_bbl = True

        # Buy when price reclaims the 9 EMA
        if self.hit_bbl and current_close > current_ema and prev_close <= prev_ema:
            # 0.5% stop loss and 1.0% take profit
            sl = current_close * 0.995
            tp = current_close * 1.010
            self.buy(sl=sl, tp=tp)

            # Reset the condition
            self.hit_bbl = False

if __name__ == '__main__':
    df = get_data()
    if not df.empty:
        bt = Backtest(df, IntradayStrategy, cash=100000, commission=.0002)
        stats = bt.run()
        print(stats)

        # Print trades to verify
        print("\nTrades:")
        print(stats['_trades'])
