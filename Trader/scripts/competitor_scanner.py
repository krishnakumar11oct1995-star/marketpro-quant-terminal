#!/usr/bin/env python3
"""
Competitor Scanner: Finds peers by sector/industry and compares key metrics.
"""
import json
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

# Curated sector mapping for common NSE stocks (ticker -> sector)
# Used as fallback when Yahoo Finance industry info is unavailable
SECTOR_MAP = {
    # Banking & Financials
    'HDFCBANK.NS': 'Banking', 'ICICIBANK.NS': 'Banking', 'SBIN.NS': 'Banking',
    'AXISBANK.NS': 'Banking', 'KOTAKBANK.NS': 'Banking', 'YESBANK.NS': 'Banking',
    'BANDHANBNK.NS': 'Banking', 'INDUSINDBK.NS': 'Banking', 'FEDERALBNK.NS': 'Banking',
    'RBLBANK.NS': 'Banking', 'PNB.NS': 'Banking', 'BANKBARODA.NS': 'Banking',
    'BAJFINANCE.NS': 'Financial Services', 'BAJAJFINSV.NS': 'Financial Services',
    'HDFCLIFE.NS': 'Insurance', 'SBILIFE.NS': 'Insurance', 'ICICIPRULI.NS': 'Insurance',
    'ICICIGI.NS': 'Insurance',

    # IT
    'TCS.NS': 'IT', 'INFY.NS': 'IT', 'WIPRO.NS': 'IT', 'HCLTECH.NS': 'IT',
    'TECHM.NS': 'IT', 'LTTS.NS': 'IT', 'COFORGE.NS': 'IT', 'MINDTREE.NS': 'IT',
    'PERSISTENT.NS': 'IT', 'MPHASIS.NS': 'IT', 'LTIINFOTECH.NS': 'IT',

    # Oil & Gas / Energy
    'RELIANCE.NS': 'Oil & Gas', 'ONGC.NS': 'Oil & Gas', 'IOC.NS': 'Oil & Gas',
    'BPCL.NS': 'Oil & Gas', 'HPCL.NS': 'Oil & Gas', 'GAIL.NS': 'Oil & Gas',
    'OIL.NS': 'Oil & Gas', 'PETRONET.NS': 'Oil & Gas', 'GUJGASLTD.NS': 'Oil & Gas',
    'MGL.NS': 'Oil & Gas', 'IGL.NS': 'Oil & Gas',

    # Pharma
    'SUNPHARMA.NS': 'Pharma', 'DRREDDY.NS': 'Pharma', 'CIPLA.NS': 'Pharma',
    'DIVISLAB.NS': 'Pharma', 'BIOCON.NS': 'Pharma', 'AUROPHARMA.NS': 'Pharma',
    'LUPIN.NS': 'Pharma', 'TORNTPHARM.NS': 'Pharma', 'ALKEM.NS': 'Pharma',
    'LAURUSLABS.NS': 'Pharma', 'GLENMARK.NS': 'Pharma', 'CADILAHC.NS': 'Pharma',

    # Auto
    'MARUTI.NS': 'Automotive', 'TATAMOTORS.NS': 'Automotive', 'M&M.NS': 'Automotive',
    'BAJAJ-AUTO.NS': 'Automotive', 'EICHERMOT.NS': 'Automotive', 'HEROMOTOCO.NS': 'Automotive',
    'BOSCHLTD.NS': 'Automotive', 'TIINDIA.NS': 'Automotive', 'BALKRISIND.NS': 'Automotive',

    # Consumer / FMCG
    'HINDUNILVR.NS': 'FMCG', 'ITC.NS': 'FMCG', 'NESTLEIND.NS': 'FMCG',
    'BRITANNIA.NS': 'FMCG', 'DABUR.NS': 'FMCG', 'MARICO.NS': 'FMCG',
    'COLPAL.NS': 'FMCG', 'GODREJCP.NS': 'FMCG', 'TATACONSUM.NS': 'FMCG',
    'PGHH.NS': 'FMCG', 'EMAMILTD.NS': 'FMCG',

    # Telecom
    'BHARTIARTL.NS': 'Telecom', 'IDEA.NS': 'Telecom', 'INDUSTOWER.NS': 'Telecom',
    'TATACOMM.NS': 'Telecom',

    # Metals & Mining
    'TATASTEEL.NS': 'Metals', 'HINDALCO.NS': 'Metals', 'JSWSTEEL.NS': 'Metals',
    'NATIONALUM.NS': 'Metals', 'NMDC.NS': 'Metals', 'COALINDIA.NS': 'Metals',
    'HINDCOPPER.NS': 'Metals', 'SAIL.NS': 'Metals', 'JINDALSTEL.NS': 'Metals',

    # Real Estate
    'DLF.NS': 'Real Estate', 'GODREJPROP.NS': 'Real Estate', 'OBEROIRLTY.NS': 'Real Estate',
    'PHOENIXLTD.NS': 'Real Estate', 'BRIGADE.NS': 'Real Estate', 'SOBHA.NS': 'Real Estate',

    # Infrastructure / Construction
    'L&T.NS': 'Infrastructure', 'ULTRACEMCO.NS': 'Infrastructure',
    'ADANIPORTS.NS': 'Infrastructure', 'NCC.NS': 'Infrastructure',
    'KNR.NS': 'Infrastructure', 'IRCON.NS': 'Infrastructure',

    # Power
    'NTPC.NS': 'Power', 'POWERGRID.NS': 'Power', 'ADANIGREEN.NS': 'Power',
    'TATAPOWER.NS': 'Power', 'JSWENERGY.NS': 'Power', 'SUZLON.NS': 'Power',

    # Cement
    'ULTRACEMCO.NS': 'Cement', 'ACC.NS': 'Cement', 'AMBUJACEM.NS': 'Cement',
    'RAMCOCEM.NS': 'Cement', 'DALBHARAT.NS': 'Cement', 'SHREECEM.NS': 'Cement',

    # Others
    'TITAN.NS': 'Consumer Durables', 'VOLTAS.NS': 'Consumer Durables',
    'BLUEDART.NS': 'Logistics', 'DELHIVERY.NS': 'Logistics',
    'HAL.NS': 'Defence', 'BEL.NS': 'Defence',
    'ZOMATO.NS': 'Internet', 'INFOEDGE.NS': 'Internet',
    'NYKAA.NS': 'Retail', 'TRENT.NS': 'Retail',
    'DMART.NS': 'Retail',
}

