#!/usr/bin/env python3
"""
Market Pro Analyst Orchestrator
Multi-ticker support, advanced ML, and database persistence.
"""
import json
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
import fetch_data
import ml_forecast
import distill_forecast_sl
import adversarial_audit
import sentiment_engine
import risk_engine
import valuation_engine
import generate_layman_report
import database
import portfolio_engine
import ml_advanced
import competitor_scanner


def analyze_single_ticker(ticker, args, analysis_template):
    """Run the full analysis pipeline for a single ticker."""
    analysis = dict(analysis_template)
    analysis['ticker'] = ticker
    output_dir = Path(args.output_dir or f'./output/{ticker}')
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Analyzing {ticker}...")
    print(f"{'='*60}")

    # 1. Fetch Data
    print(f"[1/9] Fetching data for {ticker}...")
    data_json = fetch_data.main(ticker, args.days)
    analysis['modules']['data'] = json.loads(data_json)

    # 2. ML Forecast
    print(f"[2/9] Running {'advanced' if args.advanced else 'standard'} ML forecast...")
    if args.advanced:
        forecast_json = ml_advanced.main(analysis['modules']['data'], args.forecast_days)
    else:
        forecast_json = ml_forecast.main(analysis['modules']['data'], args.forecast_days)
    analysis['modules']['forecast'] = json.loads(forecast_json)

    # 3. Distill Forecast & Risk Clustering
    print("[3/9] Clustering forecast scenarios...")
    distill_json = distill_forecast_sl.main(
        analysis['modules']['data'], analysis['modules']['forecast'], ticker
    )
    analysis['modules']['distillation'] = json.loads(distill_json)

    # 4. Adversarial Audit
    print("[4/9] Running adversarial audit...")
    audit_json = adversarial_audit.main(analysis['modules']['data'], analysis['modules']['forecast'])
    analysis['modules']['adversarial_audit'] = json.loads(audit_json)

    # 5. Sentiment
    print("[5/9] Running sentiment analysis...")
    sentiment_json = sentiment_engine.main(analysis['modules']['data'])
    analysis['modules']['sentiment'] = json.loads(sentiment_json)

    # 6. Risk Engine
    print("[6/9] Running risk engine...")
    risk_json = risk_engine.main(analysis['modules']['data'], analysis['modules']['forecast'])
    analysis['modules']['risk'] = json.loads(risk_json)

    # 7. Valuation
    print("[7/9] Running valuation engine...")
    valuation_json = valuation_engine.main(analysis['modules']['data'])
    analysis['modules']['valuation'] = json.loads(valuation_json)

    # 8. Competitor Scanner
    print("[8/9] Scanning competitors & peer comparison...")
    competitor_json = competitor_scanner.main(analysis['modules']['data'], ticker)
    analysis['modules']['competitors'] = json.loads(competitor_json)

    # 9. Report
    print("[9/9] Generating report...")
    report_json = generate_layman_report.main(analysis, str(output_dir))
    analysis['modules']['report'] = json.loads(report_json)

    # Save analysis JSON
    analysis_path = output_dir / 'analysis.json'
    with open(analysis_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"Analysis JSON saved to {analysis_path}")

    # Save to database
    if not args.no_save:
        try:
            db_path = args.db_path
            database.init_db(db_path)
            run_id = database.save_run(ticker, analysis['parameters'], db_path=db_path)
            for mod_name, mod_data in analysis['modules'].items():
                database.save_result(run_id, mod_name, mod_data, db_path=db_path)

            # Save competitor scan
            comp = analysis['modules'].get('competitors', {})
            if comp and comp.get('peer_tickers'):
                database.save_competitor_scan(
                    ticker=ticker,
                    sector=comp.get('sector', {}).get('sector', 'Unknown'),
                    n_peers=comp.get('n_peers_scanned', 0),
                    peers_json=comp.get('peers', {}),
                    comparison_json=comp.get('target_vs_peers', {}),
                    db_path=db_path
                )

            # Save model performance if forecast exists
            fc = analysis['modules'].get('forecast', {})
            if fc.get('forecast_reliability_score') is not None:
                database.save_model_performance(
                    ticker=ticker,
                    model_name='advanced_ensemble' if args.advanced else 'monte_carlo_student_t',
                    forecast_date=datetime.now().strftime('%Y-%m-%d'),
                    forecast_price=fc.get('forecast', {}).get('mean', [None])[-1],
                    actual_price=None,
                    error=None,
                    forecast_reliability=fc.get('forecast_reliability_score'),
                    db_path=db_path
                )
            print(f"Saved to database (run ID: {run_id})")
        except Exception as e:
            print(f"Warning: DB save failed ({e})")

    print(f"Analysis complete for {ticker}!")
    return analysis


