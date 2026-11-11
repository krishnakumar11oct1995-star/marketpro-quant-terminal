"""
Backtest metrics calculation.
"""
import numpy as np
from typing import List, Dict
import pandas as pd


class BacktestMetrics:
    def __init__(self, equity_curve: pd.Series, signals: List[Dict], initial_capital: float):
        self.equity_curve = equity_curve
        self.signals = signals
        self.initial_capital = initial_capital

    def compute(self) -> Dict:
        if len(self.equity_curve) < 2:
            return {'error': 'Not enough data'}

        eq = self.equity_curve.values
        final = eq[-1]
        total_ret = (final / self.initial_capital - 1) * 100

        # Daily returns
        daily_rets = np.diff(eq) / eq[:-1]

        # Sharpe (annualized, assuming 252 trading days)
        sharpe = 0.0
        if len(daily_rets) > 1 and np.std(daily_rets) > 0:
            sharpe = np.mean(daily_rets) / np.std(daily_rets) * np.sqrt(252)

        # Max drawdown
        peak = np.maximum.accumulate(eq)
        dd = (peak - eq) / peak
        max_dd = float(np.max(dd)) * 100 if len(dd) > 0 else 0.0

        # Trade analysis
        trades = [s for s in self.signals if s.get('action') in ('EXIT', 'EXIT(EOH)')]
        winning_trades = [t for t in trades if t.get('pnl_pct', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl_pct', 0) <= 0]
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0

        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0

        profit_factor = (
            abs(sum(t['pnl_pct'] for t in winning_trades) /
                min(sum(t['pnl_pct'] for t in losing_trades), -0.01))
            if losing_trades else float('inf')
        )

        return {
            'total_return_pct': round(total_ret, 2),
            'final_equity': round(final, 2),
            'sharpe_ratio': round(sharpe, 3),
            'max_drawdown_pct': round(max_dd, 2),
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': round(win_rate, 2),
            'avg_win_pct': round(avg_win, 2),
            'avg_loss_pct': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf',
        }
