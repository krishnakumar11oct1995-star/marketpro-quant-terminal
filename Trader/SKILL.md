---
name: market-pro-analyst
description: Full-stack Indian markets trading agent — strategies, backtesting, paper trading, ML forecasting, risk management, portfolio optimization, PDF reports.
---

# Market Pro Analyst

Institutional-grade trading agent for Indian markets (NSE/BSE). Supports single-ticker deep-dives, strategy-based trading, backtesting, paper trading with risk management, and portfolio optimization.

## Architecture

```
MarketProAgent/
├── main.py                    # CLI entry point (6 commands)
├── config.yaml                # All configuration
├── core/
│   ├── models.py              # Dataclasses (Bar, Order, Position, Trade, StrategyResult...)
│   ├── database.py            # SQLite persistence (8 tables, all CRUD)
│   ├── paper_broker.py        # Paper trading engine (fills, positions, SL/TSL, trade recording)
│   ├── risk_manager.py        # Position sizing, circuit breakers, max daily loss
│   └── performance_tracker.py # P&L summary, Sharpe, drawdown
├── strategies/
│   ├── __init__.py            # Strategy registry (dynamic discovery)
│   ├── base.py                # BaseStrategy ABC + indicator helpers
│   ├── supertrend.py          # Trend following (ATR bands)
│   ├── macd_crossover.py      # MACD line/signal crossover
│   ├── rsi_mean_reversion.py  # Oversold/overbought bounce
│   └── breakout.py            # Volume breakout above highs/lows
├── backtesting/
│   ├── engine.py              # Walk-forward backtest engine
│   └── metrics.py             # Return %, Sharpe, max DD, win rate, profit factor
├── agents/
│   ├── orchestrator.py        # Main coordinator — runs full analysis pipeline
│   ├── data_agent.py          # yfinance data fetching with cache
│   ├── analysis_agent.py      # Calls ML, valuation, sentiment, competitor scan
│   ├── strategy_agent.py      # Evaluates all enabled strategies, picks best
│   ├── market_context_agent.py # Nifty, Sensex, VIX
│   ├── screener_agent.py      # Pattern scan on watchlist
│   ├── llm_agent.py           # Optional Gemini/OpenAI integration
│   └── reporting_agent.py     # Text report generation
└── scripts/                   # ML, valuation, sentiment, competitor scan
    ├── valuation_engine.py, ml_forecast.py, ml_advanced.py,
    ├── sentiment_engine.py, risk_engine.py, competitor_scanner.py,
    ├── distill_forecast_sl.py, adversarial_audit.py, portfolio_engine.py, ...
```

## CLI Commands

```bash
python main.py analyze RELIANCE.NS         # Deep-dive on one ticker
python main.py screen                       # Run screener on watchlist
python main.py run                          # Full pipeline (screener + all tickers)
python main.py backtest RELIANCE.NS --period 1y   # Backtest all strategies
python main.py portfolio                    # Show P&L, win rate, Sharpe
python main.py status                       # Agent status summary
```

## Strategy Engine

| Strategy | Type | Parameters |
|----------|------|------------|
| Supertrend | Trend following | period=10, multiplier=3.0 |
| MACD Crossover | Momentum | default 12/26/9 |
| RSI Mean Reversion | Mean reversion | oversold=30, overbought=70 |
| Volume Breakout | Breakout | volume_mult=1.5, lookback=20 |

All strategies output: signal (STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL), confidence (0-1), entry price, stop-loss, target, reason.

Strategies are configurable in `config.yaml` under `strategies.enabled`.

## Backtesting

- Walk-forward evaluation on historical data (yfinance)
- Tracks entries, exits, stop-loss hits, take-profit hits
- Metrics: total return %, Sharpe ratio, max drawdown %, win rate, profit factor
- Supports comparing all strategies on the same ticker

## Paper Trading

- Simulated fills with 0.1% random slippage
- Position management (add/average in)
- Stop-loss and trailing stop-loss execution
- All trades, orders, positions persisted to SQLite
- Survives restarts (state loaded from DB)

## Risk Manager

- Position sizing: Kelly-approximate (% of capital risked per trade)
- Circuit breakers: max daily loss %, max positions, max trades/day
- Stop-loss: ATR-based (2x) or fixed percentage (default 15%)
- Take-profit: configurable risk-reward ratio (default 2:1)

## Analysis Modules

- **Valuation**: DCF, Graham Number, DDM from real financials (yfinance)
- **ML Forecast**: Monte Carlo with Student-t distribution, regime detection
- **ML Advanced**: XGBoost + RandomForest + naive ensemble, walk-forward CV
- **Sentiment**: News headlines from Yahoo Finance, TextBlob scoring
- **Competitor Scan**: Sector-based peer identification, metric comparison table
- **Adversarial Audit**: Internal forecast vs real analyst consensus
- **Risk Engine**: VaR, CVaR, Sharpe, Sortino, beta, simulated/real macro
- **Portfolio Optimization**: Correlation, mean-variance, risk parity
- **Distillation**: K-means clustering of MC paths into Bull/Bear/Neutral archetypes

## Configuration

All settings in `config.yaml`:

```yaml
trading:
  mode: paper                    # paper | live
  capital: 100000
  risk_per_trade_pct: 1.0
  max_trades_per_day: 5
  max_daily_loss_pct: 3.0
  max_positions: 3
  stop_loss_default_pct: 15.0

strategies:
  enabled: ["supertrend", "macd_crossover", "rsi_mean_reversion", "breakout"]

watchlist:
  tickers:
    - "RELIANCE.NS"
    - "TCS.NS"
    - "INFY.NS"
  indices:
    - "^NSEI"      # NIFTY 50
    - "^BSESN"     # SENSEX

llm:
  enabled: false
  provider: gemini  # gemini | openai
  api_key: ""
```

## Output

```
reports/
├── RELIANCE.NS_20260526_145256.txt
├── TCS.NS_20260526_145307.txt
└── ...
```

## Dependencies

```
yfinance, pandas, numpy, scikit-learn, scipy, xgboost, plotly
requests, beautifulsoup4, lxml, textblob, schedule
pyyaml, jinja2, weasyprint, rich
```

## Critical Guardrails

- **Paper-only by default**: Live trading requires explicit config change
- **No real money risk**: All trades are simulated unless mode is changed to `live`
- **Data transparency**: All data sources (yfinance) are logged
- **Risk limits enforced**: Circuit breakers prevent overtrading
- **LLM is opt-in**: Requires explicit API key configuration
- **Not financial advice**: All outputs are for educational/research purposes
