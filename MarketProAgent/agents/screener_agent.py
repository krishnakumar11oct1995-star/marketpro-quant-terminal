"""
Screener Agent — scans NSE 500 (or user-defined universe) for pattern-based signals.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


class ScreenerAgent:
    def __init__(self, config: dict):
        self.config = config
        self.watchlist = config.get('watchlist', {}).get('tickers', [])
        self.screeners = config.get('screening', {})
        self.universe_file = self.screeners.get('nse500_list_csv', '')

    def scan(self) -> List[Dict]:
        results = []
        for ticker in self.watchlist:
            try:
                hist = yf.Ticker(ticker).history(period='3mo')
                if hist.empty:
                    continue
                signals = self._scan_patterns(hist, ticker)
                if signals:
                    results.append(signals)
            except Exception as e:
                print(f"  Screener error {ticker}: {e}")
        return results

    def _scan_patterns(self, df: pd.DataFrame, ticker: str) -> Optional[Dict]:
        signals = {'ticker': ticker, 'patterns': [], 'score': 0}
        close = df['Close']
        volume = df['Volume']
        high = df['High']
        low = df['Low']

        # Volume breakout (last 2 days)
        avg_vol = volume.rolling(20).mean()
        if len(volume) >= 22:
            if volume.iloc[-1] > avg_vol.iloc[-1] * 1.5:
                signals['patterns'].append('volume breakout')
                signals['score'] += 1

        # 52-week high proximity
        if len(close) >= 252:
            high_52w = close.rolling(252).max()
            if close.iloc[-1] >= high_52w.iloc[-1] * 0.95:
                signals['patterns'].append('near 52w high')
                signals['score'] += 1
        else:
            high_3m = close.max()
            if close.iloc[-1] >= high_3m * 0.95:
                signals['patterns'].append('near 3m high')
                signals['score'] += 1

        # RSI oversold/overbought
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_g = gain.rolling(14).mean()
        avg_l = loss.rolling(14).mean()
        rs = avg_g / avg_l.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        if len(rsi) >= 15:
            if rsi.iloc[-1] < 30:
                signals['patterns'].append('rsi oversold')
                signals['score'] += 1
            elif rsi.iloc[-1] > 70:
                signals['patterns'].append('rsi overbought')
                signals['score'] -= 1

        # Bullish engulfing
        for i in range(1, min(6, len(df))):
            p_close = close.iloc[-i - 1]
            p_open = df['Open'].iloc[-i - 1]
            c_close = close.iloc[-i]
            c_open = df['Open'].iloc[-i]
            if p_close < p_open and c_close > c_open and c_open <= p_close and c_close >= p_open:
                signals['patterns'].append('bullish engulfing')
                signals['score'] += 2
                break

        if not signals['patterns']:
            return None

        signals['last_price'] = round(float(close.iloc[-1]), 2)
        return signals
