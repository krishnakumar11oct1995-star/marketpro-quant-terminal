"""
Orchestrator Agent — coordinates all agents for a full ticker analysis cycle.
"""
import json
from typing import Dict, Optional, List
from datetime import datetime
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.market_context_agent import MarketContextAgent
from agents.screener_agent import ScreenerAgent
from agents.llm_agent import LLMAgent
from agents.reporting_agent import ReportingAgent
from core.database import Database
from core.paper_broker import PaperBroker
from core.risk_manager import RiskManager
from core.models import OrderSide, OrderType


class Orchestrator:
    def __init__(self, config: dict):
        self.config = config
        db_path = config.get('database', {}).get('path', './data/market.db')
        self.db = Database(db_path)
        self.data_agent = DataAgent(config)
        self.analysis_agent = AnalysisAgent(config)
        self.strategy_agent = StrategyAgent(config)
        self.market_context_agent = MarketContextAgent(config)
        self.screener_agent = ScreenerAgent(config)
        self.llm_agent = LLMAgent(config)
        self.reporting_agent = ReportingAgent(config)
        self.broker = PaperBroker(
            initial_capital=config.get('trading', {}).get('initial_capital', 100000),
            db=self.db
        )
        self.risk_manager = RiskManager(config, self.broker)

    def run_full_analysis(self, ticker: str, analyses: List[str] = None,
                          print_output: bool = True) -> Dict:
        # 1. Fetch data
        df = self.data_agent.fetch_ohlcv(ticker)
        if df is None:
            if print_output:
                print(f"ERROR: No data for {ticker}")
            return {'error': f"No data for {ticker}"}

        if print_output:
            print(f"\n{'='*60}")
            print(f"MarketProAgent — Analyzing {ticker}")
            print(f"{'='*60}")

        # 2. Market context
        market_context = self.market_context_agent.fetch()
        if print_output:
            print(f"\n[Market Context]")
            for k, v in market_context.items():
                if isinstance(v, dict) and 'error' not in v:
                    print(f"  {k}: {v.get('last_price')} ({v.get('change_pct', 0):+.2f}%)")

        # 3. Strategy evaluation
        strategy_results = self.strategy_agent.evaluate(df, ticker)
        best = self.strategy_agent.best_signal(strategy_results)
        if print_output:
            print(f"\n[Strategy Signals]")
            for name, result in strategy_results.items():
                print(f"  {name}: {result.signal} (conf: {result.confidence:.0%})")
                if result.reason:
                    print(f"    {result.reason}")

        # 4. Run analyses
        analysis_results = self.analysis_agent.analyze_ticker(ticker, analyses)
        if print_output:
            for k, v in analysis_results.items():
                if k != 'ticker' and isinstance(v, dict):
                    out = json.dumps(v) if len(json.dumps(v)) < 200 else str(list(v.keys()))
                    print(f"  {k}: {out[:200]}")

        # 5. LLM summary (if available)
        if self.llm_agent.enabled:
            signal_data = {k: str(v) for k, v in strategy_results.items()}
            llm_summary = self.llm_agent.summarize_signal(ticker, signal_data)
            if llm_summary and print_output:
                print(f"\n[LLM Analysis]")
                print(f"  {llm_summary[:500]}")
        else:
            if print_output:
                print(f"\n[LLM] Disabled (no API key configured)")

        # 6. Generate and save report
        report = self.reporting_agent.generate_text_report(
            ticker, analysis_results, strategy_results, market_context
        )
        report_path = self.reporting_agent.save_report(ticker, report)
        if print_output:
            print(f"\n[Report] Saved to {report_path}")

        # 7. Execute paper trade if signal is good and risk allows
        trade_info = None
        if best and best.signal in ('BUY', 'STRONG_BUY') and best.entry_price:
            can_trade, msg = self.risk_manager.can_take_trade()
            if can_trade:
                sl = best.stop_loss or best.entry_price * 0.95
                qty = self.risk_manager.calculate_position_size(
                    entry_price=best.entry_price, stop_loss=sl
                )
                if qty > 0:
                    self.broker.place_order(
                        ticker=ticker, side=OrderSide.BUY, order_type=OrderType.MARKET,
                        quantity=qty, price=best.entry_price,
                        strategy=best.strategy_name
                    )
                    self.risk_manager.daily_trades += 1
                    trade_info = f"BUY {qty} {ticker} @ {best.entry_price}"
                    if print_output:
                        print(f"\n[Paper Trade] {trade_info}")
                        if best.stop_loss:
                            print(f"  Stop Loss: {best.stop_loss}")
                        if best.target:
                            print(f"  Target:    {best.target}")
            else:
                if print_output:
                    print(f"\n[Risk Manager] Trade blocked: {msg}")

        # 8. Save analysis run to DB
        self.db.save_analysis_run(ticker, 'full_analysis', {
            'strategy_results': {k: str(v) for k, v in strategy_results.items()},
            'analysis_results': {k: str(v) for k, v in analysis_results.items()},
        })

        return {
            'ticker': ticker,
            'strategy_results': {k: str(v) for k, v in strategy_results.items()},
            'best_signal': str(best) if best else None,
            'report_path': report_path,
            'trade': trade_info,
        }

    def run_screener(self, print_output: bool = True) -> list:
        results = self.screener_agent.scan()
        if print_output:
            print(f"\n[Screener Results]")
            for r in results:
                print(f"  {r['ticker']}: {', '.join(r['patterns'])} (score: {r['score']})")
        return results

    def run(self):
        """Main event loop (single pass for CLI mode)."""
        watchlist = self.config.get('watchlist', {}).get('tickers', [])
        if not watchlist:
            print("No watchlist configured. Add tickers to config.yaml under 'watchlist.tickers'")
            return
        self.run_screener()
        for ticker in watchlist:
            self.run_full_analysis(ticker)

    def close(self):
        self.db.close()
