#!/usr/bin/env python3
"""
Fetch historical and real-time data for a given ticker.
"""
import json
import sys
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def main(ticker, days=365):
    try:
        # Fetch historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            raise ValueError(f"No historical data found for {ticker}")
        
        # Get real-time quote
        info = stock.info
        current_price = info.get('currentPrice', info.get('regularMarketPrice', hist['Close'].iloc[-1]))
        
        # Prepare data for JSON serialization
        data = {
            'ticker': ticker,
            'historical_data': {
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'open': hist['Open'].tolist(),
                'high': hist['High'].tolist(),
                'low': hist['Low'].tolist(),
                'close': hist['Close'].tolist(),
                'volume': hist['Volume'].tolist()
            },
            'real_time': {
                'current_price': current_price,
                'market_cap': info.get('marketCap'),
                'currency': info.get('currency'),
                'exchange': info.get('exchange'),
                'timestamp': datetime.now().isoformat()
            },
            'metadata': {
                'data_source': 'yfinance',
                'historical_days': days,
                'last_update': datetime.now().isoformat()
            }
        }
        
        return json.dumps(data)
    
    except Exception as e:
        print(f"Error in fetch_data: {e}")
        # Return a minimal valid JSON to avoid breaking the pipeline
        error_data = {
            'ticker': ticker,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(error_data)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fetch_data.py <ticker> [days]")
        sys.exit(1)
    
    ticker = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 365
    print(main(ticker, days))