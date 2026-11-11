#!/usr/bin/env python3
"""
ML Forecasting with regime detection and fat-tailed distributions.
Outputs JSON with forecast paths, confidence intervals, and reliability score.
"""
import json
import sys
import numpy as np
import pandas as pd
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def detect_regime(returns, window=30):
    """Detect market regime based on volatility."""
    if len(returns) < window:
        return 'unknown'
    vol = returns.rolling(window).std().iloc[-1]
    vol_history = returns.rolling(window).std()
    vol_percentile = (vol_history < vol).sum() / len(vol_history.dropna())
    if vol_percentile > 0.8:
        return 'high_volatility'
    elif vol_percentile < 0.2:
        return 'low_volatility'
    else:
        return 'normal'

def main(historical_data_json, forecast_days=7):
    try:
        # Parse historical data
        data = json.loads(historical_data_json) if isinstance(historical_data_json, str) else historical_data_json
        if 'historical_data' not in data:
            raise ValueError("Invalid historical data format")
        
        hist = data['historical_data']
        close_prices = np.array(hist['close'])
        returns = np.diff(np.log(close_prices))
        
        # Detect current regime
        regime = detect_regime(pd.Series(returns))
        
        # Calculate parameters based on regime
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Adjust for regime: increase volatility in high_volatility regime
        if regime == 'high_volatility':
            sigma = sigma * 1.5
        elif regime == 'low_volatility':
            sigma = sigma * 0.8
        
        # Use Student's t-distribution for fat tails (degrees of freedom estimated from data)
        # Estimate degrees of freedom using method of moments (simplified)
        excess_kurtosis = stats.kurtosis(returns, fisher=True)  # excess kurtosis
        if excess_kurtosis > 0:
            # Estimate df for t-distribution: df = 6 / excess_kurtosis + 4
            df = max(3, 6 / excess_kurtosis + 4)
        else:
            df = 30  # close to normal
        
        # Monte Carlo simulation
        n_simulations = 1000
        forecast_paths = np.zeros((n_simulations, forecast_days))
        last_price = close_prices[-1]
        
        for i in range(n_simulations):
            # Generate t-distributed returns
            t_returns = np.random.standard_t(df, forecast_days) * sigma / np.sqrt(df/(df-2)) + mu
            price_path = last_price * np.exp(np.cumsum(t_returns))
            forecast_paths[i, :] = price_path
        
        # Calculate statistics
        mean_forecast = np.mean(forecast_paths, axis=0)
        median_forecast = np.median(forecast_paths, axis=0)
        percentiles = {
            '5': np.percentile(forecast_paths, 5, axis=0).tolist(),
            '25': np.percentile(forecast_paths, 25, axis=0).tolist(),
            '75': np.percentile(forecast_paths, 75, axis=0).tolist(),
            '95': np.percentile(forecast_paths, 95, axis=0).tolist()
        }
        
        # Backtest accuracy (simplified: compare last 30 days forecast vs actual)
        # We'll do a simple walk-forward for the last 30 days if enough data
        backtest_accuracy = None
        forecast_reliability_score = 0.5  # default
        if len(close_prices) > 30 + forecast_days:
            errors = []
            for i in range(30):
                train_end = -(30 - i)
                test_start = train_end
                test_end = test_start + forecast_days
                if test_end <= 0:
                    train = close_prices[:train_end]
                    test = close_prices[test_start:test_end]
                else:
                    train = close_prices[:train_end]
                    test = close_prices[test_start:]
                if len(test) < forecast_days:
                    continue
                # Simulate forecast from train
                train_returns = np.diff(np.log(train))
                mu_train = np.mean(train_returns)
                sigma_train = np.std(train_returns)
                # Simple normal forecast for backtest
                simulated_returns = np.random.normal(mu_train, sigma_train, forecast_days)
                forecast_price = train[-1] * np.exp(np.cumsum(simulated_returns))
                actual_price = test
                error = np.mean(np.abs(forecast_price - actual_price) / actual_price)
                errors.append(error)
            if errors:
                avg_error = np.mean(errors)
                # Convert error to a reliability score (0-1, higher is better)
                forecast_reliability_score = max(0, min(1, 1 - avg_error * 10))  # scale factor
        
        # Prepare result
        result = {
            'ticker': data.get('ticker', 'UNKNOWN'),
            'forecast_horizon_days': forecast_days,
            'regime': regime,
            'distribution_assumption': f'Student_t_df_{df:.2f}',
            'parameters': {
                'historical_mean_return': float(mu),
                'historical_volatility': float(sigma),
                'adjusted_for_regime': regime != 'normal'
            },
            'forecast': {
                'mean': mean_forecast.tolist(),
                'median': median_forecast.tolist(),
                'percentiles': percentiles,
                'simulation_count': n_simulations
            },
            'forecast_reliability_score': float(forecast_reliability_score),
            'backtest_note': 'Backtest accuracy based on last 30 days walk-forward forecast' if backtest_accuracy is not None else 'Insufficient data for backtest',
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        return json.dumps(result)
    
    except Exception as e:
        print(f"Error in ml_forecast: {e}", file=sys.stderr)
        # Return a minimal valid JSON
        error_result = {
            'error': str(e),
            'timestamp': pd.Timestamp.now().isoformat()
        }
        return json.dumps(error_result)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ml_forecast.py <historical_data_json> [forecast_days]")
        sys.exit(1)
    
    historical_data_json = sys.argv[1]
    forecast_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(main(historical_data_json, forecast_days))