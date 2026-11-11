#!/usr/bin/env python3
"""
Distill Forecast & Stop-Loss Cluster Analysis
Clusters Monte Carlo forecast paths into Bull/Bear/Neutral archetypes and calculates dynamic stop-losses.
Outputs JSON with archetype probabilities, expected returns, and stop-loss levels.
"""
import json
import sys
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

def main(historical_data_json, forecast_json, ticker):
    try:
        # Parse inputs
        hist_data = json.loads(historical_data_json) if isinstance(historical_data_json, str) else historical_data_json
        forecast_data = json.loads(forecast_json) if isinstance(forecast_json, str) else forecast_json
        
        # Extract forecast paths (we need the simulations, but in ml_forecast we only saved statistics)
        # We'll adjust: in a real implementation, ml_forecast would return the simulations or we would recalculate.
        # For this script, we'll assume we can get the simulations from the forecast data or we need to change ml_forecast.
        # Since we changed ml_forecast to not return simulations, we have two options:
        # 1. Change ml_forecast to return simulations (but that could be large)
        # 2. Recalculate the simulations in this script (which is inefficient but okay for now)
        # We'll do option 2 for simplicity in this example, but note that in production we might want to save the simulations.
        
        # Instead, let's change the approach: we'll have ml_forecast return the simulations in a separate file or we'll recalculate here.
        # We'll recalculate the same way as in ml_forecast to get the paths.
        
        # However, to avoid duplicating the model, we'll assume that the forecast data includes the simulations or we can approximate.
        # Given the complexity, we'll create a simplified version that uses the forecast statistics to approximate the archetypes.
        # Alternatively, we can change ml_forecast to return the simulations (as a list of lists) but that might be too big for JSON.
        # We'll compromise: we'll return the simulations as a list of lists but limit the number of simulations for the distillation step.
        
        # Let's adjust ml_forecast to return the simulations (we'll do that in a separate step, but for now we'll note).
        # Since we cannot change ml_forecast in this step without breaking the orchestrator, we'll assume that the forecast data
        # we got from ml_forecast does not have the simulations. Therefore, we must recalculate.
        
        # We'll recalculate the same way as in ml_forecast to get the paths for clustering.
        
        # Get historical data
        hist = hist_data['historical_data']
        close_prices = np.array(hist['close'])
        returns = np.diff(np.log(close_prices))
        
        # Get forecast parameters from forecast_data
        mu = forecast_data['parameters']['historical_mean_return']
        sigma = forecast_data['parameters']['historical_volatility']
        regime = forecast_data.get('regime', 'normal')
        df = float(forecast_data['distribution_assumption'].split('_')[-1])  # extract df from 'Student_t_df_X.XX'
        
        # Adjust sigma for regime (same as in ml_forecast)
        if regime == 'high_volatility':
            sigma = sigma * 1.5
        elif regime == 'low_volatility':
            sigma = sigma * 0.8
        
        # Number of simulations for clustering (we can use a subset for speed)
        n_simulations_for_clustering = 500
        forecast_days = forecast_data['forecast_horizon_days']
        last_price = close_prices[-1]
        
        # Generate t-distributed returns for clustering
        np.random.seed(42)  # for reproducibility
        t_returns = np.random.standard_t(df, (n_simulations_for_clustering, forecast_days)) * sigma / np.sqrt(df/(df-2)) + mu
        price_paths = last_price * np.exp(np.cumsum(t_returns, axis=1))
        
        # We'll cluster based on the final price and the path characteristics (e.g., volatility, trend)
        # Features: final price, max drawdown, Sharpe ratio (simplified), etc.
        features = []
        for path in price_paths:
            # Calculate features for this path
            final_price = path[-1]
            returns_path = np.diff(np.log(path))
            # Avoid division by zero
            vol_path = np.std(returns_path) if len(returns_path) > 1 else 0
            sharpe = (np.mean(returns_path) / vol_path) if vol_path != 0 else 0
            # Max drawdown
            roll_max = np.maximum.accumulate(path)
            drawdown = (roll_max - path) / roll_max
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
            
            features.append([final_price, vol_path, sharpe, max_drawdown])
        
        features = np.array(features)
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Cluster into 3 archetypes: Bull, Bear, Neutral
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Identify which cluster is which by the average final price
        cluster_final_prices = []
        for i in range(3):
            mask = (clusters == i)
            if np.any(mask):
                avg_final_price = np.mean(features[mask, 0])  # final price is the first feature
                cluster_final_prices.append((i, avg_final_price))
            else:
                cluster_final_prices.append((i, 0))
        
        # Sort by average final price: bear (lowest), neutral, bull (highest)
        cluster_final_prices.sort(key=lambda x: x[1])
        bear_cluster_id, neutral_cluster_id, bull_cluster_id = [x[0] for x in cluster_final_prices]
        
        # Calculate statistics for each archetype
        archetypes = {}
        for cluster_id, name in [(bear_cluster_id, 'Bear'), (neutral_cluster_id, 'Neutral'), (bull_cluster_id, 'Bull')]:
            mask = (clusters == cluster_id)
            if np.any(mask):
                # Probability of this archetype
                probability = np.sum(mask) / len(mask)
                # Average final price and return
                avg_final_price = np.mean(features[mask, 0])
                avg_return = (avg_final_price / last_price) - 1
                # Average Sharpe and max drawdown for the archetype
                avg_sharpe = np.mean(features[mask, 2])
                avg_max_drawdown = np.mean(features[mask, 3])
                
                # Dynamic stop-loss: we set it as a multiple of the average volatility (ATR-like) or a fixed percentage below the entry.
                # We'll use a simple approach: stop-loss = entry price * (1 - 2 * average volatility of the archetype)
                # But note: we don't have the entry price in the forecast? We are forecasting from the current price.
                # We'll set the stop-loss relative to the current price: e.g., if the archetype is bullish, we set a stop-loss below the current price.
                # Actually, we want a stop-loss for a trade based on the archetype.
                # We'll define: if we enter a long position, we set a stop-loss at a level that invalidates the bullish thesis.
                # We'll use the average maximum drawdown from the historical data or from the archetype paths.
                # For simplicity, we'll set the stop-loss as: current_price * (1 - 2 * avg_max_drawdown) for long positions.
                # But note: this is just an example.
                stop_loss_multiplier = 2.0  # example: 2 times the average max drawdown
                stop_loss_price = last_price * (1 - stop_loss_multiplier * avg_max_drawdown)
                # Ensure stop-loss is positive and below current price for long
                if stop_loss_price >= last_price:
                    stop_loss_price = last_price * 0.9  # fallback: 10% below
                
                archetypes[name.lower()] = {
                    'probability': float(probability),
                    'expected_final_price': float(avg_final_price),
                    'expected_return': float(avg_return),
                    'avg_sharpe_ratio': float(avg_sharpe),
                    'avg_max_drawdown': float(avg_max_drawdown),
                    'stop_loss_price': float(stop_loss_price),
                    'stop_loss_pct': float((stop_loss_price / last_price - 1) * 100)  # negative for long stop-loss
                }
            else:
                archetypes[name.lower()] = {
                    'probability': 0.0,
                    'expected_final_price': float(last_price),
                    'expected_return': 0.0,
                    'avg_sharpe_ratio': 0.0,
                    'avg_max_drawdown': 0.0,
                    'stop_loss_price': float(last_price),
                    'stop_loss_pct': 0.0
                }
        
        # Also calculate the overall forecast statistics (from the full set of simulations we didn't save)
        # We'll use the same price_paths we generated for clustering (but note we used a subset)
        # For consistency, we should use the same set as in ml_forecast, but we'll note the limitation.
        # We'll calculate the mean, median, percentiles from the price_paths we have (the subset for clustering)
        mean_forecast = np.mean(price_paths, axis=0)
        median_forecast = np.median(price_paths, axis=0)
        percentiles = {
            '5': np.percentile(price_paths, 5, axis=0).tolist(),
            '25': np.percentile(price_paths, 25, axis=0).tolist(),
            '75': np.percentile(price_paths, 75, axis=0).tolist(),
            '95': np.percentile(price_paths, 95, axis=0).tolist()
        }
        
        # Prepare result
        result = {
            'ticker': ticker,
            'current_price': float(last_price),
            'regime': regime,
            'archetypes': archetypes,
            'forecast_summary': {
                'mean': mean_forecast.tolist(),
                'median': median_forecast.tolist(),
                'percentiles': percentiles,
                'simulation_count_used_for_clustering': n_simulations_for_clustering
            },
            'note': 'Archetypes identified via K-means clustering on forecast path features (final price, volatility, Sharpe ratio, max drawdown). Stop-losses are dynamic based on archetype characteristics.',
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        return json.dumps(result)
    
    except Exception as e:
        print(f"Error in distill_forecast_sl: {e}", file=sys.stderr)
        # Return a minimal valid JSON
        error_result = {
            'error': str(e),
            'timestamp': pd.Timestamp.now().isoformat()
        }
        return json.dumps(error_result)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python distill_forecast_sl.py <historical_data_json> <forecast_json> <ticker>")
        sys.exit(1)
    
    historical_data_json = sys.argv[1]
    forecast_json = sys.argv[2]
    ticker = sys.argv[3]
    print(main(historical_data_json, forecast_json, ticker))