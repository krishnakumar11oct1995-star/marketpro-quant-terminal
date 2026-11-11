import sys
sys.path.insert(0, ".")
from src.services.data_service import DataService

d = DataService()
q = d.get_quote("AAPL")
print(f"AAPL: ${q.price} ({q.change_pct:+.2f}%)")
if q.pe_ratio:
    print(f"P/E: {q.pe_ratio:.2f}, Mkt Cap: ${q.market_cap/1e9:.1f}B")

indices = d.get_market_indices()
for name, data in indices.items():
    print(f"{name}: ${data['price']} ({data['change_pct']:+.2f}%)")

ratios = d.get_ratios("MSFT")
if ratios:
    print(f"MSFT ROE: {ratios.roe*100:.1f}%" if ratios.roe else "")
    print(f"MSFT EPS: {ratios.eps}" if ratios.eps else "")

print("\nData fetching OK")
