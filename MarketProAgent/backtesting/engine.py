"""
Backtesting engine — walk-forward, strategy evaluation, performance metrics.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
from strategies.base import BaseStrategy
from strategies.__init__ import get_strategy, list_strategies
from backtesting.metrics import BacktestMetrics


class BacktestEngine:
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital

    def fetch_data(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                return hist
        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
        return None

    def run_strategy(self, strategy: BaseStrategy, df: pd.DataFrame,
                     ticker: str) -> Tuple[List[Dict], pd.Series]:
        """Run a strategy over historical data and return signals + equity curve."""
        signals = []
        equity = self.initial_capital
        equity_curve = []
        position = None  # {'side': 'long'/'short', 'entry_price': float, 'entry_idx': int}

        for i in range(50, len(df)):  # need enough data for indicators
            window = df.iloc[:i + 1]
            signal = strategy.evaluate(window, ticker)
            price = float(df['Close'].iloc[i])
            date = df.index[i]

            # Entry logic
            if position is None:
                if signal.signal in ('STRONG_BUY', 'BUY') and signal.entry_price:
                    position = {
                        'side': 'long',
                        'entry_price': price,
                        'entry_idx': i,
                        'entry_date': date,
                        'stop_loss': signal.stop_loss,
                        'target': signal.target,
                    }
                    signals.append({
                        'date': date.isoformat(),
                        'action': 'BUY',
                        'price': price,
                        'strategy': strategy.name,
                        'reason': signal.reason,
                    })
                elif signal.signal in ('STRONG_SELL', 'SELL') and signal.entry_price:
                    position = {
                        'side': 'short',
                        'entry_price': price,
                        'entry_idx': i,
                        'entry_date': date,
                        'stop_loss': signal.stop_loss,
                        'target': signal.target,
                    }
                    signals.append({
                        'date': date.isoformat(),
                        'action': 'SELL',
                        'price': price,
                        'strategy': strategy.name,
                        'reason': signal.reason,
                    })

            # Exit logic
            elif position:
                exit_reason = None
                exit_price = None

                if position['side'] == 'long':
                    if signal.signal in ('STRONG_SELL', 'SELL'):
                        exit_reason = signal.reason or 'opposite_signal'
                        exit_price = price
                    elif position['stop_loss'] and price <= position['stop_loss']:
                        exit_reason = 'stop_loss'
                        exit_price = position['stop_loss']
                    elif position['target'] and price >= position['target']:
                        exit_reason = 'take_profit'
                        exit_price = position['target']
                else:  # short
                    if signal.signal in ('STRONG_BUY', 'BUY'):
                        exit_reason = signal.reason or 'opposite_signal'
                        exit_price = price
                    elif position['stop_loss'] and price >= position['stop_loss']:
                        exit_reason = 'stop_loss'
                        exit_price = position['stop_loss']
                    elif position['target'] and price <= position['target']:
                        exit_reason = 'take_profit'
                        exit_price = position['target']

                if exit_reason:
                    ret = (exit_price - position['entry_price']) / position['entry_price']
                    if position['side'] == 'short':
                        ret = -ret
                    equity *= (1 + ret)
                    signals.append({
                        'date': date.isoformat(),
                        'action': 'EXIT',
                        'price': exit_price,
                        'pnl_pct': round(ret * 100, 2),
                        'reason': exit_reason,
                        'strategy': strategy.name,
                    })
                    position = None

            equity_curve.append(equity)

        # Close any open position at last price
        if position:
            exit_price = float(df['Close'].iloc[-1])
            ret = (exit_price - position['entry_price']) / position['entry_price']
            if position['side'] == 'short':
                ret = -ret
            equity *= (1 + ret)
            signals.append({
                'date': df.index[-1].isoformat(),
                'action': 'EXIT(EOH)',
                'price': exit_price,
                'pnl_pct': round(ret * 100, 2),
            })

        return signals, pd.Series(equity_curve)

    def backtest(self, ticker: str, strategies: List[str] = None,
                 period: str = "1y") -> Dict:
        """Run backtest for one or more strategies and return comparative results."""
        df = self.fetch_data(ticker, period)
        if df is None:
            return {'ticker': ticker, 'error': 'No data'}

        if strategies is None:
            strategies = list_strategies()

        results = {}
        for s_name in strategies:
            try:
                strategy = get_strategy(s_name)
                signals, equity_curve = self.run_strategy(strategy, df, ticker)
                metrics = BacktestMetrics(equity_curve, signals, self.initial_capital)
                results[s_name] = {
                    'signals': signals,
                    'metrics': metrics.compute(),
                    'final_equity': round(float(equity_curve.iloc[-1]), 2),
                    'return_pct': round((equity_curve.iloc[-1] / self.initial_capital - 1) * 100, 2),
                }
            except Exception as e:
                results[s_name] = {'error': str(e)}

        return {
            'ticker': ticker,
            'period': period,
            'initial_capital': self.initial_capital,
            'results': results,
            'best_strategy': max(
                ((k, v) for k, v in results.items() if 'metrics' in v),
                key=lambda x: x[1]['metrics']['total_return_pct'],
                default=(None, None)
            )[0],
        }
