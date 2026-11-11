"""
Market Context Agent — fetches broader market context (indices, VIX, FII/DII, breadth).
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Optional
from datetime import datetime


class MarketContextAgent:
    def __init__(self, config: dict):
        self.config = config
        self.indices = config.get('watchlist', {}).get('indices', ['^NSEI', '^BSESN'])

    def fetch(self) -> Dict:
        context = {}
        context['timestamp'] = datetime.now().isoformat()

        # Fetch major indices
        for symbol in self.indices:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='5d')
                info = ticker.info or {}
                if not hist.empty:
                    context[symbol] = {
                        'last_price': round(float(hist['Close'].iloc[-1]), 2),
                        'change_pct': round(
                            (hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100, 2
                        ),
                        '52w_high': info.get('fiftyTwoWeekHigh'),
                        '52w_low': info.get('fiftyTwoWeekLow'),
                    }
            except Exception as e:
                context[symbol] = {'error': str(e)}

        return context

    def summary(self, context: Dict) -> str:
        lines = ['[Market Context]']
        for key, val in context.items():
            if key == 'timestamp':
                continue
            if isinstance(val, dict) and 'error' not in val:
                lines.append(f"  {key}: {val.get('last_price')} ({val.get('change_pct', 0):+.2f}%)")
            elif isinstance(val, dict) and 'error' in val:
                lines.append(f"  {key}: ERROR - {val['error']}")
        return '\n'.join(lines)
