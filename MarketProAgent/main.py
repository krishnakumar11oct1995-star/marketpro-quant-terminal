#!/usr/bin/env python3
"""
MarketProAgent — Standalone AI Trading Agent for Indian Markets.
Entry point with CLI commands.
"""
import argparse
import sys
import os
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_config(path: str = None) -> dict:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    import yaml
    with open(path, 'r') as f:
        config = yaml.safe_load(f) or {}
    return apply_env_secrets(config)


def apply_env_secrets(config: dict) -> dict:
    """Secrets come from env vars first; config.yaml values are only a fallback."""
    llm = config.get('llm') or {}
    config['llm'] = llm
    llm['api_key'] = os.environ.get('LLM_API_KEY') or llm.get('api_key') or ''

    reports = config.get('reports') or {}
    config['reports'] = reports
    email = reports.get('email') or {}
    reports['email'] = email
    email['sender_password'] = os.environ.get('SMTP_PASSWORD') or email.get('sender_password') or ''
    return config


def cmd_analyze(args):
    config = load_config(args.config)
    from agents.orchestrator import Orchestrator
    orch = Orchestrator(config)
    try:
        orch.run_full_analysis(args.ticker.upper())
    finally:
        orch.close()


def cmd_screen(args):
    config = load_config(args.config)
    from agents.orchestrator import Orchestrator
    orch = Orchestrator(config)
    try:
        orch.run_screener()
    finally:
        orch.close()


def cmd_run(args):
    """Run full pipeline on all watchlist tickers."""
    config = load_config(args.config)
    from agents.orchestrator import Orchestrator
    orch = Orchestrator(config)
    try:
        orch.run()
    finally:
        orch.close()


def cmd_backtest(args):
    """Run backtest on a ticker."""
    config = load_config(args.config)
    from backtesting.engine import BacktestEngine
    engine = BacktestEngine(initial_capital=args.capital)
    strategies = args.strategies.split(',') if args.strategies else None
    result = engine.backtest(args.ticker.upper(), strategies, args.period)
    print(f"\nBacktest Results for {result['ticker']} ({result['period']})")
    print(f"Initial Capital: Rs.{result['initial_capital']:,.2f}")
    for s_name, s_result in result.get('results', {}).items():
        if 'error' in s_result:
            print(f"  {s_name}: ERROR - {s_result['error']}")
            continue
        m = s_result.get('metrics', {})
        print(f"\n  [{s_name}]")
        print(f"    Return:   {s_result['return_pct']:.2f}%")
        print(f"    Final:    Rs.{s_result['final_equity']:,.2f}")
        print(f"    Sharpe:   {m.get('sharpe_ratio', 'N/A')}")
        print(f"    Max DD:   {m.get('max_drawdown_pct', 'N/A')}%")
        print(f"    Win Rate: {m.get('win_rate_pct', 'N/A')}%")
        print(f"    Trades:   {m.get('total_trades', 'N/A')}")
    if result['best_strategy']:
        print(f"\n  Best: {result['best_strategy']}")


def cmd_portfolio(args):
    """Show portfolio summary."""
    config = load_config(args.config)
    from core.database import Database
    from core.performance_tracker import PerformanceTracker
    db_path = config.get('database', {}).get('path', './data/market.db')
    db = Database(db_path)
    try:
        tracker = PerformanceTracker(db)
        print(tracker.generate_report())
    finally:
        db.close()


def cmd_status(args):
    """Show agent status."""
    config = load_config(args.config)
    from core.database import Database
    db_path = config.get('database', {}).get('path', './data/market.db')
    db = Database(db_path)
    try:
        stats = db.get_trade_stats()
        print(f"Trade Stats:")
        print(f"  Total Trades: {stats.get('total', 0)}")
        print(f"  Total P&L:    Rs.{stats.get('total_pnl', 0):,.2f}")
        print(f"  Win Rate:     {stats.get('win_rate', 0):.1f}%")

        # No get_portfolios method available — skipping
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='MarketProAgent — Standalone AI Trading Agent for Indian Markets'
    )
    parser.add_argument('--config', default=None, help='Path to config.yaml')

    sub = parser.add_subparsers(dest='command', required=True)

    # analyze
    p_analyze = sub.add_parser('analyze', help='Analyze a single ticker')
    p_analyze.add_argument('ticker', help='Ticker symbol (e.g., RELIANCE.NS)')

    # screen
    sub.add_parser('screen', help='Run screener on watchlist')

    # run
    sub.add_parser('run', help='Run full pipeline')

    # backtest
    p_bt = sub.add_parser('backtest', help='Run backtest')
    p_bt.add_argument('ticker', help='Ticker to backtest')
    p_bt.add_argument('--strategies', default=None, help='Comma-separted strategies')
    p_bt.add_argument('--period', default='1y', help='Backtest period (e.g., 6mo, 1y, 2y)')
    p_bt.add_argument('--capital', type=float, default=100000, help='Initial capital')

    # portfolio
    sub.add_parser('portfolio', help='Show portfolio performance summary')

    # status
    sub.add_parser('status', help='Show agent status')

    args = parser.parse_args()
    cmd_map = {
        'analyze': cmd_analyze,
        'screen': cmd_screen,
        'run': cmd_run,
        'backtest': cmd_backtest,
        'portfolio': cmd_portfolio,
        'status': cmd_status,
    }
    cmd = cmd_map.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
