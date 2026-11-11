#!/usr/bin/env python3
"""
Advanced ML Forecasting Module.
XGBoost, RandomForest, ensemble, walk-forward cross-validation, feature engineering.
"""
import json
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Optional imports with graceful fallbacks
try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.metrics import accuracy_score, mean_absolute_error
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def engineer_features(df):
    """Build a feature matrix from OHLCV data."""
    features = pd.DataFrame(index=df.index)

    # Returns
    features['return_1d'] = df['Close'].pct_change()
    features['return_5d'] = df['Close'].pct_change(5)
    features['return_21d'] = df['Close'].pct_change(21)
    features['log_return_1d'] = np.log(df['Close'] / df['Close'].shift(1))

    # Volatility
    features['volatility_5d'] = features['return_1d'].rolling(5).std()
    features['volatility_21d'] = features['return_1d'].rolling(21).std()

    # Volume
    features['volume_ratio'] = df['Volume'] / df['Volume'].rolling(21).mean()
    features['volume_change'] = df['Volume'].pct_change()

    # Price vs moving averages
    features['sma_5'] = df['Close'] / df['Close'].rolling(5).mean() - 1
    features['sma_21'] = df['Close'] / df['Close'].rolling(21).mean() - 1
    features['sma_50'] = df['Close'] / df['Close'].rolling(50).mean() - 1

    # RSI (14-day)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    features['rsi_14'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    features['macd'] = ema12 - ema26
    features['macd_signal'] = features['macd'].ewm(span=9).mean()
    features['macd_hist'] = features['macd'] - features['macd_signal']

    # ATR (14-day)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift(1))
    low_close = np.abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    features['atr_14'] = tr.rolling(14).mean()

    # Bollinger Bands %B
    sma_20 = df['Close'].rolling(20).mean()
    std_20 = df['Close'].rolling(20).std()
    features['bb_upper'] = (df['Close'] - (sma_20 + 2 * std_20)) / df['Close']
    features['bb_lower'] = (df['Close'] - (sma_20 - 2 * std_20)) / df['Close']
    features['bb_width'] = (2 * std_20) / sma_20

    # Target: next day direction (1 if up, 0 if down)
    features['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    features['target_reg'] = df['Close'].shift(-1) / df['Close'] - 1  # continuous return

    return features.dropna()


# ---------------------------------------------------------------------------
# Walk-Forward Cross-Validation
# ---------------------------------------------------------------------------

def walk_forward_cv(df_features, model_class, model_params, n_splits=5, min_train=100):
    """Expanding window walk-forward validation."""
    n = len(df_features)
    if n < min_train + n_splits:
        return None, []

    split_size = (n - min_train) // n_splits
    predictions = []
    actuals = []
    metrics = []

    for i in range(n_splits):
        train_end = min_train + i * split_size
        test_end = train_end + split_size

        train = df_features.iloc[:train_end]
        test = df_features.iloc[train_end:test_end]

        if len(test) < 5:
            break

        X_train = train.drop(['target', 'target_reg'], axis=1)
        y_train = train['target']
        X_test = test.drop(['target', 'target_reg'], axis=1)
        y_test = test['target']

        try:
            model = model_class(**model_params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            predictions.extend(y_pred.tolist())
            actuals.extend(y_test.tolist())
            metrics.append({
                'fold': i + 1,
                'train_start': str(df_features.index[0]),
                'train_end': str(df_features.index[train_end - 1]),
                'test_start': str(df_features.index[train_end]),
                'test_end': str(df_features.index[test_end - 1]),
                'accuracy': float(acc),
                'n_train': len(train),
                'n_test': len(test),
            })
        except Exception as e:
            metrics.append({
                'fold': i + 1,
                'error': str(e)
            })
            continue

    if not metrics:
        return None, []

    overall_acc = accuracy_score(actuals, predictions) if len(set(predictions)) > 1 else 0.5
    return overall_acc, metrics


# ---------------------------------------------------------------------------
# Ensemble Predictor
# ---------------------------------------------------------------------------

class EnsemblePredictor:
    """Ensemble of XGBoost, RandomForest, and naive (momentum)."""

    def __init__(self):
        self.models = {}

    def fit(self, X_train, y_train):
        if HAS_XGB:
            try:
                model = xgb.XGBClassifier(
                    n_estimators=200, max_depth=5, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8, random_state=42,
                    eval_metric='logloss', use_label_encoder=False
                )
                model.fit(X_train, y_train)
                self.models['xgboost'] = model
            except Exception:
                pass

        if HAS_SKLEARN:
            try:
                model = RandomForestClassifier(
                    n_estimators=200, max_depth=6, min_samples_leaf=5,
                    random_state=42, n_jobs=-1
                )
                model.fit(X_train, y_train)
                self.models['random_forest'] = model
            except Exception:
                pass

        # Naive momentum classifier
        self.models['naive'] = None  # will be used in predict

    def predict_proba(self, X_df):
        """Return ensemble probability of UP (class 1)."""
        probs = []

        if 'xgboost' in self.models:
            try:
                p = self.models['xgboost'].predict_proba(X_df)
                probs.append(p[:, 1])
            except Exception:
                pass

        if 'random_forest' in self.models:
            try:
                p = self.models['random_forest'].predict_proba(X_df)
                probs.append(p[:, 1])
            except Exception:
                pass

        # Naive: recent return direction as probability
        recent_return = X_df['return_1d'].values
        naive_prob = np.clip((recent_return * 5) + 0.5, 0, 1)
        probs.append(naive_prob)

        if not probs:
            return np.full(len(X_df), 0.5)

        return np.mean(probs, axis=0)

    def predict(self, X_df):
        probs = self.predict_proba(X_df)
        return (probs >= 0.5).astype(int)

    def feature_importance(self, top_n=10):
        """Aggregate feature importance across tree-based models."""
        importances = {}
        for name, model in self.models.items():
            if model is None:
                continue
            if hasattr(model, 'feature_importances_'):
                for i, imp in enumerate(model.feature_importances_):
                    importances[name] = importances.get(name, []) + [float(imp)]
        return importances


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(data, forecast_days=7):
    try:
        hist_data = json.loads(data) if isinstance(data, str) else data
        hist = hist_data.get('historical_data', {})
        df = pd.DataFrame({
            'Date': pd.to_datetime(hist['dates']),
            'Open': hist['open'], 'High': hist['high'],
            'Low': hist['low'], 'Close': hist['close'],
            'Volume': hist['volume']
        }).set_index('Date')

        features = engineer_features(df)
        if features.empty:
            raise ValueError('Not enough data for feature engineering')

        ticker = hist_data.get('ticker', 'UNKNOWN')
        last_price = float(df['Close'].iloc[-1])

        # Split into train/test (last 20% as test, rest as train)
        split = int(len(features) * 0.8)
        X = features.drop(['target', 'target_reg'], axis=1)
        y = features['target']
        y_reg = features['target_reg']

        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # Walk-forward CV
        ensemble = EnsemblePredictor()
        ensemble.fit(X_train, y_train)

        wf_accuracy, wf_folds = walk_forward_cv(features, RandomForestClassifier,
                                                 {'n_estimators': 100, 'random_state': 42, 'n_jobs': -1},
                                                 n_splits=min(5, len(features) // 50))

        # Test set accuracy
        test_pred = ensemble.predict(X_test)
        test_accuracy = float(accuracy_score(y_test, test_pred)) if len(set(test_pred)) > 1 else 0.5

        # Direction prediction for next N days (use most recent features)
        recent_features = X.iloc[-1:]
        # Simple heuristic for multi-day: use the ensemble probability as a signal strength
        up_prob = float(ensemble.predict_proba(recent_features)[0])
        # Multi-day price paths using ensemble confidence to adjust Monte Carlo parameters
        # Confidence-weighted return: higher confidence = more extreme forecast
        confidence = abs(up_prob - 0.5) * 2  # 0 to 1

        # Generate forecast path: mean reversion with ensemble bias
        returns = np.log(df['Close'] / df['Close'].shift(1)).dropna()
        mu = float(returns.mean())
        sigma = float(returns.std())
        # Add ensemble bias to drift
        bias = (up_prob - 0.5) * sigma * 2
        adjusted_mu = mu + bias

        n_sim = 1000
        np.random.seed(42)
        sim_paths = np.zeros((n_sim, forecast_days))
        for i in range(n_sim):
            noise = np.random.normal(adjusted_mu, sigma, forecast_days)
            path = last_price * np.exp(np.cumsum(noise))
            sim_paths[i, :] = path

        mean_path = np.mean(sim_paths, axis=0)
        p5 = np.percentile(sim_paths, 5, axis=0)
        p95 = np.percentile(sim_paths, 95, axis=0)

        # Feature importance
        importances = ensemble.feature_importance()
        # Aggregate across models and get top features
        agg_importance = {}
        for model_name, imps in importances.items():
            for feat, imp in zip(X.columns, imps):
                agg_importance[feat] = agg_importance.get(feat, 0) + imp
        sorted_imp = sorted(agg_importance.items(), key=lambda x: -x[1])[:10]
        top_features = [{'feature': f, 'importance': round(v, 4)} for f, v in sorted_imp]

        result = {
            'ticker': ticker,
            'model': 'ensemble_xgb_rf_naive',
            'ensemble_components': {
                'xgboost': HAS_XGB and 'xgboost' in ensemble.models,
                'random_forest': HAS_SKLEARN and 'random_forest' in ensemble.models,
                'naive_momentum': True
            },
            'forecast_horizon_days': forecast_days,
            'current_price': last_price,
            'predicted_direction': 'UP' if up_prob >= 0.5 else 'DOWN',
            'up_probability': round(up_prob, 4),
            'confidence_score': round(confidence, 4),
            'test_accuracy': round(test_accuracy, 4),
            'walk_forward_folds': wf_folds or [],
            'walk_forward_avg_accuracy': round(float(np.mean([f['accuracy'] for f in wf_folds])), 4) if wf_folds else None,
            'forecast': {
                'mean': [round(float(x), 2) for x in mean_path],
                'percentiles': {
                    '5': [round(float(x), 2) for x in p5],
                    '95': [round(float(x), 2) for x in p95]
                }
            },
            'top_features': top_features,
            'feature_count': X.shape[1],
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'timestamp': pd.Timestamp.now().isoformat()
        }

        return json.dumps(result)

    except Exception as e:
        print(f"Error in ml_advanced: {e}", file=sys.stderr)
        return json.dumps({'error': str(e), 'timestamp': pd.Timestamp.now().isoformat()})

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ml_advanced.py <data_json> [forecast_days]")
        sys.exit(1)
    data = sys.argv[1]
    forecast_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(main(data, forecast_days))
