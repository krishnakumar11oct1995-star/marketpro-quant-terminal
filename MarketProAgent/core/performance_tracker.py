"""
Performance tracker — P&L, Sharpe, drawdown, etc.
"""
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
from core.database import Database


class PerformanceTracker:
    def __init__(self, db: Database):
        self.db = db

    def get_summary(self) -> Dict:
        stats = self.db.get_trade_stats()
        total = stats.get('total', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        total_pnl = stats.get('total_pnl', 0)

        win_rate = (wins / total * 100) if total > 0 else 0
        profit_factor = (stats.get('gross_profit', 0) / abs(stats.get('gross_loss', 1))
                         if stats.get('gross_loss', 0) != 0 else float('inf'))
        avg_win = stats.get('gross_profit', 0) / wins if wins > 0 else 0
        avg_loss = stats.get('gross_loss', 0) / losses if losses > 0 else 0

        return {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': losses,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf',
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_win': round(stats.get('max_win', 0), 2),
            'max_loss': round(stats.get('max_loss', 0), 2),
        }

    def calculate_sharpe(self, returns: List[float], risk_free: float = 0.065) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns)
        excess = arr - risk_free / 252
        return float(np.mean(excess) / np.std(excess) * np.sqrt(252)) if np.std(excess) > 0 else 0.0

    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict:
        arr = np.array(equity_curve)
        peak = np.maximum.accumulate(arr)
        drawdown = (peak - arr) / peak
        max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0
        return {
            'max_drawdown_pct': round(max_dd * 100, 2),
            'max_drawdown_value': round(max_dd * arr[-1], 2),
        }

    def generate_report(self) -> str:
        """Generate a plain-text performance summary."""
        s = self.get_summary()
        lines = [
            "=" * 50,
            "PERFORMANCE REPORT",
            "=" * 50,
            f"Total Trades:   {s['total_trades']}",
            f"Win / Loss:     {s['winning_trades']} / {s['losing_trades']}",
            f"Win Rate:       {s['win_rate']:.1f}%",
            f"Total P&L:      Rs.{s['total_pnl']:,.2f}",
            f"Profit Factor:  {s['profit_factor']}",
            f"Avg Win:        Rs.{s['avg_win']:,.2f}",
            f"Avg Loss:       Rs.{s['avg_loss']:,.2f}",
            f"Max Win:        Rs.{s['max_win']:,.2f}",
            f"Max Loss:       Rs.{s['max_loss']:,.2f}",
            "=" * 50,
        ]
        return '\n'.join(lines)
