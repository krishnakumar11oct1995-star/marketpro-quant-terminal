#!/usr/bin/env python3
"""
Adversarial Audit: Compare internal forecast with real analyst consensus.
Fetches analyst targets from multiple sources and returns a comparison.
"""
import json
import sys
import requests
import pandas as pd
from datetime import datetime
import re

def fetch_analyst_targets_yahoo(ticker):
    """Fetch analyst targets from Yahoo Finance."""
    try:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        params = {'modules': 'upgradeDowngradeHistory,financialData,defaultKeyStatistics'}
        response = requests.get(url, params=params)
        data = response.json()
        
        result = data['quoteSummary']['result'][0]
        financial_data = result.get('financialData', {})
        
        target_mean = financial_data.get('targetMeanPrice', {}).get('raw')
        target_high = financial_data.get('targetHighPrice', {}).get('raw')
        target_low = financial_data.get('targetLowPrice', {}).get('raw')
        recommendation = financial_data.get('recommendationMean', {}).get('raw')
        number_of_analysts = financial_data.get('numberOfAnalystOpinions', {}).get('raw')
        
        return {
            'source': 'Yahoo Finance',
            'consensus': target_mean,
            'bull_target': target_high,
            'bear_target': target_low,
            'recommendation_mean': recommendation,  # 1.0 is strong buy, 5.0 is strong sell
            'number_of_analysts': number_of_analysts,
            'timestamp': datetime.now().isoformat(),
            'url': url
        }
    except Exception as e:
        print(f"Warning: Could not fetch Yahoo Finance analyst data: {e}")
        return None

def fetch_analyst_targets_screener(ticker):
    """Fetch analyst targets from Screener.in (for Indian stocks)."""
    # Note: Screener.in does not have a public API, so we scrape (use with caution and respect robots.txt)
    # This is a simplified example; in practice, you would need to handle JavaScript or use an API if available.
    try:
        # Extract the base symbol without .NS or .BO for Screener.in
        base_ticker = ticker.replace('.NS', '').replace('.BO', '')
        url = f"https://www.screener.in/company/{base_ticker}/consolidated/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        # This is a placeholder: actual parsing would be more complex
        # We'll return None to indicate we didn't implement the scraper for brevity
        return None
    except Exception as e:
        print(f"Warning: Could not fetch Screener.in analyst data: {e}")
        return None

def fetch_analyst_targets(ticker):
    """Fetch analyst targets from multiple sources, return the first available."""
    sources = [
        fetch_analyst_targets_yahoo,
        # fetch_analyst_targets_screener,  # Uncomment if implemented
    ]
    
    for source_func in sources:
        try:
            result = source_func(ticker)
            if result and result.get('consensus') is not None:
                return result
        except Exception as e:
            print(f"Warning: Source {source_func.__name__} failed: {e}")
            continue
    
    return None

def main(historical_data_json, forecast_json):
    try:
        # Parse inputs
        hist_data = json.loads(historical_data_json) if isinstance(historical_data_json, str) else historical_data_json
        forecast_data = json.loads(forecast_json) if isinstance(forecast_json, str) else forecast_json
        
        ticker = hist_data.get('ticker', 'UNKNOWN')
        
        # Fetch real analyst targets
        analyst_data = fetch_analyst_targets(ticker)
        
        # Extract forecast price targets (we'll use the mean forecast at the end of the horizon)
        forecast_mean = forecast_data.get('forecast', {}).get('mean', [])
        if forecast_mean:
            # Assuming the forecast is for the next N days, we take the last predicted price
            forecast_target = forecast_mean[-1] if forecast_mean else None
        else:
            forecast_target = None
        
        # Prepare comparison
        if analyst_data:
            consensus = analyst_data.get('consensus')
            bull = analyst_data.get('bull_target')
            bear = analyst_data.get('bear_target')
            
            # Calculate alignment scores (simple absolute difference normalized by price)
            current_price = hist_data.get('real_time', {}).get('current_price')
            if current_price and forecast_target:
                forecast_error = abs(forecast_target - current_price) / current_price
            else:
                forecast_error = None
            
            if current_price and consensus:
                consensus_error = abs(consensus - current_price) / current_price
            else:
                consensus_error = None
            
            # Determine if forecast is within the analyst range
            if bull and bear and forecast_target:
                within_range = bear <= forecast_target <= bull
            else:
                within_range = None
            
            result = {
                'ticker': ticker,
                'analyst_consensus': analyst_data,
                'forecast_target': forecast_target,
                'comparison': {
                    'forecast_vs_consensus': {
                        'forecast_target': forecast_target,
                        'analyst_consensus': consensus,
                        'absolute_difference': abs(forecast_target - consensus) if forecast_target and consensus else None,
                        'percentage_difference': abs(forecast_target - consensus) / consensus * 100 if forecast_target and consensus else None
                    },
                    'forecast_vs_range': {
                        'bull_target': bull,
                        'bear_target': bear,
                        'forecast_within_range': within_range
                    }
                },
                'note': 'Analyst targets fetched from real sources with timestamps and URLs.',
                'timestamp': datetime.now().isoformat()
            }
        else:
            result = {
                'ticker': ticker,
                'analyst_consensus': None,
                'forecast_target': forecast_target,
                'comparison': None,
                'note': 'Analyst target data unavailable from all sources. Using internal forecast only.',
                'timestamp': datetime.now().isoformat()
            }
        
        return json.dumps(result)
    
    except Exception as e:
        print(f"Error in adversarial_audit: {e}", file=sys.stderr)
        error_result = {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(error_result)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python adversarial_audit.py <historical_data_json> <forecast_json>")
        sys.exit(1)
    
    historical_data_json = sys.argv[1]
    forecast_json = sys.argv[2]
    print(main(historical_data_json, forecast_json))