def main():
    parser = argparse.ArgumentParser(description='Market Pro Analyst Orchestrator')
    parser.add_argument('ticker', nargs='?', default=None,
                        help='Single stock ticker (e.g., RELIANCE.NS)')
    parser.add_argument('--tickers', nargs='+', default=None,
                        help='Multiple tickers for portfolio analysis (e.g., --tickers RELIANCE.NS TCS.NS INFY.NS)')
    parser.add_argument('--days', type=int, default=365,
                        help='Days of historical data (default: 365)')
    parser.add_argument('--forecast-days', type=int, default=7,
                        help='Forecast horizon in days (default: 7)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Output directory (default: ./output/<ticker>)')
    parser.add_argument('--format', type=str, choices=['html', 'pdf', 'both'], default='both',
                        help='Output format (default: both)')
    parser.add_argument('--advanced', action='store_true',
                        help='Use advanced ML models (XGBoost, ensemble, walk-forward CV)')
    parser.add_argument('--db-path', type=str, default=None,
                        help='SQLite database path (default: ./data/market.db)')
    parser.add_argument('--no-save', action='store_true',
                        help='Skip saving to database')
    parser.add_argument('--period', type=str, default='1y',
                        help='Period for portfolio analysis (default: 1y)')
    args = parser.parse_args()

    # Determine tickers
    tickers = args.tickers or ([args.ticker] if args.ticker else [])
    if not tickers:
        parser.print_help()
        print("\nError: Specify a ticker (positional) or --tickers")
        sys.exit(1)

    # Initialize DB
    if not args.no_save:
        try:
            database.init_db(args.db_path)
        except Exception as e:
            print(f"Warning: DB init failed ({e})")

    # Base analysis template
    base_analysis = {
        'analysis_timestamp': datetime.now().isoformat(),
        'parameters': {
            'historical_days': args.days,
            'forecast_days': args.forecast_days,
            'advanced_ml': args.advanced
        },
        'modules': {}
    }

    # Single ticker mode
    if len(tickers) == 1:
        analyze_single_ticker(tickers[0], args, base_analysis)
        return

    # Multi-ticker mode: analyze each ticker then run portfolio
    print(f"\n{'='*60}")
    print(f"Portfolio Mode: {len(tickers)} tickers")
    print(f"{'='*60}")

    all_analyses = {}
    for t in tickers:
        result = analyze_single_ticker(t, args, base_analysis)
        all_analyses[t] = result

    # Run portfolio analysis
    print(f"\n{'='*60}")
    print("Running Portfolio Optimization...")
    print(f"{'='*60}")

    portfolio_json = portfolio_engine.main(tickers, period=args.period)
    portfolio_data = json.loads(portfolio_json)

    # Save portfolio results
    output_dir = Path(args.output_dir or './output/portfolio')
    output_dir.mkdir(parents=True, exist_ok=True)

    portfolio_path = output_dir / 'portfolio_analysis.json'
    with open(portfolio_path, 'w') as f:
        json.dump(portfolio_data, f, indent=2)
    print(f"Portfolio analysis saved to {portfolio_path}")

    # Save portfolio to DB
    if not args.no_save:
        try:
            database.save_portfolio_analysis(
                tickers=tickers,
                correlation_matrix=portfolio_data.get('correlation_matrix', {}),
                optimization_results=portfolio_data.get('optimization', {}),
                portfolio_metrics={
                    t: portfolio_data.get('individual_assets', {}).get(t, {})
                    for t in tickers
                },
                db_path=args.db_path
            )
            print("Portfolio saved to database.")
        except Exception as e:
            print(f"Warning: Portfolio DB save failed ({e})")

    print("\nPortfolio analysis complete!")
    print("\nSummary:")
    ind = portfolio_data.get('individual_assets', {})
    for t in tickers:
        if t in ind:
            a = ind[t]
            print(f"  {t}: Return={a.get('total_return', '?'):.1%}, "
                  f"Vol={a.get('annual_volatility', '?'):.2f}, "
                  f"Sharpe={a.get('sharpe_ratio', '?'):.2f}")

    opt = portfolio_data.get('optimization', {})
    for method, data in opt.items():
        if 'metrics' in data:
            m = data['metrics']
            print(f"\n  {method.replace('_', ' ').title()}: "
                  f"Return={m.get('expected_annual_return', '?'):.1%}, "
                  f"Vol={m.get('annual_volatility', '?'):.2f}, "
                  f"Sharpe={m.get('sharpe_ratio', '?'):.2f}")

    print(f"\nAll results saved to {output_dir}")


if __name__ == '__main__':
    main()
