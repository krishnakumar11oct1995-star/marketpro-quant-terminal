"""
Analysis Agent — runs valuation, sentiment, ML forecast, and competitor scan.
Fetches data once, then feeds it to each external script in the expected format.
"""
import subprocess
import sys
import json
import os
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime


class AnalysisAgent:
    def __init__(self, config: dict):
        self.config = config
        self.scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
        self.analysis_config = config.get('analysis', {})

    def _build_data_json(self, ticker: str) -> Optional[str]:
        """Fetch data from yfinance and format as JSON the old scripts expect."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')
            if hist.empty:
                return None
            info = stock.info or {}
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or float(hist['Close'].iloc[-1])
            data = {
                'ticker': ticker,
                'historical_data': {
                    'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                    'open': hist['Open'].tolist(),
                    'high': hist['High'].tolist(),
                    'low': hist['Low'].tolist(),
                    'close': hist['Close'].tolist(),
                    'volume': hist['Volume'].tolist(),
                },
                'real_time': {
                    'current_price': current_price,
                    'market_cap': info.get('marketCap'),
                    'currency': info.get('currency'),
                    'exchange': info.get('exchange'),
                    'timestamp': datetime.now().isoformat(),
                },
                'metadata': {
                    'data_source': 'yfinance',
                    'last_update': datetime.now().isoformat(),
                }
            }
            return json.dumps(data)
        except Exception as e:
            return None

    def _run_script(self, script_name: str, *args) -> dict:
        script_path = os.path.join(self.scripts_dir, script_name)
        if not os.path.exists(script_path):
            return {'error': f'Script not found: {script_path}'}
        try:
            cmd = [sys.executable, script_path] + list(args)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return {'error': result.stderr.strip()}
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {'output': result.stdout.strip()}
        except subprocess.TimeoutExpired:
            return {'error': 'Script timed out'}
        except Exception as e:
            return {'error': str(e)}

    def analyze_ticker(self, ticker: str, analyses: List[str] = None) -> dict:
        if analyses is None:
            analyses = self.analysis_config.get('analyses', ['valuation', 'ml_forecast', 'competitor_scan'])

        results = {'ticker': ticker}

        # Common data JSON needed by most scripts
        data_json = self._build_data_json(ticker)
        if data_json is None:
            for a in analyses:
                results[a] = {'error': f'Could not fetch data for {ticker}'}
            return results

        # Fetch forecast JSON for scripts that need it
        forecast_json = None
        if 'ml_forecast' in analyses or 'distill' in analyses or 'risk' in analyses or 'adversarial_audit' in analyses:
            fc = self._run_script('ml_forecast.py', data_json, '7')
            if 'error' not in fc:
                forecast_json = json.dumps(fc)

        for analysis in analyses:
            if analysis == 'valuation':
                results[analysis] = self._run_script('valuation_engine.py', data_json)
            elif analysis == 'ml_forecast':
                results[analysis] = fc if forecast_json else {'error': 'ML forecast failed'}
            elif analysis == 'ml_advanced':
                results[analysis] = self._run_script('ml_advanced.py', data_json, '7')
            elif analysis == 'sentiment':
                results[analysis] = self._run_script('sentiment_engine.py', data_json)
            elif analysis == 'competitor_scan':
                results[analysis] = self._run_script('competitor_scanner.py', data_json, ticker)
            elif analysis == 'risk':
                if forecast_json:
                    results[analysis] = self._run_script('risk_engine.py', data_json, forecast_json)
                else:
                    results[analysis] = {'error': 'Forecast data required but unavailable'}
            elif analysis == 'distill':
                if forecast_json:
                    results[analysis] = self._run_script('distill_forecast_sl.py', data_json, forecast_json, ticker)
                else:
                    results[analysis] = {'error': 'Forecast data required but unavailable'}
            elif analysis == 'adversarial_audit':
                if forecast_json:
                    results[analysis] = self._run_script('adversarial_audit.py', data_json, forecast_json)
                else:
                    results[analysis] = {'error': 'Forecast data required but unavailable'}

        return results