# Reverse map: sector -> [tickers]
SECTOR_TO_TICKERS = {}
for t, s in SECTOR_MAP.items():
    SECTOR_TO_TICKERS.setdefault(s, []).append(t)

# Limit peers to avoid too many API calls
MAX_PEERS = 6


def get_sector_from_yfinance(ticker):
    """Get sector/industry from yfinance."""
    if not HAS_YFINANCE:
        return None, None
    try:
        info = yf.Ticker(ticker).info
        sector = info.get('sector') or info.get('industry')
        industry = info.get('industry')
        return sector, industry
    except Exception:
        return None, None


def find_peers(ticker):
    """Find peer tickers in the same sector."""
    sector, industry = get_sector_from_yfinance(ticker)
    if not sector:
        # Fallback to static map
        sector = SECTOR_MAP.get(ticker, 'Unknown')
        if sector == 'Unknown':
            return [ticker], 'Unknown'

    peers = SECTOR_TO_TICKERS.get(sector, [])
    if not peers:
        return [ticker], sector

    # Move the target ticker to front; limit to MAX_PEERS + 1
    peers = [t for t in peers if t != ticker]
    return [ticker] + peers[:MAX_PEERS], sector


def fetch_peer_metrics(tickers):
    """Fetch key comparison metrics for all tickers."""
    if not HAS_YFINANCE:
        return {}

    results = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            hist = yf.Ticker(t).history(period='1y')
            if hist.empty:
                continue

            close = hist['Close']
            returns = close.pct_change().dropna()
            vol_annual = float(returns.std() * (252 ** 0.5)) if len(returns) > 0 else None
            total_ret = float(close.iloc[-1] / close.iloc[0] - 1) if len(close) > 1 else None

            results[t] = {
                'name': info.get('shortName') or info.get('longName') or t,
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice') or (round(float(close.iloc[-1]), 2) if len(close) > 0 else None),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'eps': info.get('trailingEPS'),
                'book_value': info.get('bookValue'),
                'dividend_yield': info.get('dividendYield'),
                'annual_volatility': round(vol_annual, 4) if vol_annual else None,
                'total_return_1y': round(total_ret, 4) if total_ret else None,
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
        except Exception as e:
            print(f"Warning: Could not fetch peer data for {t}: {e}")
            results[t] = {'name': t, 'error': str(e)}

    return results


def build_comparison_table(peer_metrics, target_ticker):
    """Build a structured comparison of the target vs peer averages."""
    if target_ticker not in peer_metrics:
        return {'peers': peer_metrics, 'comparison': None}

    target = peer_metrics[target_ticker]
    peers = {k: v for k, v in peer_metrics.items() if k != target_ticker}
    if not peers:
        return {'peers': peer_metrics, 'comparison': None}

    # Compute peer averages for numeric fields
    numeric_fields = ['market_cap', 'pe_ratio', 'eps', 'book_value',
                      'dividend_yield', 'annual_volatility', 'total_return_1y', 'current_price']
    avg = {}
    for field in numeric_fields:
        vals = [p.get(field) for p in peers.values() if p.get(field) is not None]
        if vals:
            avg[field] = sum(vals) / len(vals)
        else:
            avg[field] = None

    # Relative comparison: target vs peer average (as percentage)
    comparison = {}
    for field in numeric_fields:
        t_val = target.get(field)
        a_val = avg.get(field)
        if t_val is not None and a_val is not None and a_val != 0:
            comparison[field] = {
                'target': t_val if isinstance(t_val, float) else t_val,
                'peer_avg': round(a_val, 4),
                'difference_pct': round((t_val - a_val) / abs(a_val) * 100, 2)
            }
        else:
            comparison[field] = {
                'target': t_val,
                'peer_avg': a_val,
                'difference_pct': None
            }

    return {
        'peers': peer_metrics,
        'peer_averages': avg,
        'target_vs_peers': comparison,
        'n_peers_found': len(peers),
    }


def main(data, ticker=None):
    try:
        if isinstance(data, str):
            data = json.loads(data)

        ticker = ticker or data.get('ticker', '')
        if not ticker:
            return json.dumps({'error': 'No ticker provided'})

        peers, sector = find_peers(ticker)
        peer_metrics = fetch_peer_metrics(peers)
        comparison = build_comparison_table(peer_metrics, ticker)
        sector_info = {'sector': sector}
        if HAS_YFINANCE:
            try:
                info = yf.Ticker(ticker).info
                sector_info['industry'] = info.get('industry')
                sector_info['sector'] = info.get('sector') or sector
            except Exception:
                pass

        result = {
            'ticker': ticker,
            'sector': sector_info,
            'n_peers_scanned': len(peers) - 1,
            'peer_tickers': [t for t in peers if t != ticker],
            **comparison,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'note': 'Peers identified via sector mapping + yfinance. Metrics fetched from yfinance.'
        }

        return json.dumps(result)

    except Exception as e:
        print(f"Error in competitor_scanner: {e}", file=sys.stderr)
        return json.dumps({'error': str(e)})


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python competitor_scanner.py <data_json> [ticker]")
        sys.exit(1)
    data = sys.argv[1]
    ticker = sys.argv[2] if len(sys.argv) > 2 else None
    print(main(data, ticker))
