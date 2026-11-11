#!/usr/bin/env python3
"""
Portfolio & Multi-Asset Engine.
Correlation analysis, mean-variance optimization, risk parity, portfolio metrics.
"""
import json
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from scipy.optimize import minimize
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_aligned_prices(tickers, period='1y'):
    """Fetch and align close prices for all tickers."""
    if not HAS_YFINANCE:
        return None, 'yfinance not available'

    data = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period=period)
            if not hist.empty:
                data[t] = hist['Close']
        except Exception as e:
            print(f"Warning: Could not fetch {t}: {e}")

    if not data:
        return None, 'No data fetched for any ticker'

    df = pd.DataFrame(data)
    df = df.dropna()  # align dates
    return df, None


# ---------------------------------------------------------------------------
# Correlation & Covariance
# ---------------------------------------------------------------------------

def compute_correlation(price_df):
    """Compute correlation matrix from aligned prices."""
    returns = price_df.pct_change().dropna()
    return returns.corr(), returns.cov()


# ---------------------------------------------------------------------------
# Mean-Variance Optimization
# ---------------------------------------------------------------------------

def max_sharpe_weights(cov, expected_returns, risk_free_rate=0.065):
    """Maximize Sharpe ratio using scipy optimization."""
    n = len(cov)
    args = (cov, expected_returns, risk_free_rate)

    def neg_sharpe(weights, cov, er, rf):
        port_ret = np.sum(weights * er)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        if port_vol == 0:
            return 0
        return -(port_ret - rf) / port_vol

    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(n))
    x0 = np.array([1 / n] * n)

    result = minimize(neg_sharpe, x0, args=args, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    return result.x if result.success else None


def min_volatility_weights(cov):
    """Minimize portfolio volatility."""
    n = len(cov)

    def portfolio_vol(weights, cov):
        return np.sqrt(np.dot(weights.T, np.dot(cov, weights)))

    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(n))
    x0 = np.array([1 / n] * n)

    result = minimize(portfolio_vol, x0, args=cov, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    return result.x if result.success else None


def risk_parity_weights(cov):
    """Risk parity: equal risk contribution."""
    n = len(cov)

    def risk_contribution(weights, cov):
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        rc = weights * (np.dot(cov, weights)) / port_vol
        return rc

    def risk_parity_obj(weights, cov):
        rc = risk_contribution(weights, cov)
        target = np.mean(rc)
        return np.sum((rc - target) ** 2)

    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(n))
    x0 = np.array([1 / n] * n)

    result = minimize(risk_parity_obj, x0, args=cov, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    return result.x if result.success else None


# ---------------------------------------------------------------------------
# Portfolio Metrics
# ---------------------------------------------------------------------------

def portfolio_metrics(weights, cov, expected_returns, risk_free_rate=0.065):
    """Calculate portfolio-level metrics."""
    port_ret = np.sum(weights * expected_returns)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
    sharpe = (port_ret * 252 - risk_free_rate) / (port_vol * np.sqrt(252)) if port_vol > 0 else 0

    # Diversification ratio = weighted avg volatility / portfolio volatility
    weighted_vol = np.sum(weights * np.sqrt(np.diag(cov)))
    div_ratio = weighted_vol / port_vol if port_vol > 0 else 1

    # Risk contribution per asset
    rc = weights * (np.dot(cov, weights)) / port_vol if port_vol > 0 else weights * 0

    return {
        'expected_annual_return': round(float(port_ret * 252), 4),
        'annual_volatility': round(float(port_vol * np.sqrt(252)), 4),
        'sharpe_ratio': round(float(sharpe), 4),
        'diversification_ratio': round(float(div_ratio), 4),
        'risk_free_rate_used': risk_free_rate,
        'risk_contributions': [round(float(x), 4) for x in rc],
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(tickers, period='1y', risk_free_rate=0.065):
    try:
        ticker_list = json.loads(tickers) if isinstance(tickers, str) else list(tickers)
        if isinstance(ticker_list, str):
            ticker_list = [ticker_list]

        if len(ticker_list) < 2:
            return json.dumps({
                'tickers': ticker_list,
                'error': 'Need at least 2 tickers for portfolio analysis',
                'note': 'Running single-asset mode',
                'timestamp': pd.Timestamp.now().isoformat()
            })

        price_df, error = fetch_aligned_prices(ticker_list, period)
        if error or price_df is None:
            return json.dumps({'tickers': ticker_list, 'error': error,
                               'timestamp': pd.Timestamp.now().isoformat()})

        corr, cov = compute_correlation(price_df)
        returns = price_df.pct_change().dropna()
        expected_ret = returns.mean()

        # Correlation matrix as dict
        corr_dict = {}
        for i, t1 in enumerate(ticker_list):
            corr_dict[t1] = {}
            for j, t2 in enumerate(ticker_list):
                corr_dict[t1][t2] = round(float(corr.iloc[i, j]), 4)

        # Covariance matrix as dict
        cov_dict = {}
        for i, t1 in enumerate(ticker_list):
            cov_dict[t1] = {}
            for j, t2 in enumerate(ticker_list):
                cov_dict[t1][t2] = round(float(cov.iloc[i, j]), 6)

        # Individual asset stats
        individual = {}
        for t in ticker_list:
            asset_ret = returns[t]
            individual[t] = {
                'annual_return': round(float(asset_ret.mean() * 252), 4),
                'annual_volatility': round(float(asset_ret.std() * np.sqrt(252)), 4),
                'sharpe_ratio': round(float((asset_ret.mean() * 252 - risk_free_rate) /
                                           (asset_ret.std() * np.sqrt(252))), 4) if asset_ret.std() > 0 else 0,
                'last_price': round(float(price_df[t].iloc[-1]), 2),
                'start_price': round(float(price_df[t].iloc[0]), 2),
                'total_return': round(float(price_df[t].iloc[-1] / price_df[t].iloc[0] - 1), 4),
            }

        # Optimization
        objectives = {}

        if HAS_SCIPY:
            # Max Sharpe
            msw = max_sharpe_weights(cov.values, expected_ret.values, risk_free_rate)
            if msw is not None:
                objectives['max_sharpe'] = {
                    'weights': {t: round(float(w), 4) for t, w in zip(ticker_list, msw)},
                    'metrics': portfolio_metrics(msw, cov.values, expected_ret.values, risk_free_rate)
                }

            # Min Volatility
            mvw = min_volatility_weights(cov.values)
            if mvw is not None:
                objectives['min_volatility'] = {
                    'weights': {t: round(float(w), 4) for t, w in zip(ticker_list, mvw)},
                    'metrics': portfolio_metrics(mvw, cov.values, expected_ret.values, risk_free_rate)
                }

            # Risk Parity
            rpw = risk_parity_weights(cov.values)
            if rpw is not None:
                objectives['risk_parity'] = {
                    'weights': {t: round(float(w), 4) for t, w in zip(ticker_list, rpw)},
                    'metrics': portfolio_metrics(rpw, cov.values, expected_ret.values, risk_free_rate)
                }
        else:
            # Equal-weight fallback
            ew = np.array([1 / len(ticker_list)] * len(ticker_list))
            objectives['equal_weight'] = {
                'weights': {t: round(float(1 / len(ticker_list)), 4) for t in ticker_list},
                'metrics': portfolio_metrics(ew, cov.values, expected_ret.values, risk_free_rate)
            }

        result = {
            'tickers': ticker_list,
            'analysis_period': period,
            'n_assets': len(ticker_list),
            'individual_assets': individual,
            'correlation_matrix': corr_dict,
            'covariance_matrix': cov_dict,
            'optimization': objectives,
            'n_days_data': len(price_df),
            'timestamp': pd.Timestamp.now().isoformat()
        }

        return json.dumps(result)

    except Exception as e:
        print(f"Error in portfolio_engine: {e}", file=sys.stderr)
        return json.dumps({'error': str(e), 'timestamp': pd.Timestamp.now().isoformat()})

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python portfolio_engine.py <ticker1,ticker2,...> [period] [risk_free_rate]")
        sys.exit(1)
    tickers = sys.argv[1].split(',')
    period = sys.argv[2] if len(sys.argv) > 2 else '1y'
    rf = float(sys.argv[3]) if len(sys.argv) > 3 else 0.065
    print(main(tickers, period, rf))
