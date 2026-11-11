#!/usr/bin/env python3
"""
Valuation Engine
Fetches fundamental data and calculates intrinsic value using multiple models.
Outputs JSON with valuation results and sources.
"""
import json
import sys
import yfinance as yf
import numpy as np
from datetime import datetime

def main(data):
    try:
        # Parse inputs
        hist_data = json.loads(data) if isinstance(data, str) else data
        
        ticker = hist_data.get('ticker', 'UNKNOWN')
        
        # Fetch ticker object for fundamentals
        stock = yf.Ticker(ticker)
        
        # Get info (contains many fundamentals)
        info = stock.info
        
        # Get financial statements
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        # Extract key metrics (with fallbacks)
        # Market cap
        market_cap = info.get('marketCap')
        # Enterprise value
        enterprise_value = info.get('enterpriseValue')
        # Shares outstanding
        shares_outstanding = info.get('sharesOutstanding')
        # Current price (from real_time or info)
        rt_current = hist_data.get('real_time', {}).get('current_price')
        current_price = rt_current or info.get('currentPrice') or info.get('regularMarketPrice')
        
        # For Indian stocks, sometimes the above fields are not populated, so we try to get from history
        if not current_price and 'historical_data' in hist_data:
            close_prices = hist_data['historical_data']['close']
            if close_prices:
                current_price = close_prices[-1]
        
        # EPS (trailing and forward)
        eps_trailing = info.get('trailingEPS')
        eps_forward = info.get('forwardEPS')
        # Book value per share
        book_value = info.get('bookValue')
        # Dividend yield
        dividend_yield = info.get('dividendYield')
        # Profit margins
        profit_margin = info.get('profitMargins')
        # Operating margin
        operating_margin = info.get('operatingMargins')
        # Return on equity
        roe = info.get('returnOnEquity')
        # Debt to equity
        debt_to_equity = info.get('debtToEquity')
        # Free cash flow (try to get from cash flow statement)
        fcf = None
        if not cash_flow.empty:
            # Look for Free Cash Flow or Operating Cash Flow - Capital Expenditures
            if 'Free Cash Flow' in cash_flow.index:
                fcf = cash_flow.loc['Free Cash Flow'].iloc[0]  # most recent
            elif 'Operating Cash Flow' in cash_flow.index and 'Capital Expenditures' in cash_flow.index:
                fcf = cash_flow.loc['Operating Cash Flow'].iloc[0] - abs(cash_flow.loc['Capital Expenditures'].iloc[0])
        
        # If still no FCF, try to get from info
        if fcf is None:
            fcf = info.get('freeCashflow')
        
        # Prepare data for valuation models
        # We'll calculate:
        # 1. Graham Number (if we have EPS and BVPS)
        # 2. Simple DCF (if we have FCF and shares)
        # 3. Relative valuation (if we have peer data, but we skip for simplicity)
        # 4. Dividend Discount Model (if we have dividend)
        
        valuation_results = {}
        notes = []
        
        # Graham Number: sqrt(22.5 * EPS * BVPS)
        if eps_trailing and eps_trailing > 0 and book_value and book_value > 0:
            graham_number = (22.5 * eps_trailing * book_value) ** 0.5
            valuation_results['graham_number'] = {
                'value': graham_number,
                'eps_used': eps_trailing,
                'book_value_per_share_used': book_value,
                'note': 'Based on trailing EPS and book value per share.'
            }
        else:
            notes.append("Graham Number: insufficient data (EPS or BVPS missing or non-positive).")
        
        # Simple DCF: FCF * (1+g) / (WACC - g) terminal value, simplified
        # We'll use a simple single-stage DCF with assumptions
        if fcf and shares_outstanding and shares_outstanding > 0:
            # Assumptions (these should be configurable or based on industry)
            growth_rate = 0.05  # 5% perpetual growth
            wacc = 0.10  # 10% WACC
            if wacc > growth_rate:
                # Present value of future FCFs: FCF * (1+g) / (WACC - g)
                firm_value = fcf * (1 + growth_rate) / (wacc - growth_rate)
                equity_value = firm_value  # assuming no net debt for simplicity; we should subtract debt and add cash
                # Try to get net debt from balance sheet
                net_debt = 0
                if not balance_sheet.empty:
                    # Approximate: total debt - cash and equivalents
                    # We'll try to get total debt and cash
                    total_debt = None
                    cash_and_equivalents = None
                    # Look for common items
                    if 'Total Debt' in balance_sheet.index:
                        total_debt = balance_sheet.loc['Total Debt'].iloc[0]
                    if 'Cash And Cash Equivalents' in balance_sheet.index:
                        cash_and_equivalents = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
                    if total_debt is not None and cash_and_equivalents is not None:
                        net_debt = total_debt - cash_and_equivalents
                    elif 'Total Liabilities Net Minority Interest' in balance_sheet.index:
                        # Fallback: use total liabilities as debt (crude)
                        total_liabilities = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
                        net_debt = total_liabilities - (cash_and_equivalents if cash_and_equivalents is not None else 0)
                
                equity_value = firm_value - net_debt
                dcf_value_per_share = equity_value / shares_outstanding
                valuation_results['dcf'] = {
                    'value_per_share': dcf_value_per_share,
                    'fcf_used': fcf,
                    'shares_outstanding_used': shares_outstanding,
                    'net_debt_used': net_debt,
                    'assumptions': {
                        'growth_rate': growth_rate,
                        'wacc': wacc
                    },
                    'note': 'Simple single-stage DCF with perpetual growth. Net debt approximated from balance sheet.'
                }
            else:
                notes.append("DCF: WACC must be greater than growth rate.")
        else:
            notes.append("DCF: insufficient data (FCF or shares outstanding missing).")
        
        # Dividend Discount Model (if we have dividend)
        if dividend_yield and dividend_yield > 0 and eps_trailing:
            # Simple Gordon Growth Model: D1 / (k - g)
            # We'll assume dividend grows at same rate as earnings (simplified)
            dividend_per_share = current_price * dividend_yield if current_price else None
            if dividend_per_share and current_price:
                # We need to solve for implied growth, but we'll assume a growth rate
                g = 0.05  # same as above
                k = 0.10  # cost of equity
                if k > g:
                    ddm_value = dividend_per_share * (1 + g) / (k - g)
                    valuation_results['ddm'] = {
                        'value_per_share': ddm_value,
                        'dividend_per_share_used': dividend_per_share,
                        'assumptions': {
                            'growth_rate': g,
                            'cost_of_equity': k
                        },
                        'note': 'Gordon Growth Model for dividend discount.'
                    }
                else:
                    notes.append("DDM: cost of equity must be greater than growth rate.")
            else:
                notes.append("DDM: insufficient data (dividend or price missing).")
        else:
            notes.append("DDM: no dividend or dividend yield not available.")
        
        # If we have no valuation models, we can try to use price multiples (like PE) but we need industry average.
        # We'll skip for now and note.
        
        # Prepare final result
        result = {
            'ticker': ticker,
            'current_price': current_price,
            'fundamental_data': {
                'market_cap': market_cap,
                'enterprise_value': enterprise_value,
                'shares_outstanding': shares_outstanding,
                'eps_trailing': eps_trailing,
                'eps_forward': eps_forward,
                'book_value_per_share': book_value,
                'dividend_yield': dividend_yield,
                'profit_margin': profit_margin,
                'operating_margin': operating_margin,
                'roe': roe,
                'debt_to_equity': debt_to_equity,
                'free_cash_flow': fcf
            },
            'valuation_models': valuation_results,
            'notes': notes,
            'timestamp': datetime.now().isoformat(),
            'data_sources': {
                'info': 'yfinance.Ticker.info',
                'financial_statements': 'yfinance.Ticker.income_stmt, balance_sheet, cashflow'
            }
        }
        
        return json.dumps(result)
    
    except Exception as e:
        print(f"Error in valuation_engine: {e}", file=sys.stderr)
        error_result = {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(error_result)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python valuation_engine.py <data_json>")
        sys.exit(1)
    
    data = sys.argv[1]
    print(main(data))