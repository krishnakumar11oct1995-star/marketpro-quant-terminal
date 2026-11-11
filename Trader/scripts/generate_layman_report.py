#!/usr/bin/env python3
"""
Generate production-grade HTML report from analysis JSON, then export to PDF.
Includes charts (via Plotly HTML), source table, confidence meter, executive summary,
and 'what could make this wrong' section.
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import base64
import io
import warnings
warnings.filterwarnings('ignore')

# Try to load plotting libs
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

# ---------------------------------------------------------------------------
# Chart generators (return HTML strings for embedding)
# ---------------------------------------------------------------------------

def build_price_chart(hist_data):
    """Build an interactive Plotly price chart with volume."""
    if not HAS_PLOTLY or not HAS_PANDAS:
        return '<p class="chart-fallback">[Chart unavailable – missing plotly/pandas]</p>'
    dates = hist_data.get('dates', [])
    close = hist_data.get('close', [])
    if not dates or not close:
        return ''
    df = pd.DataFrame({'Date': pd.to_datetime(dates), 'Close': close})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name='Close',
                              line=dict(color='#1a73e8', width=2)))
    fig.update_layout(title='Price History', template='plotly_white',
                      xaxis_title='Date', yaxis_title='Price')
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def build_forecast_chart(forecast_data, hist_data):
    """Build a chart showing forecast mean and confidence bands."""
    if not HAS_PLOTLY or not HAS_PANDAS:
        return '<p class="chart-fallback">[Forecast chart unavailable]</p>'
    mean_f = forecast_data.get('forecast', {}).get('mean', [])
    p5 = forecast_data.get('forecast', {}).get('percentiles', {}).get('5', [])
    p95 = forecast_data.get('forecast', {}).get('percentiles', {}).get('95', [])
    if not mean_f:
        return ''
    days = list(range(1, len(mean_f) + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=mean_f, mode='lines', name='Mean Forecast',
                              line=dict(color='#34a853', width=2)))
    if p5 and p95:
        fig.add_trace(go.Scatter(x=days + days[::-1],
                                  y=p95 + p5[::-1],
                                  fill='toself', fillcolor='rgba(52,168,83,0.2)',
                                  line=dict(color='rgba(255,255,255,0)'),
                                  name='5%-95% CI'))
    fig.update_layout(title='Price Forecast (Mean ± 90% CI)', template='plotly_white',
                      xaxis_title='Days Ahead', yaxis_title='Price')
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def build_confidence_meter(score):
    """Build a simple SVG confidence meter (0-1 scale)."""
    pct = max(0, min(100, score * 100))
    color = '#34a853' if pct >= 70 else '#fbbc04' if pct >= 40 else '#ea4335'
    html = f'''
    <div class="confidence-meter" style="text-align:center;margin:1em 0;">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="60" fill="none" stroke="#e0e0e0" stroke-width="12"/>
        <circle cx="70" cy="70" r="60" fill="none" stroke="{color}" stroke-width="12"
                stroke-dasharray="{pct*3.77} 377" stroke-linecap="round"
                transform="rotate(-90,70,70)"/>
        <text x="70" y="75" text-anchor="middle" font-size="28" font-weight="bold" fill="{color}">
          {pct:.0f}%
        </text>
      </svg>
      <p style="margin:0;font-size:0.9em;color:#666;">Forecast Reliability</p>
    </div>
    '''
    return html

def build_source_table(analysis):
    """Build an HTML source table showing origin of key data points."""
    rows = []
    modules = analysis.get('modules', {})
    ticker = analysis.get('ticker', 'N/A')

    # Price source
    data_mod = modules.get('data', {})
    if data_mod:
        rt = data_mod.get('real_time', {})
        rows.append({
            'data_point': f'{ticker} Current Price',
            'value': rt.get('current_price', 'N/A'),
            'source': rt.get('data_source', 'yfinance') if isinstance(data_mod.get('metadata'), dict) else 'yfinance',
            'timestamp': rt.get('timestamp', 'N/A')
        })

    # Forecast source
    fc_mod = modules.get('forecast', {})
    if fc_mod:
        mean_f = fc_mod.get('forecast', {}).get('mean', [])
        last_val = mean_f[-1] if mean_f else 'N/A'
        rows.append({
            'data_point': f'{ticker} Mean Forecast (D+{fc_mod.get("forecast_horizon_days", "?")})',
            'value': f'{last_val:.2f}' if isinstance(last_val, (int, float)) else last_val,
            'source': 'Monte Carlo (Student-t)',
            'timestamp': fc_mod.get('timestamp', 'N/A')
        })

    # Analyst consensus
    audit_mod = modules.get('adversarial_audit', {})
    if audit_mod:
        consensus = audit_mod.get('analyst_consensus')
        if consensus:
            rows.append({
                'data_point': f'{ticker} Analyst Consensus',
                'value': consensus.get('consensus', 'N/A'),
                'source': consensus.get('source', 'Unknown'),
                'timestamp': consensus.get('timestamp', 'N/A')
            })
        else:
            rows.append({
                'data_point': f'{ticker} Analyst Consensus',
                'value': 'Not available',
                'source': 'N/A',
                'timestamp': audit_mod.get('timestamp', 'N/A')
            })

    # Valuation
    val_mod = modules.get('valuation', {})
    if val_mod:
        for model, details in val_mod.get('valuation_models', {}).items():
            if isinstance(details, dict):
                rows.append({
                    'data_point': f'{ticker} {model.replace("_"," ").title()}',
                    'value': f'{details.get("value_per_share") or details.get("value", "N/A"):.2f}',
                    'source': details.get('note', 'yfinance financials'),
                    'timestamp': val_mod.get('timestamp', 'N/A')
                })

    # Competitor
    comp_mod = modules.get('competitors', {})
    if comp_mod:
        rows.append({
            'data_point': f'{ticker} Sector / Peers',
            'value': f'{comp_mod.get("sector",{}).get("sector","?")} ({comp_mod.get("n_peers_scanned",0)} peers)',
            'source': 'yfinance + curated mapping',
            'timestamp': comp_mod.get('timestamp', 'N/A')
        })

    # Sentiment
    sent_mod = modules.get('sentiment', {})
    if sent_mod:
        summary = sent_mod.get('summary', {})
        rows.append({
            'data_point': f'{ticker} News Sentiment',
            'value': summary.get('sentiment_label', 'N/A'),
            'source': 'Yahoo Finance / TextBlob',
            'timestamp': sent_mod.get('timestamp', 'N/A')
        })

    # Risk
    risk_mod = modules.get('risk', {})
    if risk_mod:
        metrics = risk_mod.get('metrics', {})
        for k, v in metrics.items():
            if isinstance(v, dict) and 'value' in v:
                rows.append({
                    'data_point': f'{ticker} {k.replace("_"," ").title()}',
                    'value': f'{v["value"]:.4f}' if isinstance(v['value'], float) else v['value'],
                    'source': v.get('note', 'Historical calculation'),
                    'timestamp': risk_mod.get('timestamp', 'N/A')
                })

    if not rows:
        return '<p class="no-data">No source records available.</p>'

    html = '<table class="source-table"><thead><tr><th>Data Point</th><th>Value</th><th>Source</th><th>Timestamp</th></tr></thead><tbody>'
    for r in rows:
        html += f'<tr><td>{r["data_point"]}</td><td>{r["value"]}</td><td>{r["source"]}</td><td>{r["timestamp"]}</td></tr>'
    html += '</tbody></table>'
    return html

def build_what_could_go_wrong(analysis):
    """Generate a 'What could make this wrong' section based on analysis data."""
    warnings_list = []

    # Check data availability
    data_mod = analysis.get('modules', {}).get('data', {})
    if 'error' in data_mod:
        warnings_list.append('Data fetch failed or is incomplete.')

    # Forecast reliability
    fc_mod = analysis.get('modules', {}).get('forecast', {})
    reliability = fc_mod.get('forecast_reliability_score', 0.5)
    if reliability < 0.4:
        warnings_list.append('Forecast reliability is low. Model accuracy on recent backtests was poor.')
    elif reliability < 0.7:
        warnings_list.append('Moderate forecast reliability. Use with caution and consult other indicators.')

    # Analyst consensus gap
    audit_mod = analysis.get('modules', {}).get('adversarial_audit', {})
    if audit_mod.get('analyst_consensus') is None:
        warnings_list.append('No analyst consensus available. Forecast is not externally validated.')
    else:
        comp = audit_mod.get('comparison', {})
        fc_vs = comp.get('forecast_vs_consensus', {})
        diff = fc_vs.get('percentage_difference')
        if diff is not None and abs(diff) > 15:
            warnings_list.append(f'Internal forecast deviates significantly from analyst consensus ({diff:.1f}%). Market may disagree.')

    # Valuation gaps
    val_mod = analysis.get('modules', {}).get('valuation', {})
    current_price = analysis.get('modules', {}).get('data', {}).get('real_time', {}).get('current_price')
    val_models = val_mod.get('valuation_models', {})
    if val_models:
        vals = [v.get('value_per_share') or v.get('value') for k, v in val_models.items() if isinstance(v, dict)]
        vals = [v for v in vals if v is not None and isinstance(v, (int, float))]
        if vals and current_price:
            avg_val = sum(vals) / len(vals)
            gap = (current_price - avg_val) / avg_val * 100
            warnings_list.append(f'Price vs. intrinsic value gap: {gap:.1f}%. Markets can remain irrational.')
    else:
        warnings_list.append('No valuation models could be computed due to insufficient fundamental data.')

    # Sentiment warning
    sent_mod = analysis.get('modules', {}).get('sentiment', {})
    summary = sent_mod.get('summary', {})
    if summary.get('total_news_items', 0) < 3:
        warnings_list.append('Limited news coverage. Sentiment signal may be weak.')

    # General model limitations
    warnings_list.append('Monte Carlo forecast assumes past volatility and return patterns persist. Regime changes, black swan events, or sudden news can invalidate all forecasts.')
    warnings_list.append('This is not financial advice. Always do your own research and consult a qualified advisor.')

    html = '<ul class="risk-list">'
    for w in warnings_list:
        html += f'<li>{w}</li>'
    html += '</ul>'
    return html

# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------

def main(analysis, output_dir=None):
    try:
        analysis = json.loads(analysis) if isinstance(analysis, str) else analysis
    except Exception:
        analysis = analysis if isinstance(analysis, dict) else {}

    ticker = analysis.get('ticker', 'UNKNOWN')
    ts = analysis.get('analysis_timestamp', datetime.now().isoformat())
    modules = analysis.get('modules', {})

    # ---- Build sub-sections ----
    exec_summary = '<p class="no-data">No analysis data available.</p>'
    price_chart = ''
    forecast_chart = ''
    confidence_meter = ''
    source_table = ''
    what_could_go_wrong = ''
    valuation_section = ''
    sentiment_section = ''
    risk_section = ''

    data_mod = modules.get('data', {})
    fc_mod = modules.get('forecast', {})
    distill_mod = modules.get('distillation', {})
    audit_mod = modules.get('adversarial_audit', {})
    val_mod = modules.get('valuation', {})
    sent_mod = modules.get('sentiment', {})
    risk_mod = modules.get('risk', {})
    comp_mod = modules.get('competitors', {})

    # Price chart
    hist_data = data_mod.get('historical_data', {})
    if hist_data:
        price_chart = build_price_chart(hist_data)

    # Forecast chart
    if fc_mod:
        forecast_chart = build_forecast_chart(fc_mod, hist_data)

    # Confidence meter
    reliability = fc_mod.get('forecast_reliability_score', 0.5)
    confidence_meter = build_confidence_meter(reliability)

    # Source table
    source_table = build_source_table(analysis)

    # What could go wrong
    what_could_go_wrong = build_what_could_go_wrong(analysis)

    # Valuation secion
    if val_mod and val_mod.get('valuation_models'):
        cur_price = data_mod.get('real_time', {}).get('current_price', 'N/A')
        models = val_mod['valuation_models']
        html = f'<p>Current Price: <strong>{cur_price}</strong></p><table class="val-table"><thead><tr><th>Model</th><th>Intrinsic Value</th><th>Upside/(Downside)</th></tr></thead><tbody>'
        for model_name, details in models.items():
            if isinstance(details, dict):
                val = details.get('value_per_share') or details.get('value')
                if val is not None and cur_price and isinstance(cur_price, (int, float)):
                    spread = (cur_price - val) / val * 100
                else:
                    spread = 'N/A'
                html += f'<tr><td>{model_name.replace("_"," ").title()}</td><td>{val if val is not None else "N/A"}</td><td>{f"{spread:.1f}%" if isinstance(spread, float) else "N/A"}</td></tr>'
        html += '</tbody></table>'
        if val_mod.get('notes'):
            for note in val_mod['notes']:
                html += f'<p class="note">{note}</p>'
        valuation_section = html
    else:
        valuation_section = '<p class="no-data">Valuation data not available.</p>'

    # Sentiment secion
    if sent_mod and sent_mod.get('summary'):
        s = sent_mod['summary']
        sentiment_section = f'''
        <div class="sentiment-summary">
          <p>Average Sentiment: <strong class="sent-{s.get("sentiment_label","neutral")}">{s.get("sentiment_label","N/A")}</strong>
          (score: {s.get("average_sentiment",0):.3f})</p>
          <p>Positive: {s.get("positive_count",0)} | Negative: {s.get("negative_count",0)} | Neutral: {s.get("neutral_count",0)}</p>
          <p class="note">{sent_mod.get("note","")}</p>
        </div>'''
    else:
        sentiment_section = '<p class="no-data">Sentiment data not available.</p>'

    # Risk secion
    if risk_mod and risk_mod.get('metrics'):
        metrics = risk_mod['metrics']
        html = '<table class="risk-table"><thead><tr><th>Metric</th><th>Value</th><th>Note</th></tr></thead><tbody>'
        for k, v in metrics.items():
            if isinstance(v, dict):
                note = v.get('note', '')
                val = v.get('value', 'N/A')
                if isinstance(val, float):
                    val = f'{val:.4f}'
                html += f'<tr><td>{k.replace("_"," ").title()}</td><td>{val}</td><td class="note-cell">{note}</td></tr>'
        html += '</tbody></table>'
        # Show simulated flags
        sim_flags = risk_mod.get('simulated_flags', {})
        if any(sim_flags.values()):
            html += '<p class="warning"><strong>Note:</strong> The following data points are simulated/unavailable:</p><ul>'
            for flag, val in sim_flags.items():
                if val:
                    html += f'<li>{flag.replace("_"," ").title()} – simulated</li>'
            html += '</ul>'
        risk_section = html
    else:
        risk_section = '<p class="no-data">Risk data not available.</p>'

    # Competitor comparison section
    competitor_section = ''
    if comp_mod and comp_mod.get('peers'):
        peers = comp_mod.get('peers', {})
        ticker = analysis.get('ticker', '')
        target = peers.get(ticker, {})
        peer_list = comp_mod.get('peer_tickers', [])

        html = f'''<p><strong>Sector:</strong> {comp_mod.get('sector', {}).get('sector', 'N/A')}
        | <strong>Peers Found:</strong> {comp_mod.get('n_peers_scanned', 0)}</p>'''

        if target:
            html += '<table class="comp-table"><thead><tr><th>Metric</th><th>' + ticker + '</th>'
            for p in peer_list[:4]:
                name = peers.get(p, {}).get('name', p)[:20]
                html += f'<th>{name}</th>'
            html += '<th>Peer Avg</th></tr></thead><tbody>'

            metrics_def = [
                ('Current Price', 'current_price', '{:.2f}'),
                ('Market Cap', 'market_cap', '{:.0f}'),
                ('P/E Ratio', 'pe_ratio', '{:.2f}'),
                ('EPS', 'eps', '{:.2f}'),
                ('Book Value', 'book_value', '{:.2f}'),
                ('Div Yield', 'dividend_yield', '{:.4f}'),
                ('Volatility (Ann)', 'annual_volatility', '{:.4f}'),
                ('Return (1Y)', 'total_return_1y', '{:.2%}'),
            ]

            for label, key, fmt in metrics_def:
                t_val = target.get(key)
                row = f'<tr><td><strong>{label}</strong></td><td>{fmt.format(t_val) if t_val is not None else "N/A"}</td>'
                for p in peer_list[:4]:
                    p_val = peers.get(p, {}).get(key)
                    row += f'<td>{fmt.format(p_val) if p_val is not None else "N/A"}</td>'
                avg_val = comp_mod.get('peer_averages', {}).get(key)
                row += f'<td>{fmt.format(avg_val) if avg_val is not None else "N/A"}</td></tr>'
                html += row

            html += '</tbody></table>'

            # Target vs peers comparison
            tvp = comp_mod.get('target_vs_peers', {})
            if tvp:
                html += '<h3>Target vs Peer Average</h3><table class="comp-table"><thead><tr><th>Metric</th><th>Target</th><th>Peer Avg</th><th>Difference</th></tr></thead><tbody>'
                for label, key, fmt in metrics_def:
                    c = tvp.get(key, {})
                    if c.get('difference_pct') is not None:
                        diff = c['difference_pct']
                        cls = 'pos' if diff > 0 else 'neg'
                        html += f'<tr><td>{label}</td><td>{fmt.format(c["target"]) if c["target"] is not None else "N/A"}</td><td>{fmt.format(c["peer_avg"]) if c["peer_avg"] is not None else "N/A"}</td><td class="diff-{cls}">{diff:+.2f}%</td></tr>'
                html += '</tbody></table>'

        competitor_section = html

    # Comprehensive Analysis Dump
    comprehensive_section = ''
    comp_sections = []

    # Adversarial audit raw data
    if audit_mod:
        html = '<table class="raw-table"><thead><tr><th>Item</th><th>Details</th></tr></thead><tbody>'
        ac = audit_mod.get('analyst_consensus')
        if ac:
            html += f'<tr><td>Analyst Source</td><td>{ac.get("source","N/A")}</td></tr>'
            html += f'<tr><td>Consensus Target</td><td>{ac.get("consensus","N/A")}</td></tr>'
            html += f'<tr><td>Bull Target</td><td>{ac.get("bull_target","N/A")}</td></tr>'
            html += f'<tr><td>Bear Target</td><td>{ac.get("bear_target","N/A")}</td></tr>'
            html += f'<tr><td>Recommendation</td><td>{ac.get("recommendation_mean","N/A")}</td></tr>'
            html += f'<tr><td># Analysts</td><td>{ac.get("number_of_analysts","N/A")}</td></tr>'
        else:
            html += '<tr><td>Analyst Consensus</td><td>Not available</td></tr>'
        fc_vs = audit_mod.get('comparison', {}).get('forecast_vs_consensus', {})
        if fc_vs:
            diff = fc_vs.get('percentage_difference')
            html += f'<tr><td>Forecast vs Consensus</td><td>{"{:.2f}%".format(diff) if diff is not None else "N/A"}</td></tr>'
        html += f'<tr><td>Note</td><td>{audit_mod.get("note","")}</td></tr>'
        html += '</tbody></table>'
        comp_sections.append(('Adversarial Audit Details', html))

    # Sentiment raw news
    if sent_mod and sent_mod.get('news_items'):
        items = sent_mod['news_items']
        html = '<div class="news-scroll">'
        for item in items[:10]:
            score = item.get('sentiment_score', 0)
            label = item.get('sentiment_label', 'neutral')
            html += f'<div class="news-item"><span class="sent-{label}">[{label.upper()}]</span> '
            html += f'{item.get("headline","")} <span class="meta">— {item.get("source","")}</span></div>'
        html += '</div>'
        if len(items) > 10:
            html += f'<p class="note">... and {len(items) - 10} more headlines</p>'
        comp_sections.append(('News Sentiment (Headlines)', html))

    # Forecast parameters
    if fc_mod:
        html = '<table class="raw-table"><thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>'
        html += f'<tr><td>Model</td><td>{fc_mod.get("distribution_assumption","N/A")}</td></tr>'
        html += f'<tr><td>Regime Detected</td><td>{fc_mod.get("regime","N/A")}</td></tr>'
        html += f'<tr><td>Mean Return (hist)</td><td>{fc_mod.get("parameters",{}).get("historical_mean_return","N/A")}</td></tr>'
        html += f'<tr><td>Volatility (hist)</td><td>{fc_mod.get("parameters",{}).get("historical_volatility","N/A")}</td></tr>'
        html += f'<tr><td>Reliability Score</td><td>{fc_mod.get("forecast_reliability_score","N/A")}</td></tr>'
        html += f'<tr><td>Backtest Note</td><td>{fc_mod.get("backtest_note","")}</td></tr>'
        # Advanced model details
        if 'model' in fc_mod:
            html += f'<tr><td>Ensemble Components</td><td>{json.dumps(fc_mod.get("ensemble_components",{}))}</td></tr>'
            html += f'<tr><td>Predicted Direction</td><td>{fc_mod.get("predicted_direction","N/A")} (prob: {fc_mod.get("up_probability","N/A")})</td></tr>'
            html += f'<tr><td>Test Accuracy</td><td>{fc_mod.get("test_accuracy","N/A")}</td></tr>'
            html += f'<tr><td>Features Used</td><td>{fc_mod.get("feature_count","N/A")}</td></tr>'
            html += f'<tr><td>Walk-Forward Avg Acc</td><td>{fc_mod.get("walk_forward_avg_accuracy","N/A")}</td></tr>'
        html += '</tbody></table>'
        comp_sections.append(('Forecast Parameters', html))

    # Valuation model details
    if val_mod and val_mod.get('valuation_models'):
        html = '<table class="raw-table"><thead><tr><th>Model</th><th>Value</th><th>Inputs</th><th>Note</th></tr></thead><tbody>'
        for model_name, details in val_mod['valuation_models'].items():
            if isinstance(details, dict):
                val = details.get('value_per_share') or details.get('value', 'N/A')
                inputs = json.dumps({k: v for k, v in details.items()
                                     if k not in ('value', 'value_per_share', 'note', 'assumptions')})
                note = details.get('note', '')
                html += f'<tr><td>{model_name.replace("_"," ").title()}</td><td>{val}</td><td style="font-size:.8em;">{inputs}</td><td>{note}</td></tr>'
        html += '</tbody></table>'
        if val_mod.get('notes'):
            for n in val_mod['notes']:
                html += f'<p class="note">{n}</p>'
        comp_sections.append(('Valuation Inputs', html))

    # Fundamental data
    if val_mod and val_mod.get('fundamental_data'):
        fd = val_mod['fundamental_data']
        html = '<table class="raw-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>'
        for k, v in fd.items():
            if v is not None:
                html += f'<tr><td>{k.replace("_"," ").title()}</td><td>{v}</td></tr>'
        html += '</tbody></table>'
        comp_sections.append(('Fundamental Data', html))

    if comp_sections:
        html = ''
        for title, content in comp_sections:
            html += f'<details open><summary><strong>{title}</strong></summary><div class="detail-content">{content}</div></details>'
        comprehensive_section = html

    # Archetype distillation
    if distill_mod and distill_mod.get('archetypes'):
        archs = distill_mod['archetypes']
        html = '<table class="arch-table"><thead><tr><th>Archetype</th><th>Prob</th><th>Exp Return</th><th>Stop-Loss</th></tr></thead><tbody>'
        for name, data in archs.items():
            prob = f'{data.get("probability",0)*100:.1f}%'
            exp_ret = f'{data.get("expected_return",0)*100:.1f}%'
            sl = f'{data.get("stop_loss_price",0):.2f} ({data.get("stop_loss_pct",0):.1f}%)'
            html += f'<tr class="arch-{name}"><td>{name.title()}</td><td>{prob}</td><td>{exp_ret}</td><td>{sl}</td></tr>'
        html += '</tbody></table>'
        distill_html = html

    # Executive summary builder
    arch = distill_mod.get('archetypes', {})
    bull_p = arch.get('bull', {}).get('probability', 0)
    bear_p = arch.get('bear', {}).get('probability', 0)
    prob_label = 'Bullish' if bull_p > bear_p else 'Bearish' if bear_p > bull_p else 'Neutral'
    sent_label = sent_mod.get('summary', {}).get('sentiment_label', 'neutral')
    exec_summary = f'''
    <div class="exec-summary">
      <h3>{ticker} Analysis Summary</h3>
      <p><strong>Probability Bias:</strong> {prob_label} (Bull: {bull_p*100:.0f}% / Bear: {bear_p*100:.0f}%)</p>
      <p><strong>Sentiment:</strong> {sent_label.title()} (score: {sent_mod.get("summary",{}).get("average_sentiment",0):.2f})</p>
      <p><strong>Forecast Reliability:</strong> {reliability*100:.0f}%</p>
      <p><strong>Risk Level:</strong> {risk_mod.get("metrics",{}).get("volatility",{}).get("annualized","N/A")}</p>
      <p class="disclaimer"><em>This report is for informational purposes only and does not constitute financial advice.</em></p>
    </div>'''

    # ---- Assemble HTML ----
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{ticker} – Market Pro Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #222; background: #fff; line-height: 1.6; padding: 2em; }}
    h1 {{ font-size: 1.8em; border-bottom: 2px solid #1a73e8; padding-bottom: .3em; }}
    h2 {{ font-size: 1.4em; margin: 1.5em 0 .5em; color: #1a73e8; }}
    h3 {{ font-size: 1.1em; margin: 1em 0 .3em; }}
    .meta {{ color: #666; font-size: .85em; }}
    .section {{ margin: 2em 0; padding: 1.5em; border: 1px solid #e0e0e0; border-radius: 8px; }}
    .exec-summary {{ background: #f0f7ff; }}
    .disclaimer {{ font-size: .85em; color: #888; margin-top: .5em; }}
    table {{ width: 100%; border-collapse: collapse; margin: .5em 0; font-size: .9em; }}
    th, td {{ padding: .5em .7em; text-align: left; border-bottom: 1px solid #ddd; }}
    th {{ background: #f5f5f5; font-weight: 600; }}
    .source-table td {{ font-size: .8em; }}
    .risk-list li {{ margin: .3em 0; padding-left: .5em; }}
    .note {{ color: #666; font-size: .85em; font-style: italic; }}
    .no-data {{ color: #999; font-style: italic; }}
    .warning {{ color: #ea4335; }}
    .sent-positive {{ color: #34a853; }}
    .sent-negative {{ color: #ea4335; }}
    .arch-Bear td:first-child {{ color: #ea4335; }}
    .arch-Neutral td:first-child {{ color: #fbbc04; }}
    .arch-Bull td:first-child {{ color: #34a853; }}
    .note-cell {{ font-size: .8em; color: #666; }}
    .val-table th, .val-table td, .risk-table th, .risk-table td, .arch-table th, .arch-table td {{ font-size: .85em; }}
    .comp-table {{ font-size: .8em; }}
    .comp-table th {{ font-size: .75em; white-space: nowrap; }}
    .diff-pos {{ color: #34a853; font-weight: bold; }}
    .diff-neg {{ color: #ea4335; font-weight: bold; }}
    .news-scroll {{ max-height: 300px; overflow-y: auto; font-size: .85em; }}
    .news-item {{ padding: .3em 0; border-bottom: 1px solid #eee; }}
    .raw-table {{ font-size: .8em; }}
    .raw-table td {{ word-break: break-word; }}
    details {{ margin: .5em 0; padding: .5em; border: 1px solid #e0e0e0; border-radius: 4px; }}
    details summary {{ cursor: pointer; color: #1a73e8; }}
    .detail-content {{ margin-top: .5em; }}
    @page {{ margin: 2cm; }}
    @media print {{
      body {{ font-size: 11pt; }}
      .section {{ page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <h1>{ticker} – Market Professional Report</h1>
  <p class="meta">Generated: {ts}</p>

  <div class="section">{exec_summary}</div>

  {confidence_meter}

  <div class="section">
    <h2>Price &amp; Volume History</h2>
    {price_chart}
  </div>

  <div class="section">
    <h2>Forecast (Next {fc_mod.get("forecast_horizon_days","?")} Days)</h2>
    {forecast_chart}
    {distill_html}
  </div>

  <div class="section">
    <h2>Fundamental Valuation</h2>
    {valuation_section}
  </div>

  <div class="section">
    <h2>Sentiment Analysis</h2>
    {sentiment_section}
  </div>

  <div class="section">
    <h2>Risk Dashboard</h2>
    {risk_section}
  </div>

  <div class="section">
    <h2>What Could Make This Wrong</h2>
    {what_could_go_wrong}
  </div>

  <div class="section">
    <h2>Competitor Comparison</h2>
    {competitor_section}
  </div>

  <div class="section">
    <h2>Complete Analysis</h2>
    {comprehensive_section}
  </div>

  <div class="section">
    <h2>Data Sources</h2>
    {source_table}
  </div>
</body>
</html>'''

    # ---- Write HTML ----
    if output_dir:
        html_path = Path(output_dir) / 'report.html'
    else:
        html_path = Path(f'./output/{ticker}/report.html')
    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # ---- Convert to PDF ----
    pdf_path = None
    if HAS_WEASYPRINT:
        try:
            pdf_path = html_path.with_suffix('.pdf')
            HTML(string=html).write_pdf(str(pdf_path))
        except Exception as e:
            print(f"Warning: PDF generation failed ({e}). HTML report available.")
    else:
        print("WeasyPrint not installed. HTML report generated but not converted to PDF.")

    result = {
        'html_path': str(html_path),
        'pdf_path': str(pdf_path) if pdf_path else None,
        'pdf_generated': bool(pdf_path),
        'note': 'Report generated as HTML first, with embedded Plotly charts and source table.'
    }
    return json.dumps(result)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_layman_report.py <analysis_json> [output_dir]")
        sys.exit(1)
    with open(sys.argv[1], 'r') as f:
        analysis = json.load(f)
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    print(main(analysis, output_dir))
